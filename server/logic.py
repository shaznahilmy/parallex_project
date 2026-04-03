import os
import io
import re
import torch
import fitz  # PyMuPDF is used for PDF highlighting and merging
from dotenv import load_dotenv
load_dotenv()

from transformers import AutoTokenizer, AutoModelForSequenceClassification
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# Reportlab is only used to build the summary page 
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.units import inch
from reportlab.lib import colors

# Model Initialisation 
# Models are loaded once globally so they are not reloaded on every API request

token = os.getenv("OPENAI_TOKEN")

print("Loading Embedding Model & LLM Engine...")
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# NLI model — cross-encoder/nli-roberta-base is a lightweight sentence-pair classifier
# trained on MultiNLI + SNLI. It outputs P(entailment), P(neutral), P(contradiction)
# for a (premise, hypothesis) pair. We use P(entailment) as our semantic alignment signal.
# Label order from model config: {0: contradiction, 1: entailment, 2: neutral}
print("Loading NLI Model (cross-encoder/nli-roberta-base)...")
try:
    _nli_tokenizer = AutoTokenizer.from_pretrained("cross-encoder/nli-roberta-base")
    _nli_model = AutoModelForSequenceClassification.from_pretrained("cross-encoder/nli-roberta-base")
    _nli_model.eval()  # disable dropout, inference only
    NLI_AVAILABLE = True
    print("NLI Model loaded.")
except Exception as _nli_load_err:
    print(f"[NLI] WARNING: Could not load NLI model: {_nli_load_err}")
    print("[NLI] entailment_score will default to 0.5 (neutral).")
    NLI_AVAILABLE = False

# Using GitHub Models endpoint
llm_engine = ChatOpenAI(
    # model="gpt-4o-mini",
    # model="gpt-4o",
    model="gpt-4.1-mini",
    api_key=token,
    base_url="https://models.inference.ai.azure.com",
    temperature=0
)

# Path to the FAISS vector index saved during upload
FAISS_INDEX_PATH = "temp/faiss_index"

# Path to the original course PDF uploaded by the user
# Saved during upload so that generate_audit_pdf() can open and highlight it later
COURSE_PDF_PATH = ""

#  Advocate Prompt 
"""
The Advocate is the primary LLM pass. It assesses coverage and scores the
depth of teaching across 3 rubric dimensions in a single call.
"""
prompt_template = """
You are a strict academic auditor. Your job is to verify if specific concepts are explicitly taught in the course content.

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

Semantic Depth Rubric — answer with 0 or 1 ONLY, no extra words:
Criterion-1 (Concept Mentioned): Is the concept name or term explicitly present in the text? [0 or 1]
Criterion-2 (Mechanism Explained): Is the HOW or WHY of the concept explained, not just named? [0 or 1]
Criterion-3 (Example Provided): Is there a concrete example, analogy, code snippet, or demonstration? [0 or 1]
"""
prompt = PromptTemplate(input_variables=["guideline", "context"], template=prompt_template)

#  Adversary Prompt 
"""
The Adversary is a second LLM agent that receives the Advocate's verdict and
actively tries to find flaws in it. It only runs when the Advocate claims
coverage (Fully or Partially), because Not Covered needs no cross-examination.
If it finds a meaningful gap, it outputs DOWNGRADED, which triggers a one-step
downgrade: Fully Covered to Partially Covered, Partially Covered to Not Covered.
"""
adversary_prompt_template = """
You are a strict academic auditor acting as a DEVIL'S ADVOCATE.

GUIDELINE UNDER REVIEW: "{guideline}"

RETRIEVED EVIDENCE:
"{evidence}"

ADVOCATE'S VERDICT: {advocate_status}
ADVOCATE'S REASONING: "{advocate_reasoning}"

Apply DIFFERENT standards depending on the Advocate's verdict:

IF THE VERDICT IS "Fully Covered":
  - You may DOWNGRADE if: the concept is barely mentioned, the mechanism is absent or assumed,
    or the Advocate's reasoning makes logical leaps the evidence does not support.
  - UPHOLD if: the concept, how it works, and at least one concrete application are all present.

IF THE VERDICT IS "Partially Covered":
  - "Partially Covered" already means coverage is incomplete — do NOT penalise it for that.
  - DOWNGRADE ONLY IF: the evidence is essentially a passing mention with no substance —
    no mechanism, no example, just a name drop. That belongs in "Not Covered".
  - UPHOLD if: there is any substantive teaching present, even if the full guideline is not met.

Answer format (no extra text, no preamble):
Verdict: [UPHELD / DOWNGRADED]
Reason: [One sentence explaining your decision]
"""
adversary_prompt = PromptTemplate(
    input_variables=["guideline", "evidence", "advocate_status", "advocate_reasoning"],
    template=adversary_prompt_template
)

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

