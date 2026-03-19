import os
from dotenv import load_dotenv
load_dotenv()

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
# from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
import re
from langchain_openai import ChatOpenAI
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

token = os.getenv("OPENAI_TOKEN")

#  Initialising Models Globally (so it doesn't reload on every API request)
print("Loading Embedding Model & LLM Engine...")
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
# llm_engine = OllamaLLM(model="llama3.2", temperature=0)
# Using GitHub Models with OpenAI SDK
llm_engine = ChatOpenAI(
    model="gpt-4o-mini",
    # model="gpt-4o",
    api_key=token,  
    base_url="https://models.inference.ai.azure.com",
    temperature=0
)

FAISS_INDEX_PATH = "temp/faiss_index"
# Global variable to store course content
FULL_COURSE_CONTENT = ""

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
    """Uses LLaMA 3.2 to extract guidelines from PDF."""
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    
    # Combining the entire PDF into one string
    full_text = "\n".join([p.page_content for p in pages])
    
    # Passing it to the LLM
    final_prompt = extraction_prompt.format(text=full_text)
    print("Extracting guidelines via LLaMA 3.2...")
    response = llm_engine.invoke(final_prompt)

    #added after the change to the open ai model, as the response format is different
    response = response.content  # extract string from message object
    
    # Parsing the LLM output into a list
    clean_guidelines = []
    
    for line in response.split('\n'):
        line = line.strip()
        # Using regex to strip the numbers or - that the LLM generates so FE gets clean text without double numbering
        clean_line = re.sub(r'^(\d+\.|\-|\*)\s*', '', line).strip()
        
        # Keeping only lines that have substance (i.e removing blank lines)
        if len(clean_line) > 10: 
            clean_guidelines.append(clean_line)
            
    return clean_guidelines

def build_and_save_faiss(pdf_path):
    """Chunks the content PDF and saves a FAISS index to disk."""
    global FULL_COURSE_CONTENT
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    
    # Store the full course content
    FULL_COURSE_CONTENT = "\n".join([doc.page_content for doc in docs])
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(docs)
    
    vector_db = FAISS.from_documents(chunks, embedding_model)
    vector_db.save_local(FAISS_INDEX_PATH)  # Save to disk for the next API call!
    return True

def run_analysis(guidelines: list):
    """Loads FAISS, loops through guidelines, and returns structured JSON results."""
    # Loading the database saved during the upload 
    vector_db = FAISS.load_local(FAISS_INDEX_PATH, embedding_model, allow_dangerous_deserialization=True)
    
    audit_results = []

    # Rule based alignment (L2 Distance)
    # Anything above 1.1 is unrelated text
    DISTANCE_THRESHOLD = 1.1 
    
    for rule in guidelines:
        # Searching with scores now     
        # We use similarity_search_with_score to get the actual mathematical distance
        results_with_scores = vector_db.similarity_search_with_score(rule, k=3)

        # Get the distance of the absolute best match
        best_match_distance = results_with_scores[0][1]
        
        # 2. RULE-BASED ALIGNMENT LOGIC (The "Bouncer")
        if best_match_distance > DISTANCE_THRESHOLD:
            # Short-circuit: The text is too unrelated. Don't even ask the LLM.
            audit_results.append({
                "guideline": rule,
                "match_status": "Not Covered",
                "reasoning": f"System Rule Enforcement: No related content found in the document.",
                # "reasoning": f"System Rule Enforcement: No related content found in the document. (Semantic Distance: {best_match_distance:.2f})",
                "exact_quote": "None",
                "evidence_text": "No relevant evidence met the similarity threshold."
            })
            continue # Skip to the next rule in the loop


       # Extracting just the text from the tuple for the LLM
        context_text = "\n".join([doc.page_content for doc, score in results_with_scores])
        
        # Reasoning
        final_prompt = prompt.format(guideline=rule, context=context_text)
        response = llm_engine.invoke(final_prompt)

        #added after the change to the open ai model, as the response format is different
        response = response.content  # extract string from message object
        
        # Parsinh the LLM output into a clean JSON structure
        match_status = "Unknown"
        reasoning = "Parsing error"
        exact_quote = "None"
        
        # Extracting match and reasoning safely
        for line in response.split('\n'):
            if line.startswith("Match:"):
                match_status = line.replace("Match:", "").replace("[", "").replace("]", "").strip()
            elif line.startswith("Reasoning:"):
                reasoning = line.replace("Reasoning:", "").strip()
            elif line.startswith("Exact Quote:"):
                exact_quote = line.replace("Exact Quote:", "").strip()    
        
        #  Appending to results list
        audit_results.append({
            "guideline": rule,
            "match_status": match_status,
            "reasoning": reasoning,
            "exact_quote": exact_quote,
            "evidence_text": context_text
        })
        
    return audit_results


