import os
import io
import re
import fitz  # PyMuPDF — used for native PDF highlighting and merging
from dotenv import load_dotenv
load_dotenv()

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# Reportlab is only used to build the summary page (page 1 of the final report)
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors

# ─── Model Initialisation ────────────────────────────────────────────────────
# Models are loaded once globally so they are not reloaded on every API request

token = os.getenv("OPENAI_TOKEN")

print("Loading Embedding Model & LLM Engine...")
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Using GitHub Models endpoint with OpenAI-compatible SDK
llm_engine = ChatOpenAI(
    # model="gpt-4o-mini",
    model="gpt-4o",
    # model="gpt-4.1-mini",
    api_key=token,
    base_url="https://models.inference.ai.azure.com",
    temperature=0
)

# ─── Global State ────────────────────────────────────────────────────────────
# Path to the FAISS vector index saved during upload
FAISS_INDEX_PATH = "temp/faiss_index"

# Path to the original course PDF uploaded by the user.
# Saved during upload so that generate_audit_pdf() can open and annotate it later.
COURSE_PDF_PATH = ""

# ─── Prompt Templates ────────────────────────────────────────────────────────

prompt_template = """
You are a strict academic auditor. Your job is to verify if specific are explicitly taught in the course content.

GUIDELINE TO CHECK: "{guideline}"

AVAILABLE COURSE CONTENT: 
"{context}"

INSTRUCTIONS:
1. Determine if the guideline is "Fully Covered", "Partially Covered", or "Not Covered".
2. Start your response with exactly "Match: [Status]".
3. Provide a concise explanation.
4. You MUST provide the exact quote from the text that proves your decision. If it is Not Covered, write "Exact Quote: None".

RULES FOR GRADING:
1. **EXACT MATCH REQUIRED:** If the guideline asks for a specific concept (e.g., "Sessions", "Cookies") and the content only talks about generic logic (e.g., "If statements", "Loops"), the answer MUST be "Not Covered".
2. **NO ASSUMPTIONS:** Do not assume students "might" learn it. If the text is missing, it is "Not Covered".
3. **BE HONEST:** It is okay to say "Not Covered".

Answer format:
Match: [Fully Covered / Partially Covered / Not Covered]
Reasoning: [Explanation]
Exact Quote: [The quote from the text]
"""
prompt = PromptTemplate(input_variables=["guideline", "context"], template=prompt_template)

extraction_prompt_template = """
You are an academic curriculum assistant. Your only task is to extract the core learning objectives, guidelines, or syllabus requirements from the provided text.

SOURCE TEXT:
"{text}"

INSTRUCTIONS:
1. Extract the specific learning guidelines, outcomes, or objectives.
2. STRICT RULE: Do not hallucinate or invent anything. Only extract what is explicitly stated in the source text. 
3. Do not paraphrase. Extract the concepts as faithfully to the original text as possible.
4. Return your answer as a clean, numbered list.
5. Provide ONLY the list. Absolutely no introductory or concluding remarks.

OUTPUT FORMAT:
1. [Guideline 1]
2. [Guideline 2]
"""
extraction_prompt = PromptTemplate(input_variables=["text"], template=extraction_prompt_template)

def extract_guidelines(pdf_path):
    """Loads a guidelines PDF and uses the LLM to extract a clean list of learning objectives."""
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()

    # Combine every page into one string for the LLM to process
    full_text = "\n".join([p.page_content for p in pages])

    final_prompt = extraction_prompt.format(text=full_text)
    print("Extracting guidelines via LLM...")
    response = llm_engine.invoke(final_prompt)
    response = response.content  # Unwrap the message object to get the plain string

    # Parse the numbered list the LLM returns into a clean Python list
    clean_guidelines = []
    for line in response.split('\n'):
        line = line.strip()
        # Strip leading numbering/bullets (e.g. "1.", "-", "*") so the frontend doesn't double-number
        clean_line = re.sub(r'^(\d+\.|\-|\*)\s*', '', line).strip()
        if len(clean_line) > 10:  # Skip blank or trivially short lines
            clean_guidelines.append(clean_line)

    return clean_guidelines


