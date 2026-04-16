import os
import uuid
import base64
#to save uploaded files
import shutil
import traceback
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
#allows fe to call be
from fastapi.middleware.cors import CORSMiddleware
#validates incoming json
from pydantic import BaseModel
#for type hinting
from typing import List

from server import logic

#  Initialising app (creates API server)
app = FastAPI(title="Parallex API")

#  Setting up CORS 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
    # session_id ties every request to the FAISS index and PDF uploaded at /upload-content.
    # Each upload generates a fresh UUID so concurrent users never share state.
    session_id: str

#ENDPOINT 1 to upload guideline
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
        "guidelines": clean_guidelines,
    }

# ENDPOINT 2 to upload course content
@app.post("/upload-content")
async def upload_content(file: UploadFile = File(...)):
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(TEMP_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    # Saving the uploaded PDF under the session directory
    file_path = os.path.join(session_dir, "content.pdf")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    session_faiss_path = os.path.join(session_dir, "faiss_index")
    logic.build_and_save_faiss(file_path, session_faiss_path)

    return {
        "status": "success",
        "session_id": session_id,
        "message": "Course content uploaded and FAISS index built.",
    }


@app.post("/generate-pdf")
async def generate_pdf(request: AuditRequest):
    try:
        # Resolving the session specific paths from the fe session id
        session_dir        = os.path.join(TEMP_DIR, request.session_id)
        session_faiss_path = os.path.join(session_dir, "faiss_index")
        course_pdf_path = os.path.join(session_dir, "content.pdf")

        if not os.path.exists(session_faiss_path):
            raise HTTPException(
                status_code=404,
                detail="Session not found. Please re-upload the course content.",
            )

        results = logic.run_analysis(request.guidelines, session_faiss_path)

        # Writing the PDF to a temp file
        current_date = datetime.now().strftime("%B_%d_%Y")
        filename = f"Analysis_Report_{current_date}.pdf"
        pdf_path = os.path.join(session_dir, filename)

        logic.generate_audit_pdf(results, pdf_path, course_pdf_path)

        # Reading the file and base64 encoding it 
        with open(pdf_path, "rb") as f:
            pdf_b64 = base64.b64encode(f.read()).decode("utf-8")

        return {
            "status": "success",
            "filename": filename,
            "results": results,
            "pdf_base64": pdf_b64,
        }

    except Exception as e:
        # Printing the full traceback to the server terminal for debugging
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e),
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)