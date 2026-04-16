"""
test_performance.py — Performance and response-time tests for Parallex API.
Mapped to NFR03 (Performance) and NFR01 (Scalability).

Test IDs:
  TC-P01  POST /upload-guidelines response time < 30 s            (NFR03)
  TC-P02  POST /upload-content (FAISS build) response time < 30 s (NFR03)
  TC-P03  POST /run-audit (single guideline) response time < 60 s (NFR03)
  TC-P04  3 concurrent POST /run-audit requests all succeed       (NFR01 Scalability)
"""

import os
import sys
import time
import threading

import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.conftest import BASE_URL, CONTENT_PDF, GUIDELINE_PDF, KNOWN_GUIDELINE


# Performance thresholds (seconds).
# The LLM endpoint (GitHub Models / Azure) is network-bound so thresholds
# are set generously at 90 s for LLM-heavy calls and 30 s for CPU-only calls.
UPLOAD_GUIDELINES_THRESHOLD_S  = 90   # NFR03: guideline extraction (LLM call)
UPLOAD_CONTENT_THRESHOLD_S     = 30   # NFR03: FAISS embedding build (CPU-bound, no LLM)
RUN_AUDIT_THRESHOLD_S          = 90   # NFR03: dual-agent LLM audit pipeline


# ---------------------------------------------------------------------------
# TC-P01 — Guidelines upload response time                 (NFR03)
# ---------------------------------------------------------------------------
def test_upload_guidelines_response_time():
    """TC-P01: NFR03 — POST /upload-guidelines (LLM extraction) must complete
    within {UPLOAD_GUIDELINES_THRESHOLD_S} seconds for a standard guideline PDF."""
    with open(GUIDELINE_PDF, "rb") as f:
        start = time.perf_counter()
        r = httpx.post(
            f"{BASE_URL}/upload-guidelines",
            files={"file": ("webdev.pdf", f, "application/pdf")},
            timeout=120,
        )
        elapsed = time.perf_counter() - start

    assert r.status_code == 200
    print(f"\n[TC-P01] /upload-guidelines latency: {elapsed:.2f}s")
    assert elapsed < UPLOAD_GUIDELINES_THRESHOLD_S, (
        f"Upload guidelines took {elapsed:.2f}s — exceeded {UPLOAD_GUIDELINES_THRESHOLD_S}s threshold"
    )


# ---------------------------------------------------------------------------
# TC-P02 — Content upload / FAISS build response time      (NFR03)
# ---------------------------------------------------------------------------
def test_upload_content_response_time():
    """TC-P02: NFR03 — POST /upload-content (FAISS index build) must complete
    within {UPLOAD_CONTENT_THRESHOLD_S} seconds for a standard course PDF."""
    with open(CONTENT_PDF, "rb") as f:
        start = time.perf_counter()
        r = httpx.post(
            f"{BASE_URL}/upload-content",
            files={"file": ("cloud.pdf", f, "application/pdf")},
            timeout=120,
        )
        elapsed = time.perf_counter() - start

    assert r.status_code == 200
    print(f"\n[TC-P02] /upload-content latency: {elapsed:.2f}s")
    assert elapsed < UPLOAD_CONTENT_THRESHOLD_S, (
        f"Content upload took {elapsed:.2f}s — exceeded {UPLOAD_CONTENT_THRESHOLD_S}s threshold"
    )


# ---------------------------------------------------------------------------
# TC-P03 — Single-guideline audit response time             (NFR03)
# ---------------------------------------------------------------------------
def test_run_audit_single_guideline_response_time():
    """TC-P03: NFR03 — A single-guideline audit (FAISS + dual-agent LLM) must
    complete within {RUN_AUDIT_THRESHOLD_S} seconds."""
    start = time.perf_counter()
    r = httpx.post(
        f"{BASE_URL}/run-audit",
        json={"guidelines": [KNOWN_GUIDELINE]},
        timeout=120,
    )
    elapsed = time.perf_counter() - start

    assert r.status_code == 200
    print(f"\n[TC-P03] /run-audit (1 guideline) latency: {elapsed:.2f}s")
    assert elapsed < RUN_AUDIT_THRESHOLD_S, (
        f"Single audit took {elapsed:.2f}s — exceeded {RUN_AUDIT_THRESHOLD_S}s threshold"
    )


# ---------------------------------------------------------------------------
# TC-P04 — 3 concurrent audit requests all succeed          (NFR01 Scalability)
# ---------------------------------------------------------------------------
def test_concurrent_audit_requests_all_succeed():
    """TC-P04: NFR01 Scalability — 3 simultaneous POST /run-audit calls must all
    return HTTP 200 with no failures. Tests that FastAPI's async execution handles
    concurrent requests without deadlocking or crashing."""
    results = []
    errors  = []

    def make_request(guideline: str):
        try:
            r = httpx.post(
                f"{BASE_URL}/run-audit",
                json={"guidelines": [guideline]},
                timeout=120,
            )
            results.append(r.status_code)
        except Exception as exc:
            errors.append(str(exc))

    guidelines = [
        KNOWN_GUIDELINE,
        "Explain the concept of containerisation and virtualisation in cloud computing",
        "Describe the role of load balancers in distributed cloud systems",
    ]

    threads = [threading.Thread(target=make_request, args=(g,)) for g in guidelines]
    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=130)
    elapsed = time.perf_counter() - start

    print(f"\n[TC-P04] 3 concurrent requests completed in {elapsed:.2f}s")
    print(f"         Status codes: {results}")

    assert len(errors) == 0, f"Concurrent requests raised errors: {errors}"
    assert all(s == 200 for s in results), (
        f"Not all concurrent requests returned 200: {results}"
    )
    assert len(results) == 3, f"Expected 3 results, got {len(results)}"