def build_and_save_faiss(pdf_path):
    """
    Chunks the uploaded course content PDF into overlapping segments,
    embeds them, and saves a FAISS vector index to disk for later retrieval.
    Also saves the path to the original PDF so it can be annotated at report time.
    """
    global COURSE_PDF_PATH

    loader = PyPDFLoader(pdf_path)
    docs = loader.load()

    # Remembering where the original PDF lives as it's needed by generate_audit_pdf()
    COURSE_PDF_PATH = pdf_path

    # Splitting the document into 500-char chunks with 50-char overlap for better context capture
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(docs)

    # Building the FAISS index and persisting it so run_analysis() can load it without re-embedding
    vector_db = FAISS.from_documents(chunks, embedding_model)
    vector_db.save_local(FAISS_INDEX_PATH)
    return True


def run_analysis(guidelines: list):
    """
    For each guideline, retrieves the most relevant chunks from FAISS,
    applies a distance threshold to skip clearly unrelated content,
    then asks the LLM to determine coverage and extract an exact quote.
    Returns a structured list of audit result dicts.
    """
    # Load the FAISS index that was built during the upload step
    vector_db = FAISS.load_local(FAISS_INDEX_PATH, embedding_model, allow_dangerous_deserialization=True)

    audit_results = []

    # L2 distance threshold: anything above 1.1 is considered semantically unrelated
    DISTANCE_THRESHOLD = 1.1

    for rule in guidelines:
        # Retrieve the 3 closest chunks, along with their L2 distances
        results_with_scores = vector_db.similarity_search_with_score(rule, k=3)
        best_match_distance = results_with_scores[0][1]

        #Rule-based logic to skip the LLM entirely if no chunk is close enough
        if best_match_distance > DISTANCE_THRESHOLD:
            audit_results.append({
                "guideline": rule,
                "match_status": "Not Covered",
                "reasoning": "System Rule Enforcement: No related content found in the document.",
                "exact_quote": "None",
                "evidence_text": "No relevant evidence met the similarity threshold."
            })
            continue

        # Combine the retrieved chunks into a single context string for the LLM
        context_text = "\n".join([doc.page_content for doc, score in results_with_scores])

        # Ask the LLM to assess coverage and provide an exact quote
        final_prompt = prompt.format(guideline=rule, context=context_text)
        response = llm_engine.invoke(final_prompt)

        #added after the change to the open ai model, as the response format is different
        response = response.content  # extract string from message object 
 
        # Parsing the structured LLM response line by line
        match_status = "Unknown"
        reasoning = "Parsing error"
        exact_quote = "None"

        for line in response.split('\n'):
            if line.startswith("Match:"):
                match_status = line.replace("Match:", "").replace("[", "").replace("]", "").strip()
            elif line.startswith("Reasoning:"):
                reasoning = line.replace("Reasoning:", "").strip()
            elif line.startswith("Exact Quote:"):
                exact_quote = line.replace("Exact Quote:", "").strip()

        audit_results.append({
            "guideline": rule,
            "match_status": match_status,
            "reasoning": reasoning,
            "exact_quote": exact_quote,
            "evidence_text": context_text
        })

    return audit_results


#  PDF Generation

def _clean_quote(quote: str) -> str:
    """
    Strips surrounding quotation marks that the LLM adds around its Exact Quote answer.
    Handles both straight quotes (") and curly/smart quotes (\u201c \u201d \u2018 \u2019).
    The PDF text layer never contains these wrapper characters, so leaving them in
    causes search_for() to find nothing even when the content is clearly present.
    """
    q = quote.strip()
    # Remove matching outer quotes loop so nested pairs are all stripped
    while len(q) >= 2 and q[0] in ('"', '\u201c', '\u2018', "'") and q[-1] in ('"', '\u201d', '\u2019', "'"):
        q = q[1:-1].strip()
    return q