def _extract_text_with_fitz(pdf_path: str) -> list:
    """
    Extracts text from every page of a PDF using PyMuPDF (fitz) and returns
    a list of LangChain Document objects, one per page.

    Using fitz here (instead of PyPDFLoader/PDFMiner) is intentional:
    fitz is also the engine used by search_for() when applying highlights.
    Extracting and searching with the same engine guarantees the text
    representation is identical, so highlight lookups reliably find matches.
    """
    doc = fitz.open(pdf_path)
    documents = []
    for page_num, page in enumerate(doc):
        text = page.get_text()  # fitz's own text extraction
        if text.strip():        # skip completely blank pages
            documents.append(Document(
                page_content=text,
                metadata={"source": pdf_path, "page": page_num}
            ))
    doc.close()
    return documents


# Loads a guidelines PDF and uses the LLM to extract a list of learning objectives
def extract_guidelines(pdf_path):
    # Using fitz instead of pyPDFLoader
    pages = _extract_text_with_fitz(pdf_path)

    # Combine every page into one string for the LLM to process
    full_text = "\n".join([p.page_content for p in pages])

    final_prompt = extraction_prompt.format(text=full_text)
    print("Extracting guidelines via LLM...")
    response = llm_engine.invoke(final_prompt)
    response = response.content  # Unwrap the message object to get the plain string

    # Parsing the numbered list the LLM returns into a clean Python list
    clean_guidelines = []
    for line in response.split('\n'):
        line = line.strip()
        # Strip leading numbering/bullets (e.g. "1.", "-", "*") so the frontend doesn't double-number
        clean_line = re.sub(r'^(\d+\.|\-|\*)\s*', '', line).strip()
        if len(clean_line) > 10:  # Skipping blank or trivially short lines
            clean_guidelines.append(clean_line)

    return clean_guidelines

"""
    Chunks the uploaded course content PDF into overlapping segments,
    embeds them, and saves a FAISS vector index to disk for later retrieval.
    Also saves the path to the original PDF so it can be annotated at report time.
    """
def build_and_save_faiss(pdf_path):
    global COURSE_PDF_PATH

    # Extract text using fitz, same engine as search_for() used during highlighting
    # so the indexed text and the PDF text layer are guaranteed to be consistent
    docs = _extract_text_with_fitz(pdf_path)

    # Remembering where the original PDF lives as its needed to generate the audit report
    COURSE_PDF_PATH = pdf_path

    # Splitting the document into 500 char chunks with 50 char overlap
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(docs)

    # Building the FAISS index and persisting it so run_analysis() can load it without re embedding
    vector_db = FAISS.from_documents(chunks, embedding_model)
    vector_db.save_local(FAISS_INDEX_PATH)
    return True


def _compute_entailment_score(premise: str, hypothesis: str) -> float:
    """
    Runs cross-encoder/nli-roberta-base on the (premise, hypothesis) pair and
    returns P(entailment) in [0.0, 1.0].

    Premise  = the retrieved course content chunks (what the document teaches).
    Hypothesis = the guideline being audited (what should have been taught).

    The model was trained on MultiNLI + SNLI, so it has seen academic and
    general-domain entailment examples. Label order from the model config:
        index 0 → contradiction
        index 1 → entailment   ← this is what we extract
        index 2 → neutral

    A high score (~0.8+) means the content logically implies the guideline is covered.
    A neutral score (~0.3-0.6) means the content is related but doesn't clearly entail it.
    A low score (~0.0-0.2) alongside high contradiction probability means the content
    actually conflicts with what the guideline expects.
    """
    if not NLI_AVAILABLE:
        return 0.5  # neutral default when model failed to load

    try:
        # Tokenise as a sentence pair; truncate so combined length fits within 512 tokens
        inputs = _nli_tokenizer(
            premise,
            hypothesis,
            return_tensors="pt",
            truncation=True,
            max_length=512,
            padding=False
        )
        with torch.no_grad():
            logits = _nli_model(**inputs).logits          # shape (1, 3)
        probs = torch.softmax(logits, dim=1)[0]           # shape (3,)
        entailment_prob = probs[1].item()                 # index 1 = entailment
        return round(entailment_prob, 4)
    except Exception as e:
        print(f"[NLI] Inference error: {e}")
        return 0.5


