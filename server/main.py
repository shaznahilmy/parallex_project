import os
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from langchain_community.document_loaders import PyPDFLoader
from pydantic import BaseModel
from typing import List

from server import logic

#  Initialising app
app = FastAPI(title="Parallex API")

#  Setting up CORS 
app.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"], 
     allow_origins=["http://localhost:5173"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)

#  Creating a temporary folder to store uploaded PDFs
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Defining the expected JSON body for the audit endpoint
class AuditRequest(BaseModel):
    guidelines: List[str]

#ENDPOINT 1 to upload guildline
@app.post("/upload-guidelines")
async def upload_guidelines(file: UploadFile = File(...)):
    # Saving the file to the temp folder
    file_path = os.path.join(TEMP_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    clean_guidelines = logic.extract_guidelines(file_path)          
           
    # Returning the clean list as a JSON array
    return {
        "status": "success",
        "filename": file.filename,
        "extracted_count": len(clean_guidelines),
        "guidelines": clean_guidelines
    }

# ENDPOINT 2 to upload course content
@app.post("/upload-content")
async def upload_content(file: UploadFile = File(...)):
    #saving the file
    file_path = os.path.join(TEMP_DIR, "content.pdf") 
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Triggering the FAISS indexing immediately after upload
    logic.build_and_save_faiss(file_path)
    
    return {
        "status": "success",
        "message": "Course content uploaded and FAISS index built."
    }     


# ENDPOINT 3 to run the comparison
@app.post("/run-audit")
async def run_audit(request: AuditRequest):
    # Passing the JSON list of guidelines into LLaMA 
    results = logic.run_analysis(request.guidelines)
    
    return {
        "status": "success",
        "total_audited": len(request.guidelines),
        "results": results
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)