def _search_and_highlight_quote(page, quote: str, color: tuple):
    """
    Attempts to find and highlight a quote on a single PDF page using two strategies

    1 Full match:
        Search for the entire cleaned quote string. Works most of the time when
        the LLM's extracted text matches the PDF's text layer.

    2. Phrase fragments:
        If the full match fails for eg because PyPDFLoader normalised whitespace
        or the LLM paraphrased slightly, split the quote into individual
        sentences/clauses and highlight each fragment that IS found.
        Minimum fragment length is 20 characters to avoid false positives.

    Returns True if at least one highlight was applied.
    """
    highlighted = False

    # Strip any surrounding quotation marks the LLM may have added
    quote = _clean_quote(quote)
    if not quote:
        return False

    # Strategy 1: try the whole quote first
    instances = page.search_for(quote)
    if instances:
        annot = page.add_highlight_annot(instances)
        annot.set_colors(stroke=color)
        annot.update()
        return True

    # Strategy 2: break into sentence/clause fragments and search each.
    # Split on sentence-ending punctuation (. ! ?) or on commas for long clauses
    fragments = [f.strip() for f in re.split(r'[.!?,;]', quote) if len(f.strip()) >= 20]
    for fragment in fragments:
        instances = page.search_for(fragment)
        if instances:
            annot = page.add_highlight_annot(instances)
            annot.set_colors(stroke=color)
            annot.update()
            highlighted = True

    return highlighted


def highlight_text_in_pdf(input_pdf_path: str, output_pdf_path: str, exact_quotes: list):
    """
    Opens the original course PDF and applies highlight
    to every passage that matches an exact_quote from a covered guideline.    
    """
    doc = fitz.open(input_pdf_path)

    # Clean (strip surrounding quote chars) and deduplicate before searching.
    # _clean_quote handles both straight " and curly \u201c\u201d\u2018\u2019 wrappers the LLM adds.
    unique_quotes = list({
        _clean_quote(q)
        for q in exact_quotes
        if q and q.strip() and q.strip().lower() != "none" and _clean_quote(q)
    })

    # Golden yellow
    highlight_color = (1.0, 0.92, 0.23)

    print(f"Highlighting {len(unique_quotes)} unique quote(s) across {len(doc)} page(s)...")

    for page in doc:
        for quote in unique_quotes:
            found = _search_and_highlight_quote(page, quote, highlight_color)
            if found:
                print(f"  ✓ Highlighted on page {page.number + 1}: \"{quote[:60]}...\"")
            else:
                print(f"  ✗ Not found on page {page.number + 1}: \"{quote[:60]}...\"")

    doc.save(output_pdf_path)
    doc.close()


