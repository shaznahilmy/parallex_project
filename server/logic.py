import os
import io
import re
import torch
import fitz  # PyMuPDF is used for PDF highlighting and merging
import nltk
from nltk.tokenize import sent_tokenize
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel, Field
from typing import Literal, Optional
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
# embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
embedding_model = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")

print("Loading NLI Model (cross-encoder/nli-deberta-v3-base)...")
try:
    _nli_tokenizer = AutoTokenizer.from_pretrained("cross-encoder/nli-deberta-v3-base")
    _nli_model = AutoModelForSequenceClassification.from_pretrained("cross-encoder/nli-deberta-v3-base")
    _nli_model.eval()  # disable dropout, inference only
    # Resolve label indices dynamically — do not hardcode, ordering can vary across uploads
    _id2label_lower = {v.lower(): k for k, v in _nli_model.config.id2label.items()}
    NLI_ENTAILMENT_IDX    = _id2label_lower.get("entailment", 1)
    NLI_CONTRADICTION_IDX = _id2label_lower.get("contradiction", 0)
    NLI_NEUTRAL_IDX       = _id2label_lower.get("neutral", 2)
    print(f"[NLI] Label map: {_nli_model.config.id2label}")
    print(f"[NLI] Indices → Entailment={NLI_ENTAILMENT_IDX}, Contradiction={NLI_CONTRADICTION_IDX}, Neutral={NLI_NEUTRAL_IDX}")
    NLI_AVAILABLE = True
    print("NLI Model loaded.")
except Exception as _nli_load_err:
    print(f"[NLI] WARNING: Could not load NLI model: {_nli_load_err}")
    print("[NLI] NLI scores will default to neutral (0.5 entailment, 0.0 contradiction).")
    NLI_AVAILABLE = False
    NLI_ENTAILMENT_IDX    = 1
    NLI_CONTRADICTION_IDX = 0
    NLI_NEUTRAL_IDX       = 2

# Using GitHub Models endpoint
llm_engine = ChatOpenAI(
    # model="gpt-4o-mini",
    model="gpt-4o",
    # model="gpt-4.1-mini",
    api_key=token,
    base_url="https://models.inference.ai.azure.com",
    temperature=0
)

# Structured Output Schemas 
# Using Pydantic models to enforce strict JSON output from the LLM
class AdvocateResponse(BaseModel):
    """Schema for the Advocate LLM's coverage assessment."""
    match_status: Literal["Fully Covered", "Partially Covered", "Not Covered"] = Field(
        description="Coverage verdict for the guideline."
    )
    reasoning: str = Field(
        description="Concise explanation of the verdict."
    )
    exact_quote: Optional[str] = Field(
        default=None,
        description="The exact quote from the course content that supports the verdict. Null if Not Covered."
    )
    criterion_1: Literal[0, 1] = Field(
        description="Concept Mentioned: Is the concept name or term explicitly present in the text? 0 or 1."
    )
    criterion_2: Literal[0, 1] = Field(
        description="Mechanism Explained: Is the HOW or WHY of the concept explained? 0 or 1."
    )
    criterion_3: Literal[0, 1] = Field(
        description="Example Provided: Is there a concrete example, analogy, code snippet, or demonstration? 0 or 1."
    )

class AdversaryResponse(BaseModel):
    """Schema for the Adversary LLM's cross-examination verdict."""
    verdict: Literal["UPHELD", "DOWNGRADED"] = Field(
        description="Whether the Advocate's verdict is upheld or downgraded."
    )
    reason: str = Field(
        description="Explaination for the verdict."
    )

# Bind the structured output schemas to the LLM engine.
# with_structured_output() forces the model to return valid JSON conforming to
# the Pydantic schema, eliminating the need for manual string parsing entirely.
advocate_llm  = llm_engine.with_structured_output(AdvocateResponse)
adversary_llm = llm_engine.with_structured_output(AdversaryResponse)