def run_analysis(guidelines: list):
    """
    Dual-Agent Adversarial Verification pipeline with Weighted NLI Scoring.

    For each guideline:
      1. FAISS retrieval  — 3 most relevant content chunks
      2. Distance gate    — skips LLM when no chunk is close enough (L2 > 1.1)
      3. NLI scoring      — P(entailment) from cross-encoder/nli-roberta-base
      4. Agent 1 Advocate — coverage verdict + rubric depth scores (C1/C2/C3)
      5. Agent 2 Adversary— cross-examines Advocate; downgrades verdict if flawed

    Final weighted_nli_score:
      0.5 × NLI entailment  +  0.3 × coverage label  +  0.2 × rubric depth
    """
    # Load the FAISS index that was built during the upload 
    vector_db = FAISS.load_local(FAISS_INDEX_PATH, embedding_model, allow_dangerous_deserialization=True)

    audit_results = []

    # L2 distance threshold: anything above 1.1 is considered semantically unrelated. lower means more similar
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
                "evidence_text": "No relevant evidence met the similarity threshold.",
                "adversary_verdict": "N/A",
                "adversary_reason": "",
                "entailment_score": 0.0,
                "weighted_nli_score": 0,
                "rubric": {"concept_mentioned": 0, "mechanism_explained": 0, "example_provided": 0}
            })
            continue

        # Combine the retrieved chunks into a single context string for the LLM
        context_text = "\n".join([doc.page_content for doc, score in results_with_scores])

        """
        Normalise whitespace in the context before passing to the LLM.
        fitz.get_text() inserts \n at every line end, so a phrase spanning two
        lines in the PDF becomes "word1\nword2" in the extracted text. If the LLM
        quotes that phrase it may write "word1 word2" (natural space), and
        search_for() won't find it because the original PDF has a line-break there.
        Collapsing all whitespace runs to a single space means the LLM's quote
        and search_for() are working with the same normalised representation.
        """
        context_text_for_llm = " ".join(context_text.split())

        """
        NLI entailment score that runs before the LLM calls so it is independent.
        Use the normalised context so the NLI text matches what we give the LLM
        """
        entailment_score = _compute_entailment_score(context_text_for_llm, rule)
        print(f"[NLI] P(entailment) for \"{rule[:55]}...\": {entailment_score}")
        
        """
        The Advocate LLM  
        Asks the LLM to assess coverage, provide an exact quote, and score
        the depth of teaching across 3 rubrics
        """
        final_prompt = prompt.format(guideline=rule, context=context_text_for_llm)
        response = llm_engine.invoke(final_prompt).content

        # Parsing the structured Advocate response line by line
        match_status = "Unknown"
        reasoning = "Parsing error"
        exact_quote = "None"
        criterion_1 = 0  # Concept Mentioned
        criterion_2 = 0  # Mechanism Explained
        criterion_3 = 0  # Example Provided

        for line in response.split('\n'):
            line = line.strip()
            if line.startswith("Match:"):
                match_status = line.replace("Match:", "").replace("[", "").replace("]", "").strip()
            elif line.startswith("Reasoning:"):
                reasoning = line.replace("Reasoning:", "").strip()
            elif line.startswith("Exact Quote:"):
                exact_quote = line.replace("Exact Quote:", "").strip()
            elif line.startswith("Criterion-1"):
                criterion_1 = 1 if "1" in line.split(":")[-1] else 0
            elif line.startswith("Criterion-2"):
                criterion_2 = 1 if "1" in line.split(":")[-1] else 0
            elif line.startswith("Criterion-3"):
                criterion_3 = 1 if "1" in line.split(":")[-1] else 0

        """
        Drift score is calculated after the adversary runs (below)
        so it correctly reflects the final match_status, not the Advocate's initial claim.
        """

        """
        The Adversary LLM 
        Only runs when the Advocate claims coverage      
        """
        adversary_verdict = "N/A"
        adversary_reason = ""

        if "Not Covered" not in match_status:
            print(f"[ADVERSARY] Cross-examining: \"{rule[:60]}...\"")
            adv_prompt = adversary_prompt.format(
                guideline=rule,
                evidence=context_text,
                advocate_status=match_status,
                advocate_reasoning=reasoning
            )
            adv_response = llm_engine.invoke(adv_prompt).content

            # Parse the Adversary's verdict and reason
            for line in adv_response.split('\n'):
                line = line.strip()
                if line.startswith("Verdict:"):
                    adversary_verdict = line.replace("Verdict:", "").strip()
                elif line.startswith("Reason:"):
                    adversary_reason = line.replace("Reason:", "").strip()

            # One-step demotion if the Adversary found a flaw, fully to partial and partial to not covered       
            if adversary_verdict == "DOWNGRADED":
                print(f"[ADVERSARY] DOWNGRADED — {adversary_reason}")
                if "Fully Covered" in match_status:
                    match_status = "Partially Covered"
                elif "Partially Covered" in match_status:
                    match_status = "Not Covered"
            else:
                print(f"[ADVERSARY] UPHELD — {adversary_reason}")

        """
        Weighted NLI Score computed after the Adversary finalises match_status.
        Weights are calibrated to reflect actual signal quality in this domain:
        NLI entailment (0.2): cross-encoder/nli-roberta-base was trained on short
        sentence pairs (MultiNLI/SNLI). Applied to chunked
        course content vs guidelines, it consistently scores 1–10% regardless of true coverage
        due to register mismatch. Treated as a weak tiebreaker.
        Coverage label  (0.5): dual-agent LLM verdict — most reliable signal.
        Fully=1.0, Partially=0.5, Not Covered=0.0
        Rubric depth    (0.3): quality of teaching (concept + mechanism + example).
       
        These weights produce intuitive ranges:
        Fully Covered + all rubric criteria met  → ~80%
        Partially Covered + all rubric criteria  → ~55–57%
        Not Covered                              → ~1–5%
        """
        coverage_map = {"Fully Covered": 1.0, "Partially Covered": 0.5, "Not Covered": 0.0}
        coverage_score = coverage_map.get(match_status, 0.0)
        raw_rubric_fraction = (criterion_1 + criterion_2 + criterion_3) / 3

        weighted_nli_score = round(
            (0.2 * entailment_score + 0.5 * coverage_score + 0.3 * raw_rubric_fraction) * 100
        )
        print(f"[SCORE] weighted_nli={weighted_nli_score}% "
              f"(nli={entailment_score:.2f}×0.2, cov={coverage_score}×0.5, rubric={raw_rubric_fraction:.2f}×0.3)")

        audit_results.append({
            "guideline": rule,
            "match_status": match_status,           # final verdict (may be downgraded by Adversary)
            "reasoning": reasoning,
            "exact_quote": exact_quote,
            "evidence_text": context_text,
            "adversary_verdict": adversary_verdict, # "UPHELD" / "DOWNGRADED" / "N/A"
            "adversary_reason": adversary_reason,
            "entailment_score": entailment_score,   # P(entailment) from NLI model, 0.0–1.0
            "weighted_nli_score": weighted_nli_score, # final composite score, 0–100
            "rubric": {
                "concept_mentioned": criterion_1,
                "mechanism_explained": criterion_2,
                "example_provided": criterion_3
            }
        })

    return audit_results


#  PDF Generation

def _clean_quote(quote: str) -> str:
    """
    Strips surrounding quotation marks that the LLM adds around its Exact Quote answer.
    Handles both straight quotes (") and curly/smart quotes (\u201c \u201d \u2018 \u2019).
    Also normalises internal whitespace runs to single spaces so that search_for()
    can match phrases that span line breaks in the original PDF.
    """
    q = quote.strip()
    # Remove matching outer quotes loop so nested pairs are all stripped
    while len(q) >= 2 and q[0] in ('"', '\u201c', '\u2018', "'") and q[-1] in ('"', '\u201d', '\u2019', "'"):
        q = q[1:-1].strip()
    # Collapse any embedded \n / \t / multiple spaces to a single space
    q = " ".join(q.split())
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
