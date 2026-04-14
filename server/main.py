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
        "guidelines": clean_guidelines
    }

# ENDPOINT 2 to upload course content
@app.post("/upload-content")
async def upload_content(file: UploadFile = File(...)):
    # Generate a unique session ID for this upload.
    # All downstream calls (run-audit, generate-pdf) must include this ID
    # so they load the correct FAISS index and annotate the correct PDF —
    # even if another user uploads a different document at the same time.
    session_id = str(uuid.uuid4())
    session_dir = os.path.join(TEMP_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    # Save the uploaded PDF under the session directory
    file_path = os.path.join(session_dir, "content.pdf")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Build and persist the FAISS index inside the same session directory
    session_faiss_path = os.path.join(session_dir, "faiss_index")
    logic.build_and_save_faiss(file_path, session_faiss_path)
    
    return {
        "status": "success",
        "session_id": session_id,   # returned to the frontend to include in subsequent requests
        "message": "Course content uploaded and FAISS index built."
    }     


# ENDPOINT 3 to run the comparison
#not needed, the 4th endpoint does all
# @app.post("/run-audit")
# async def run_audit(request: AuditRequest):
#     # Resolve the session-specific paths from the session_id supplied by the frontend.
#     # Using per-session directories means User A's FAISS index and PDF are
#     # completely isolated from User B's, regardless of request timing.
#     session_dir        = os.path.join(TEMP_DIR, request.session_id)
#     session_faiss_path = os.path.join(session_dir, "faiss_index")

#     if not os.path.exists(session_faiss_path):
#         raise HTTPException(status_code=404, detail="Session not found. Please re-upload the course content.")

#     # Passing the JSON list of guidelines into LLM
#     #returns match status, reasonining, quote and score
#     results = logic.run_analysis(request.guidelines, session_faiss_path)
    
#     return {
#         "status": "success",
#         "total_audited": len(request.guidelines),
#         "results": results
#     }


# ENDPOINT 4 to generate the audit PDF and return it as a base64-encoded JSON string and the results
# Using base64 (instead of a binary FileResponse) means:
#   Errors are always clean JSON — never accidentally parsed as a corrupt PDF blob
#   The client can check "status" before attempting to decode
@app.post("/generate-pdf")
async def generate_pdf(request: AuditRequest):
    try:
        # Resolve the session-specific paths from the session_id supplied by the frontend
        session_dir        = os.path.join(TEMP_DIR, request.session_id)
        session_faiss_path = os.path.join(session_dir, "faiss_index")
        course_pdf_path    = os.path.join(session_dir, "content.pdf")

        if not os.path.exists(session_faiss_path):
            raise HTTPException(status_code=404, detail="Session not found. Please re-upload the course content.")

        # Run the analysis (FAISS retrieval + LLM grading)
        results = logic.run_analysis(request.guidelines, session_faiss_path)

        # Write the PDF to a temp file
        current_date = datetime.now().strftime("%B_%d_%Y")
        filename = f"Analysis_Report_{current_date}.pdf"
        pdf_path = os.path.join(session_dir, filename)

        # Pass the session-specific course PDF path so the correct document gets annotated
        logic.generate_audit_pdf(results, pdf_path, course_pdf_path)

        # Read the file and base64 encode it so it travels safely as JSON
        with open(pdf_path, "rb") as f:
            pdf_b64 = base64.b64encode(f.read()).decode("utf-8")

        return {
            "status": "success",
            "filename": filename,
            "results": results,       # structured audit results for the left panel
            "pdf_base64": pdf_b64     # encoded PDF for the right panel
        }

    except Exception as e:
        # Print the full traceback to the server terminal so can debug easily
        traceback.print_exc()
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)