#  Advocate Prompt 
prompt_template = """
You are a strict academic auditor. Your job is to verify if specific concepts are explicitly taught in the course content.

GUIDELINE TO CHECK: "{guideline}"

AVAILABLE COURSE CONTENT: 
"{context}"

INSTRUCTIONS:
1. Determine if the guideline is "Fully Covered", "Partially Covered", or "Not Covered".
2. Provide a concise explanation.
3. You MUST provide the exact quote from the text that proves your decision. If it is Not Covered, set exact_quote to null.

RULES FOR GRADING:
1. **EXACT MATCH REQUIRED:** If the guideline asks for a specific concept (e.g., "Sessions", "Cookies") and the content only talks about generic logic (e.g., "If statements", "Loops"), the answer MUST be "Not Covered".
2. **NO ASSUMPTIONS:** Do not assume students "might" learn it. If the text is missing, it is "Not Covered".
3. **BE HONEST:** It is okay to say "Not Covered".

Semantic Depth Rubric — answer with 0 or 1 ONLY:
criterion_1 (Concept Mentioned): Is the concept name or term explicitly present in the text?
criterion_2 (Mechanism Explained): Is the HOW or WHY of the concept explained, not just named?
criterion_3 (Example Provided): Is there a concrete example, analogy, code snippet, or demonstration?
"""
prompt = PromptTemplate(input_variables=["guideline", "context"], template=prompt_template)

#  Adversary Prompt 
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

"""
    Extracts text from every page of a PDF using PyMuPDF (fitz) and returns
    a list of LangChain Document objects, one per page
    Using fitz here (instead of PyPDFLoader/PDFMiner) is intentional 
    bc fitz is also the engine used by search_for() when applying highlights.
    Extracting and searching with the same engine guarantees the text
    representation is identical, so highlight lookups can find matches
"""
def extract_text(pdf_path: str) -> list:
    
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
   
    pages = extract_text(pdf_path)

    full_text = "\n".join([p.page_content for p in pages])

    final_prompt = extraction_prompt.format(text=full_text)
    print("Extracting guidelines via LLM...")
    response = llm_engine.invoke(final_prompt)
    response = response.content  

    # Parsing the numbered list the LLM returns into a clean Python list
    clean_guidelines = []
    for line in response.split('\n'):
        line = line.strip()
    
        clean_line = re.sub(r'^(\d+\.|\-|\*)\s*', '', line).strip()
        if len(clean_line) > 10:  # Skipping blank lines
            clean_guidelines.append(clean_line)

    return clean_guidelines


"""
    Chunks the uploaded course content PDF into overlapping segments,
    embeds them, and saves a FAISS vector index to disk for later retrieval.
    Returns the session-specific FAISS index path so the caller can pass it
    to run_analysis()
    """
def build_and_save_faiss(pdf_path: str, session_faiss_path: str) -> bool:    
    docs = extract_text(pdf_path)

    # Splitting the document into 500 char chunks with 50 char overlap
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(docs)

    # Building the FAISS index and persisting 
    vector_db = FAISS.from_documents(chunks, embedding_model)
    vector_db.save_local(session_faiss_path)
    return True

#Runs cross-encoder/nli-deberta-v3-base on guideline and exact quote and returns all three NLI probabilities as a dict
def _compute_nli_scores(premise: str, hypothesis: str) -> dict:   

    if not NLI_AVAILABLE:
        return {"entailment": 0.5, "contradiction": 0.0, "neutral": 0.5}

    try:
        # Tokenise as a sentence pair; the exact_quote is short so truncation is rarely needed
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
        return {
            "entailment":    round(probs[NLI_ENTAILMENT_IDX].item(), 4),
            "contradiction": round(probs[NLI_CONTRADICTION_IDX].item(), 4),
            "neutral":       round(probs[NLI_NEUTRAL_IDX].item(), 4),
        }
    except Exception as e:
        print(f"[NLI] Inference error: {e}")
        return {"entailment": 0.5, "contradiction": 0.0, "neutral": 0.5}

