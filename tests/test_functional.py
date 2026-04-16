"""
test_functional.py — Functional (API integration) tests for the Parallex FastAPI server.
Tests the live server at http://localhost:8000 using httpx.

Mapped to Functional Requirements (FR01–FR08) from the thesis MoSCoW table.

Test IDs:
  TC-F01  POST /upload-guidelines → extracts guidelines list            (FR01, FR02)
  TC-F02  POST /upload-content    → FAISS index built successfully      (FR01, FR04, FR05)
  TC-F03  POST /run-audit         → returns structured audit results    (FR06, FR07, FR08)
  TC-F04  Coverage label values are valid                               (FR07)
  TC-F05  POST /generate-pdf      → returns base64 PDF                  (FR01, FR07, FR08)
  TC-F06  Generated PDF bytes start with PDF magic bytes                (FR08)
  TC-F07  Adversary verdict field present in all results                (FR07)
  TC-F08  Semantic Drift Score in valid range 0-100                     (FR08, NFR05)
  TC-F09  Rubric dict returned with correct keys                        (FR08, NFR05)
  TC-F10  Unrelated guideline is classified as Not Covered (dist. gate) (FR07)
  TC-F11  User can select subset of guidelines (empty list → empty res) (FR03)
  TC-F12  Re-upload content → FAISS rebuilds, audit still works          (FR04, FR05)
"""

import os
import sys
import base64

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import BASE_URL, CONTENT_PDF, GUIDELINE_PDF, KNOWN_GUIDELINE, UNRELATED_GUIDELINE

TIMEOUT = 90  # seconds — LLM calls can be slow


