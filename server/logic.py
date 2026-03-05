import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
import re

#  Initialising Models Globally (so it doesn't reload on every API request)
print("Loading Embedding Model & LLM Engine...")
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
llm_engine = OllamaLLM(model="llama3.2", temperature=0)

FAISS_INDEX_PATH = "temp/faiss_index"

prompt_template = """
You are a strict academic auditor. Your job is to verify if specific are explicitly taught in the course content.

GUIDELINE TO CHECK: "{guideline}"

AVAILABLE COURSE CONTENT: 
"{context}"

INSTRUCTIONS:
1. Determine if the guideline is "Fully Covered", "Partially Covered", or "Not Covered".
2. Start your response with exactly "Match: [Status]".
3. Provide a concise explanation.

RULES FOR GRADING:
1. **EXACT MATCH REQUIRED:** If the guideline asks for a specific concept (e.g., "Sessions", "Cookies") and the content only talks about generic logic (e.g., "If statements", "Loops"), the answer MUST be "Not Covered".
2. **NO ASSUMPTIONS:** Do not assume students "might" learn it. If the text is missing, it is "Not Covered".
3. **BE HONEST:** It is okay to say "Not Covered".

Answer format:
Match: [Fully Covered / Partially Covered / Not Covered]
Reasoning: [Explanation]
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
    
    # Parsing the LLM output into a list
    clean_guidelines = []
    
    for line in response.split('\n'):
        line = line.strip()
        # Using regex to strip the "1. ", "2. ", or "- " that the LLM generates so FE gets clean text without double numbering
        clean_line = re.sub(r'^(\d+\.|\-|\*)\s*', '', line).strip()
        
        # Keeping only lines that have substance (i.e removing blank lines)
        if len(clean_line) > 10: 
            clean_guidelines.append(clean_line)
            
    return clean_guidelines

def build_and_save_faiss(pdf_path):
    """Chunks the content PDF and saves a FAISS index to disk."""
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    
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
                "reasoning": f"System Rule Enforcement: No related content found in the document. (Semantic Distance: {best_match_distance:.2f})",
                "evidence_text": "No relevant evidence met the similarity threshold."
            })
            continue # Skip to the next rule in the loop


       # Extracting just the text from the tuple for the LLM
        context_text = "\n".join([doc.page_content for doc in results_with_scores])
        
        # Reasoning
        final_prompt = prompt.format(guideline=rule, context=context_text)
        response = llm_engine.invoke(final_prompt)
        
        # Parsinh the LLM output into a clean JSON structure
        match_status = "Unknown"
        reasoning = response
        
        # Extracting match and reasoning safely
        for line in response.split('\n'):
            if line.startswith("Match:"):
                match_status = line.replace("Match:", "").replace("[", "").replace("]", "").strip()
            elif line.startswith("Reasoning:"):
                reasoning = line.replace("Reasoning:", "").strip()
        
        if reasoning == response and "Reasoning:" in response:
            reasoning = response.split("Reasoning:")[-1].strip()

        #  Appending to results list
        audit_results.append({
            "guideline": rule,
            "match_status": match_status,
            "reasoning": reasoning,
            "evidence_text": context_text
        })
        
    return audit_results