def generate_audit_pdf(audit_results: list, output_path: str):
    """
    Produces the audit report PDF in two sections:

    Summary page created using reportLab
              
    The original course PDF uploaded by the user, with 
    text highlight on every passage that was identified as evidence for a Fully or Partially Covered guideline.
    The formatting are exactly as the user uploaded

    The two parts are merged using PyMuPDF into the single output file.
    """

    # Building the summary page with reportlab
    # We write to a BytesIO buffer in memory rather than a file,
    # because we'll pass it straight to PyMuPDF for merging
    summary_buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        summary_buffer,
        pagesize=letter,
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )
    story = []

    #  Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        fontName='Helvetica-Bold',
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#000000'),
        spaceAfter=8,
        fontName='Helvetica-Bold',
    )
    result_guideline_style = ParagraphStyle(
        'GuidelineText',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        fontName='Helvetica-Bold',
    )
    result_text_style = ParagraphStyle(
        'ResultText',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#000000'),
        spaceAfter=4,
        leftIndent=12,
    )
    summary_style = ParagraphStyle(
        'SummaryStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
    )

    # Coverage counts
    fully_covered    = sum(1 for r in audit_results if "Fully Covered"    in r['match_status'])
    partially_covered = sum(1 for r in audit_results if "Partially Covered" in r['match_status'])
    not_covered      = sum(1 for r in audit_results if "Not Covered"      in r['match_status'])

    # Summary section
    story.append(Paragraph("Curriculum Alignment Audit Report", title_style))
    story.append(Paragraph("Alignment Summary", heading_style))
    story.append(Paragraph(f"<b>Total Guidelines:</b> {len(audit_results)}", summary_style))
    story.append(Paragraph(f"<font color='#21c45d'><b>\u2713 Fully Covered:</b> {fully_covered}</font>", summary_style))
    story.append(Paragraph(f"<font color='#fbbf24'><b>\u25d0 Partially Covered:</b> {partially_covered}</font>", summary_style))
    story.append(Paragraph(f"<font color='#f87171'><b>\u2717 Not Covered:</b> {not_covered}</font>", summary_style))
    story.append(Spacer(1, 0.2 * inch))

    #  Detailed per-guideline results
    story.append(Paragraph("Detailed Results", heading_style))
    for idx, result in enumerate(audit_results, 1):
        story.append(Paragraph(f"<b>{idx}. {result['guideline']}</b>", result_guideline_style))

        status = result['match_status']
        if "Fully Covered" in status:
            status_text = "<font color='#21c45d'><b>\u2713 Fully Covered</b></font>"
        elif "Partially Covered" in status:
            status_text = "<font color='#fbbf24'><b>\u25d0 Partially Covered</b></font>"
        else:
            status_text = "<font color='#f87171'><b>\u2717 Not Covered</b></font>"

        story.append(Paragraph(f"<b>Status:</b> {status_text}", result_text_style))
        story.append(Paragraph(f"<b>Reasoning:</b> {result['reasoning']}", result_text_style))
        story.append(Spacer(1, 0.15 * inch))

    doc.build(story)
    summary_buffer.seek(0)

    #  Annotating the original course PDF with highlights
    # Collecting only the quotes for guidelines that were Fully or Partially Covered
    exact_quotes = [
        r['exact_quote']
        for r in audit_results
        if r.get('exact_quote')
        and r['exact_quote'].strip().lower() != "none"
        and ("Fully Covered" in r['match_status'] or "Partially Covered" in r['match_status'])
    ]

    # Writing the annotated course PDF to a temp path. It will be cleaned up below
    annotated_course_path = output_path + "_course_annotated.pdf"

    if COURSE_PDF_PATH and os.path.exists(COURSE_PDF_PATH):
        highlight_text_in_pdf(COURSE_PDF_PATH, annotated_course_path, exact_quotes)
    else:
        # Safety fallback so that if no course PDF is on disk, insert a blank page instead of crashing
        print("Warning: original course PDF not found, inserting blank placeholder.")
        placeholder = fitz.open()
        placeholder.new_page()
        placeholder.save(annotated_course_path)
        placeholder.close()

    #  Merging the two PDFs into the final output 
    # PyMuPDF's insert_pdf() appends pages from one document into another in memory
    merged = fitz.open()

    # Inserting the reportlab summary page — loaded from the in-memory buffer
    summary_fitz = fitz.open(stream=summary_buffer.read(), filetype="pdf")
    merged.insert_pdf(summary_fitz)
    summary_fitz.close()

    # Appending the annotated original course pages
    course_fitz = fitz.open(annotated_course_path)
    merged.insert_pdf(course_fitz)
    course_fitz.close()

    merged.save(output_path)
    merged.close()

    # Removing the intermediate temp file now that the final PDF is written
    if os.path.exists(annotated_course_path):
        os.remove(annotated_course_path)