def generate_audit_pdf(audit_results: list, output_path: str):
    """Generates a PDF report with audit results and highlighted course content."""
    from datetime import datetime
    
    doc = SimpleDocTemplate(output_path, pagesize=letter, rightMargin=0.5*inch, leftMargin=0.5*inch, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    date_style = ParagraphStyle(
        'DateStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        spaceAfter=12,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#000000'),
        spaceAfter=8,
        fontName='Helvetica-Bold'
    )
    
    result_guideline_style = ParagraphStyle(
        'GuidelineText',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        fontName='Helvetica-Bold'
    )
    
    result_text_style = ParagraphStyle(
        'ResultText',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#000000'),
        spaceAfter=4,
        leftIndent=12
    )
    
    quote_style = ParagraphStyle(
        'QuoteStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#333333'),
        backColor=colors.HexColor('#fffacd'),
        spaceAfter=4,
        leftIndent=12,
        rightIndent=12,
        borderPadding=4,
    )
    
    content_style = ParagraphStyle(
        'ContentStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        alignment=4,  # Justify
    )
    
    # Add title
    story.append(Paragraph("Curriculum Alignment Audit Report", title_style)) 
    
    # Add audit results summary section
    story.append(Paragraph("Alignment Summary", heading_style))
    
    # Count coverage status
    fully_covered = sum(1 for r in audit_results if "Fully Covered" in r['match_status'])
    partially_covered = sum(1 for r in audit_results if "Partially Covered" in r['match_status'])
    not_covered = sum(1 for r in audit_results if "Not Covered" in r['match_status'])
    
    summary_style = ParagraphStyle(
        'SummaryStyle',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
    )
    
    story.append(Paragraph(f"<b>Total Guidelines:</b> {len(audit_results)}", summary_style))
    story.append(Paragraph(f"<font color='#21c45d'><b>✓ Fully Covered:</b> {fully_covered}</font>", summary_style))
    story.append(Paragraph(f"<font color='#fbbf24'><b>◐ Partially Covered:</b> {partially_covered}</font>", summary_style))
    story.append(Paragraph(f"<font color='#f87171'><b>✗ Not Covered:</b> {not_covered}</font>", summary_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Add detailed results
    story.append(Paragraph("Detailed Results", heading_style))
    
    for idx, result in enumerate(audit_results, 1):
        # Guideline
        story.append(Paragraph(f"<b>{idx}. {result['guideline']}</b>", result_guideline_style))
        
        # Status with color coding
        status = result['match_status']
        if "Fully Covered" in status:
            status_text = f"<font color='#21c45d'><b>✓ Fully Covered</b></font>"
        elif "Partially Covered" in status:
            status_text = f"<font color='#fbbf24'><b>◐ Partially Covered</b></font>"
        else:
            status_text = f"<font color='#f87171'><b>✗ Not Covered</b></font>"
        
        story.append(Paragraph(f"<b>Status:</b> {status_text}", result_text_style))
        story.append(Paragraph(f"<b>Reasoning:</b> {result['reasoning']}", result_text_style))     
    
        
        story.append(Spacer(1, 0.15*inch))
    
    # Add page break before course content
    story.append(PageBreak())
    
    # Add course content section
    story.append(Paragraph("Course Content", heading_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Create content with highlighting for covered guidelines
    covered_quotes = set()
    for result in audit_results:
        if result['match_status'] and ("Fully Covered" in result['match_status'] or "Partially Covered" in result['match_status']):
            if result['exact_quote'] and result['exact_quote'] != "None":
                covered_quotes.add(result['exact_quote'])
    
    # Display course content with highlighted sections
    if FULL_COURSE_CONTENT:
        # Split content into paragraphs for better formatting
        paragraphs = FULL_COURSE_CONTENT.split('\n\n')
        
        for para in paragraphs:
            if para.strip():
                # Check if this paragraph contains any covered content
                para_text = para.strip()
                contains_covered = any(quote in para_text for quote in covered_quotes)
                
                # Highlight covered sections with background
                highlighted_para = para_text
                for quote in covered_quotes:
                    if quote in highlighted_para:
                        # Add highlighting with yellow background
                        highlighted_para = highlighted_para.replace(
                            quote,
                            f'<font backColor="#ffff99">{quote}</font>'
                        )
                
                # Add paragraph with appropriate styling
                if contains_covered:
                    story.append(Paragraph(highlighted_para.replace("\n", "<br/>"), quote_style))
                else:
                    story.append(Paragraph(highlighted_para.replace("\n", "<br/>"), content_style))
                
                story.append(Spacer(1, 0.1*inch))
    
    # Build PDF
    doc.build(story)


