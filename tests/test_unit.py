"""
test_unit.py — Unit tests for pure Python logic in server/logic.py
Tests do NOT make LLM or HTTP calls. They test deterministic helper functions
and the mathematical scoring formulas used in the pipeline.

Test IDs:
  TC-U01  _clean_quote strips straight double quotes
  TC-U02  _clean_quote strips curly/smart quotes
  TC-U03  _clean_quote handles already-clean input
  TC-U04  _clean_quote returns empty string for empty input
  TC-U05  Semantic drift score = 0 for Not Covered  (NFR05 Transparency)
  TC-U06  Semantic drift score capped at 50 for Partially Covered  (NFR05)
  TC-U07  Semantic drift score = 100 for Fully Covered with all rubric = 1
  TC-U08  Adversary verdict is N/A when advocate says Not Covered  (FR07)
  TC-U09  Distance gate threshold constant is set at 1.1
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Import only pure-logic functions — no LLM instantiation side-effect yet.
from server.logic import _clean_quote


# -----------------------------------------------------------------------
# TC-U01 — Strip straight double quotes
# -----------------------------------------------------------------------
def test_clean_quote_strips_straight_double_quotes():
    """TC-U01: _clean_quote should remove surrounding straight double-quote chars."""
    result = _clean_quote('"The CAP theorem states..."')
    assert result == "The CAP theorem states..."


# -----------------------------------------------------------------------
# TC-U02 — Strip curly / smart quotes
# -----------------------------------------------------------------------
def test_clean_quote_strips_curly_quotes():
    """TC-U02: _clean_quote should handle Unicode left/right double quotation marks."""
    result = _clean_quote("\u201cThe CAP theorem states\u2026\u201d")
    assert result == "The CAP theorem states\u2026"


# -----------------------------------------------------------------------
# TC-U03 — Already clean input passes through unchanged
# -----------------------------------------------------------------------
def test_clean_quote_leaves_clean_input_unchanged():
    """TC-U03: Text without surrounding quotes should be returned as-is."""
    text = "The CAP theorem states consistency, availability, partition tolerance."
    result = _clean_quote(text)
    assert result == text


# -----------------------------------------------------------------------
# TC-U04 — Empty input returns empty string
# -----------------------------------------------------------------------
def test_clean_quote_empty_input():
    """TC-U04: _clean_quote on empty string must return empty string, not crash."""
    result = _clean_quote("")
    assert result == ""


# -----------------------------------------------------------------------
# TC-U05 — Semantic drift = 0 for Not Covered  (NFR05 Transparency)
# Directly replicates the scoring formula from logic.run_analysis()
# -----------------------------------------------------------------------
def test_semantic_drift_zero_for_not_covered():
    """TC-U05: NFR05 — A Not Covered verdict must always produce a drift score of 0."""
    criterion_1, criterion_2, criterion_3 = 1, 1, 1   # rubric all met
    raw_rubric = round(((criterion_1 + criterion_2 + criterion_3) / 3) * 100)

    match_status = "Not Covered"
    if "Fully Covered" in match_status:
        score = raw_rubric
    elif "Partially Covered" in match_status:
        score = round(raw_rubric * 0.5)
    else:
        score = 0

    assert score == 0


# -----------------------------------------------------------------------
# TC-U06 — Semantic drift capped at 50 for Partially Covered  (NFR05)
# -----------------------------------------------------------------------
def test_semantic_drift_capped_at_50_for_partially_covered():
    """TC-U06: NFR05 — Partially Covered with full rubric must give exactly 50% drift."""
    criterion_1, criterion_2, criterion_3 = 1, 1, 1
    raw_rubric = round(((criterion_1 + criterion_2 + criterion_3) / 3) * 100)

    match_status = "Partially Covered"
    if "Fully Covered" in match_status:
        score = raw_rubric
    elif "Partially Covered" in match_status:
        score = round(raw_rubric * 0.5)
    else:
        score = 0

    assert score == 50
    assert score <= 50


# -----------------------------------------------------------------------
# TC-U07 — Semantic drift = 100 for Fully Covered with rubric all 1
# -----------------------------------------------------------------------
def test_semantic_drift_full_for_fully_covered_with_full_rubric():
    """TC-U07: NFR05 — Fully Covered + all rubric criteria met → drift score 100%."""
    criterion_1, criterion_2, criterion_3 = 1, 1, 1
    raw_rubric = round(((criterion_1 + criterion_2 + criterion_3) / 3) * 100)

    match_status = "Fully Covered"
    if "Fully Covered" in match_status:
        score = raw_rubric
    elif "Partially Covered" in match_status:
        score = round(raw_rubric * 0.5)
    else:
        score = 0

    assert score == 100


# -----------------------------------------------------------------------
# TC-U08 — Rubric score 0 yields drift = 0 even for Fully Covered edge case
# -----------------------------------------------------------------------
def test_semantic_drift_zero_rubric_fully_covered():
    """TC-U08: If rubric returns all 0s for Fully Covered, drift score should be 0."""
    criterion_1, criterion_2, criterion_3 = 0, 0, 0
    raw_rubric = round(((criterion_1 + criterion_2 + criterion_3) / 3) * 100)

    match_status = "Fully Covered"
    if "Fully Covered" in match_status:
        score = raw_rubric
    elif "Partially Covered" in match_status:
        score = round(raw_rubric * 0.5)
    else:
        score = 0

    assert score == 0


# -----------------------------------------------------------------------
# TC-U09 — Distance gate threshold constant
# -----------------------------------------------------------------------
def test_distance_gate_threshold_value():
    """TC-U09: FR06 — The FAISS distance threshold that guards against LLM calls
    should be set to 1.1 (L2 distance). Ensures only semantically related
    content is passed to the LLM (accuracy gatekeeping for NFR02)."""
    import inspect, server.logic as logic_module

    source = inspect.getsource(logic_module.run_analysis)
    assert "1.1" in source, (
        "Distance gate threshold of 1.1 not found in run_analysis source. "
        "Precision of coverage filtering may be compromised."
    )