# ---------------------------------------------------------------------------
# TC-F01 — Upload Guidelines PDF → guidelines extracted   (FR01, FR02)
# ---------------------------------------------------------------------------
def test_upload_guidelines_extracts_list():
    """TC-F01: FR01 + FR02 — Uploading a guideline PDF must return a non-empty
    guidelines list with status 'success'."""
    with open(GUIDELINE_PDF, "rb") as f:
        r = httpx.post(
            f"{BASE_URL}/upload-guidelines",
            files={"file": ("webdev.pdf", f, "application/pdf")},
            timeout=TIMEOUT,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert isinstance(data["guidelines"], list)
    assert len(data["guidelines"]) > 0
    assert data["extracted_count"] == len(data["guidelines"])


# ---------------------------------------------------------------------------
# TC-F02 — Upload Course Content PDF → FAISS index built  (FR01, FR04, FR05)
# ---------------------------------------------------------------------------
def test_upload_content_builds_faiss_index():
    """TC-F02: FR01 + FR04 + FR05 — Uploading a course content PDF must return
    'success' and a FAISS index must be persisted to disk."""
    with open(CONTENT_PDF, "rb") as f:
        r = httpx.post(
            f"{BASE_URL}/upload-content",
            files={"file": ("cloud.pdf", f, "application/pdf")},
            timeout=TIMEOUT,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    # FAISS index must have been written to disk
    assert os.path.isdir("temp/faiss_index"), "FAISS index directory was not created"
    assert any(
        fname.endswith(".faiss") for fname in os.listdir("temp/faiss_index")
    ), "No .faiss file found inside temp/faiss_index"


# ---------------------------------------------------------------------------
# TC-F03 — Run Audit → structured results returned        (FR06, FR07, FR08)
# ---------------------------------------------------------------------------
def test_run_audit_returns_structured_results():
    """TC-F03: FR06 + FR07 + FR08 — /run-audit must return a list of results,
    each containing match_status, reasoning, and exact_quote."""
    r = httpx.post(
        f"{BASE_URL}/run-audit",
        json={"guidelines": [KNOWN_GUIDELINE]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert isinstance(data["results"], list)
    assert len(data["results"]) == 1

    result = data["results"][0]
    assert "match_status" in result    # FR07 — coverage gap identification
    assert "reasoning" in result       # FR08 — explanation for decision
    assert "exact_quote" in result     # FR08 — evidence transparency
    assert "guideline" in result


# ---------------------------------------------------------------------------
# TC-F04 — Coverage labels are valid enum values           (FR07)
# ---------------------------------------------------------------------------
def test_coverage_labels_are_valid():
    """TC-F04: FR07 — Every match_status value must belong to the three
    defined coverage categories."""
    VALID_LABELS = {"Fully Covered", "Partially Covered", "Not Covered"}
    guidelines = [KNOWN_GUIDELINE, UNRELATED_GUIDELINE]
    r = httpx.post(
        f"{BASE_URL}/run-audit",
        json={"guidelines": guidelines},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    for result in r.json()["results"]:
        assert result["match_status"] in VALID_LABELS, (
            f"Invalid match_status: {result['match_status']}"
        )


# ---------------------------------------------------------------------------
# TC-F05 — Generate PDF → base64 string returned          (FR01, FR07, FR08)
# ---------------------------------------------------------------------------
def test_generate_pdf_returns_base64_string():
    """TC-F05: FR08 — /generate-pdf must return a non-empty base64-encoded PDF
    and structured audit results in the same response."""
    r = httpx.post(
        f"{BASE_URL}/generate-pdf",
        json={"guidelines": [KNOWN_GUIDELINE]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert "pdf_base64" in data
    assert isinstance(data["pdf_base64"], str)
    assert len(data["pdf_base64"]) > 100   # must be a non-trivial base64 string
    assert "results" in data               # structured results also returned


# ---------------------------------------------------------------------------
# TC-F06 — Decoded PDF bytes start with PDF magic bytes   (FR08)
# ---------------------------------------------------------------------------
def test_generated_pdf_is_valid_pdf():
    """TC-F06: FR08 — The base64 payload from /generate-pdf must decode to a
    valid PDF file (starts with the %PDF magic byte sequence)."""
    r = httpx.post(
        f"{BASE_URL}/generate-pdf",
        json={"guidelines": [KNOWN_GUIDELINE]},
        timeout=TIMEOUT,
    )
    data = r.json()
    assert data["status"] == "success"
    raw_bytes = base64.b64decode(data["pdf_base64"])
    assert raw_bytes[:4] == b"%PDF", (
        "Decoded base64 payload does not start with %PDF — not a valid PDF file"
    )


# ---------------------------------------------------------------------------
# TC-F07 — Adversary verdict field present in all results  (FR07)
# ---------------------------------------------------------------------------
def test_adversary_verdict_field_present():
    """TC-F07: FR07 — Dual-agent verification must return an adversary_verdict
    key for every result. Value must be UPHELD, DOWNGRADED, or N/A."""
    r = httpx.post(
        f"{BASE_URL}/run-audit",
        json={"guidelines": [KNOWN_GUIDELINE, UNRELATED_GUIDELINE]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    VALID_VERDICTS = {"UPHELD", "DOWNGRADED", "N/A"}
    for result in r.json()["results"]:
        assert "adversary_verdict" in result
        assert result["adversary_verdict"] in VALID_VERDICTS, (
            f"Unexpected adversary_verdict: {result['adversary_verdict']}"
        )


# ---------------------------------------------------------------------------
# TC-F08 — Semantic Drift Score in valid range 0–100       (FR08, NFR05)
# ---------------------------------------------------------------------------
def test_semantic_drift_score_in_valid_range():
    """TC-F08: FR08 + NFR05 — semantic_drift_score must be an integer in [0, 100]."""
    r = httpx.post(
        f"{BASE_URL}/run-audit",
        json={"guidelines": [KNOWN_GUIDELINE, UNRELATED_GUIDELINE]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    for result in r.json()["results"]:
        score = result.get("semantic_drift_score")
        assert isinstance(score, (int, float)), "semantic_drift_score must be numeric"
        assert 0 <= score <= 100, f"Score out of range: {score}"


# ---------------------------------------------------------------------------
# TC-F09 — Rubric dict has correct keys                    (FR08, NFR05)
# ---------------------------------------------------------------------------
def test_rubric_dict_has_correct_keys():
    """TC-F09: FR08 + NFR05 — Each result must include a 'rubric' dict with
    the three teaching-depth criteria keys."""
    r = httpx.post(
        f"{BASE_URL}/run-audit",
        json={"guidelines": [KNOWN_GUIDELINE]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    rubric = r.json()["results"][0]["rubric"]
    assert set(rubric.keys()) == {"concept_mentioned", "mechanism_explained", "example_provided"}
    for v in rubric.values():
        assert v in (0, 1), f"Rubric value must be 0 or 1, got {v}"


# ---------------------------------------------------------------------------
# TC-F10 — Unrelated guideline → Not Covered via distance gate  (FR07)
# ---------------------------------------------------------------------------
def test_unrelated_guideline_classified_not_covered():
    """TC-F10: FR07 — A guideline from a completely different domain must be
    blocked by the FAISS distance gate and classified as Not Covered without
    LLM invocation. Verifies the accuracy safety net (NFR02)."""
    r = httpx.post(
        f"{BASE_URL}/run-audit",
        json={"guidelines": [UNRELATED_GUIDELINE]},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200
    result = r.json()["results"][0]
    assert result["match_status"] == "Not Covered"
    # Distance gate produces N/A adversary verdict (LLM never called)
    assert result["adversary_verdict"] == "N/A"
    assert result["semantic_drift_score"] == 0


# ---------------------------------------------------------------------------
# TC-F11 — Empty guidelines list → empty results, no crash  (FR03)
# ---------------------------------------------------------------------------
def test_empty_guidelines_list_returns_empty_results():
    """TC-F11: FR03 — If user deselects all guidelines and submits, the API
    must return an empty results list without error."""
    r = httpx.post(
        f"{BASE_URL}/run-audit",
        json={"guidelines": []},
        timeout=30,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["results"] == []


# ---------------------------------------------------------------------------
# TC-F12 — Re-upload content → FAISS rebuilt, audit still works  (FR04, FR05)
# ---------------------------------------------------------------------------
def test_re_upload_content_refreshes_faiss_index():
    """TC-F12: FR04 + FR05 — Re-uploading a new course content PDF must rebuild
    the FAISS index and subsequent audit must still return valid results."""
    # Upload a different course content PDF
    alt_pdf = "educational_dataset/nlp.pdf"
    with open(alt_pdf, "rb") as f:
        upload_r = httpx.post(
            f"{BASE_URL}/upload-content",
            files={"file": ("nlp.pdf", f, "application/pdf")},
            timeout=TIMEOUT,
        )
    assert upload_r.status_code == 200
    assert upload_r.json()["status"] == "success"

    # Audit should still work with the new index
    audit_r = httpx.post(
        f"{BASE_URL}/run-audit",
        json={"guidelines": ["Explain the mathematical mechanics of the Attention mechanism using Query, Key, and Value matrices"]},
        timeout=TIMEOUT,
    )
    assert audit_r.status_code == 200
    results = audit_r.json()["results"]
    assert len(results) == 1
    assert results[0]["match_status"] in {"Fully Covered", "Partially Covered", "Not Covered"}
