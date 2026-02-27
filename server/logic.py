import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

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
    
    for rule in guidelines:
        # Searching
        results = vector_db.similarity_search(rule, k=3)
        context_text = "\n".join([doc.page_content for doc in results])
        
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