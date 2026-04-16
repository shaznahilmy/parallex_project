"""
conftest.py — Shared pytest fixtures for the Parallex test suite.

Provides:
  - BASE_URL constant for API calls
  - content_pdf_path / guideline_pdf_path helpers
  - A session-scoped fixture that pre-uploads content so audit tests can rely on
    an existing FAISS index without rebuilding it in every test.
"""

import os
import sys
import pytest
import httpx

# Make the project root importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:8000"

# Test PDFs taken from the existing educational dataset (already on disk)
CONTENT_PDF   = os.path.abspath("educational_dataset/cloud.pdf")
GUIDELINE_PDF = os.path.abspath("educational_dataset/webdev.pdf")

# A guideline that IS in the cloud.pdf content (for positive-case tests)
KNOWN_GUIDELINE = "Explain the concept of distributed cloud architecture and its CAP theorem implications"

# A guideline completely unrelated to any course content (for distance-gate tests)
UNRELATED_GUIDELINE = "Calculate the tensile strength of steel-reinforced concrete beams under seismic load"


# ---------------------------------------------------------------------------
# Session fixture — uploads content PDF once so the FAISS index is available
# for all audit tests without repeating the expensive embedding step.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def upload_content_once():
    """Pre-upload the content PDF so FAISS index exists for audit tests."""
    with open(CONTENT_PDF, "rb") as f:
        r = httpx.post(
            f"{BASE_URL}/upload-content",
            files={"file": ("cloud.pdf", f, "application/pdf")},
            timeout=60,
        )
    assert r.status_code == 200, f"Session fixture upload failed: {r.text}"
    yield
