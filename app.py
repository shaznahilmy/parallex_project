import streamlit as st
import os
import tempfile
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

st.set_page_config(page_title="Parallex: Syllabus Auditor", page_icon="🎓", layout="wide")

st.title("🎓 Parallex: Automated Curriculum Auditor")
st.markdown("### Cross-Document Semantic Analysis System")
st.markdown("Upload your **Course Content** and **Guidelines** to check for compliance.")

# using @st.cache_resource so the model loads once and stays in memory
@st.cache_resource
def load_resources():
    print("Loading Embedding Model...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    print("Connecting to Ollama...")

    llm = OllamaLLM(model="llama3.2", temperature=0) 
    
    return embeddings, llm

# Loading models
embedding_model, llm_engine = load_resources()

# helper functions
def process_pdf(uploaded_file):
    """Saves uploaded file to temp disk so PyPDFLoader can read it."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name
    return tmp_path

def extract_guidelines(pdf_path):
    """Extracts text from PDF and cleans up junk lines."""
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()
    full_text = "\n".join([p.page_content for p in pages])    

    raw_lines = full_text.split('\n')
    clean_guidelines = []
    
    for line in raw_lines:
        line = line.strip()
        # Skipping empty or too short lines
        if len(line) < 10: 
            continue
        # Skipping incomplete sentences (ending in ;)
        if line.endswith(";"): 
            continue
        # Skipping common headers
        if "students will be able to" in line.lower(): 
            continue
        
        clean_guidelines.append(line)
        
    return clean_guidelines

def create_vector_db(pdf_path):
    """Chunks the content PDF and builds a fresh FAISS index."""
    loader = PyPDFLoader(pdf_path)
    docs = loader.load()
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(docs)
    
    vector_db = FAISS.from_documents(chunks, embedding_model)
    return vector_db

prompt_template = """
You are a strict academic auditor. Your job is to verify if specific technical topics are explicitly taught in the course content.

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

# UI and logic
col1, col2 = st.columns(2)

with col1:
    st.info("📂 **Step 1: Upload Course Content** (Lecture Notes)")
    content_file = st.file_uploader("Drop Lecture PDF", type=["pdf"], key="content")

with col2:
    st.info("📋 **Step 2: Upload Guidelines** (Syllabus/Standards)")
    guideline_file = st.file_uploader("Drop Guideline PDF", type=["pdf"], key="guideline")

if st.button("🚀 Check Alignment", type="primary"):
    if not content_file or not guideline_file:
        st.error("Please upload both documents first!")
    else:
        # A. Processing Files
        with st.spinner("Processing Documents..."):
            content_path = process_pdf(content_file)
            guideline_path = process_pdf(guideline_file)
            
            # Building DB from the uploaded content
            vector_db = create_vector_db(content_path)
            
            # Extracting guidelines
            guidelines = extract_guidelines(guideline_path)
            st.success(f"Extracted {len(guidelines)} valid guidelines.")
        
        # Analysis Loop
        st.subheader("📝 Analysis")
        progress_bar = st.progress(0)
        
        for i, rule in enumerate(guidelines):
            # Updating Progress
            progress_bar.progress((i + 1) / len(guidelines))
            
            #  Searching the db for similar vectors
            results = vector_db.similarity_search(rule, k=3)
            context_text = "\n".join([doc.page_content for doc in results])
            
            #  Reasoning with llm
            final_prompt = prompt.format(guideline=rule, context=context_text)
            response = llm_engine.invoke(final_prompt)
            
            # assigning status colours for output
            status_color = "gray"
            if "Fully Covered" in response:
                status_color = "green"
            elif "Partially Covered" in response:
                status_color = "orange"
            elif "Not Covered" in response:
                status_color = "red"
            
            #  Displaying Result Card
            with st.expander(f"{rule}", expanded=True):
                st.markdown(f":{status_color}[**{response.splitlines()[0]}**]") # The Matching line
                st.markdown(f"_{response.split('Reasoning:')[-1].strip()}_")   # The Reasoning
                with st.expander("View Source Evidence"):
                    st.text(context_text)
                    
        # Cleaning up temp files
        os.remove(content_path)
        os.remove(guideline_path)
        st.success("Analysis Complete!")