#running the dual agent pipeline
def run_analysis(guidelines: list, session_faiss_path: str):     
    vector_db = FAISS.load_local(session_faiss_path, embedding_model, allow_dangerous_deserialization=True)
    audit_results = []
    # L2 distance threshold
    DISTANCE_THRESHOLD = 1.1
    for rule in guidelines:
        # Retrieving the 5 most relevant chunks using MMR      
        results_with_scores = vector_db.similarity_search_with_score(rule, k=1)
        best_match_distance = results_with_scores[0][1]
        results_with_scores = [(doc, 0.0) for doc in vector_db.max_marginal_relevance_search(
            rule, k=5, fetch_k=20, lambda_mult=0.5
        )]
        #Rule based logic
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
                "contradiction_score": 0.0,
                "neutral_score": 0.0,
                "nli_tripwire_fired": False,
                "weighted_nli_score": 0,
                "rubric": {"concept_mentioned": 0, "mechanism_explained": 0, "example_provided": 0}
            })
            continue       
        context_text = "\n".join([doc.page_content for doc, score in results_with_scores])       
        context_text_for_llm = " ".join(context_text.split())
       
        final_prompt = prompt.format(guideline=rule, context=context_text_for_llm)
        advocate_result: AdvocateResponse = advocate_llm.invoke(final_prompt)

        match_status  = advocate_result.match_status
        reasoning     = advocate_result.reasoning
        exact_quote   = advocate_result.exact_quote or "None"
        criterion_1   = advocate_result.criterion_1  # Concept Mentioned
        criterion_2   = advocate_result.criterion_2  # Mechanism Explained
        criterion_3   = advocate_result.criterion_3  # Example Provided

        #NLI Faithfulness Check
        nli_scores = {"entailment": 0.5, "contradiction": 0.0, "neutral": 0.5}  # safe defaults
        has_valid_quote = bool(exact_quote and exact_quote.strip().lower() not in ("none", ""))

        if has_valid_quote and "Not Covered" not in match_status:
            nli_scores = _compute_nli_scores(exact_quote, rule)
            print(
                f"[NLI Faithfulness] "
                f"E={nli_scores['entailment']:.2f}  "
                f"C={nli_scores['contradiction']:.2f}  "
                f"N={nli_scores['neutral']:.2f}  "
                f"| Quote: \"{exact_quote[:60]}...\""
            )
        else:
            print(f"[NLI Faithfulness] Skipped — no valid quote or verdict is 'Not Covered'.")

        #NLI Tripwire
        nli_tripwire = nli_scores["contradiction"] > 0.40
        should_run_adversary = (
            "Not Covered" not in match_status and (
                "Fully Covered" in match_status or  
                nli_tripwire   
            )
        )        
        adversary_verdict = "N/A"
        adversary_reason = ""

        if should_run_adversary:
            trigger_reason = "NLI tripwire (contradiction detected)" if nli_tripwire else "Fully Covered claim"
            print(f"[ADVERSARY] Cross-examining ({trigger_reason}): \"{rule[:60]}...\"")
            adv_prompt = adversary_prompt.format(
                guideline=rule,
                evidence=context_text,
                advocate_status=match_status,
                advocate_reasoning=reasoning
            )
            adv_result: AdversaryResponse = adversary_llm.invoke(adv_prompt)
            adversary_verdict = adv_result.verdict
            adversary_reason  = adv_result.reason

            # One step demotion
            if adversary_verdict == "DOWNGRADED":
                print(f"[ADVERSARY] DOWNGRADED — {adversary_reason}")
                if "Fully Covered" in match_status:
                    match_status = "Partially Covered"
                elif "Partially Covered" in match_status:
                    match_status = "Not Covered"
            else:
                print(f"[ADVERSARY] UPHELD — {adversary_reason}")

        #Weighted Audit Score
        coverage_map = {"Fully Covered": 1.0, "Partially Covered": 0.5, "Not Covered": 0.0}
        coverage_score    = coverage_map.get(match_status, 0.0)
        raw_rubric_fraction = (criterion_1 + criterion_2 + criterion_3) / 3
        entailment_score  = nli_scores["entailment"]

        weighted_nli_score = round(
            (0.40 * entailment_score + 0.40 * coverage_score + 0.20 * raw_rubric_fraction) * 100
        )
        print(
            f"[SCORE] audit_score={weighted_nli_score}% "
            f"(faithfulness={entailment_score:.2f}×0.40, "
            f"coverage={coverage_score}×0.40, "
            f"rubric={raw_rubric_fraction:.2f}×0.20)"
        )

        audit_results.append({
            "guideline": rule,
            "match_status": match_status, # final verdict 
            "reasoning": reasoning,
            "exact_quote": exact_quote,
            "evidence_text": context_text,
            "adversary_verdict": adversary_verdict,
            "adversary_reason": adversary_reason,
            "entailment_score": entailment_score,      # P(entailment) from NLI faithfulness check
            "contradiction_score": nli_scores["contradiction"],  # P(contradiction) tripwire signal
            "neutral_score": nli_scores["neutral"],    # P(neutral)
            "nli_tripwire_fired": nli_tripwire,        # true if NLI forced the Adversary to run
            "weighted_nli_score": weighted_nli_score, 
            "rubric": {
                "concept_mentioned": criterion_1,
                "mechanism_explained": criterion_2,
                "example_provided": criterion_3
            }
        })
    return audit_results


#  PDF Generation
"""
Strips surrounding quotation marks that the LLM adds around its Exact Quote answer.
Handles both straight quotes (") and curly/smart quotes (\u201c \u201d \u2018 \u2019).
Also normalises internal whitespace runs to single spaces so that search_for()
can match phrases that span line breaks in the original PDF.
"""    
def _clean_quote(quote: str) -> str:
   
    q = quote.strip()
    # Remove matching outer quotes loop so nested pairs are all stripped
    while len(q) >= 2 and q[0] in ('"', '\u201c', '\u2018', "'") and q[-1] in ('"', '\u201d', '\u2019', "'"):
        q = q[1:-1].strip()
    # Collapse any embedded \n / \t / multiple spaces to a single space
    q = " ".join(q.split())
    return q

#Attempts to find and highlight a quote on a single PDF page using two strategies
def _search_and_highlight_quote(page, quote: str, color: tuple):    
    highlighted = False

    # Strip any surrounding quotation marks the LLM may have added
    quote = _clean_quote(quote)
    if not quote:
        return False

    # Strategy 1 to try the whole quote first    
    instances = page.search_for(quote)
    if instances:
        annot = page.add_highlight_annot(instances)
        annot.set_colors(stroke=color)
        annot.update()
        return True

    # Strategy 2 to with NLTK span expansion   
    sentences = sent_tokenize(quote)
    processed_spans = set()  # deduplicate: skip spans already highlighted on this page
    for i in range(len(sentences)):
        for j in range(i + 1, len(sentences) + 1):
            span = " ".join(sentences[i:j])
            if len(span) < 20 or span in processed_spans:
                continue
            instances = page.search_for(span)
            if instances:
                annot = page.add_highlight_annot(instances)
                annot.set_colors(stroke=color)
                annot.update()
                processed_spans.add(span)
                highlighted = True
                break  # stop growing once this starting sentence has a match

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

# Produces the audit report PDF
def generate_audit_pdf(audit_results: list, output_path: str, course_pdf_path: str):   

    # Building the summary page with reportlab
    # writing to a BytesIO buffer in memory rather than a file because we'll pass it straight to PyMuPDF for merging
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

    if course_pdf_path and os.path.exists(course_pdf_path):
        highlight_text_in_pdf(course_pdf_path, annotated_course_path, exact_quotes)
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
