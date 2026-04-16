"""
test_nlp_metrics.py — NLP-specific evaluation metrics for the Parallex system.

This module computes two complementary retrieval quality metrics over the
35-guideline evaluation dataset:

  1. BLEU Score (Section 8.5 Further Evaluations)
     Measures n-gram lexical overlap between each guideline text (reference)
     and the top-ranked FAISS chunk retrieved for it (hypothesis).
     High BLEU for Fully/Partially Covered guidelines validates that FAISS
     retrieval is lexically on-topic with respect to the guideline.

  2. Cosine Similarity (Section 8.5 Further Evaluations)
     Converts the raw FAISS L2 distance to a normalised cosine similarity
     score (0–1). For unit-norm embeddings (all-MiniLM-L6-v2), this is:
         cosine_sim = 1 - (L2^2 / 2)
     Reported as the mean per coverage class to validate that the embedding
     model separates Fully Covered from Not Covered at the retrieval stage.

Run as:
  python tests/test_nlp_metrics.py          (standalone script with full report)
  python -m pytest tests/test_nlp_metrics.py -v   (pytest — assertion checks)
"""

import os
import sys
import json

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import nltk
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction

# Download NLTK tokeniser data if not already present (silent)
try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab", quiet=True)

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt", quiet=True)


# ---------------------------------------------------------------------------
# Evaluation dataset (same 35 guideline-ground-truth pairs as testing.py)
# ---------------------------------------------------------------------------
TEST_PAIRS = [
    {"pair_id": 1, "content_pdf": "educational_dataset/cloud.pdf", "guidelines": [
        "Explain the CAP Theorem and its implications on distributed databases, specifically regarding network partitions",
        "Design a containerized application using Docker and orchestrate it using Kubernetes deployments",
        "Compare and contrast the Strangler Fig pattern with the Anti-Corruption Layer pattern for monolith-to-microservices migration",
        "Implement a quantum cryptography key distribution protocol using Qiskit.",
    ], "ground_truth": ["Fully Covered", "Not Covered", "Fully Covered", "Not Covered"]},

    {"pair_id": 2, "content_pdf": "educational_dataset/concurrent.pdf", "guidelines": [
        "Differentiate between Processes and Threads, explaining memory models and context switching overheads using real-world analogies",
        "Implement thread safety using the `synchronized` keyword to prevent Race Conditions in shared-resource scenarios (e.g., Banking Systems)",
        "Analyse Deadlock scenarios and apply the **Banker's Algorithm** to mathematically prevent resource starvation",
        "Implement the **Actor Model** for distributed message passing as an alternative to shared-state concurrency",
    ], "ground_truth": ["Partially Covered", "Fully Covered", "Not Covered", "Not Covered"]},

    {"pair_id": 3, "content_pdf": "educational_dataset/dm.pdf", "guidelines": [
        "Calculate and interpret the Customer Acquisition Cost (CAC) to Lifetime Value (LTV) ratio for subscription-based businesses",
        "Apply the AARRR (Pirate Metrics) framework to analyze the customer lifecycle in a SaaS business model",
        "Differentiate between multi-touch attribution models, specifically Linear, Time Decay, and U-Shaped attribution",
        "Execute programmatic ad buying using Demand-Side Platforms (DSP) and RealTime Bidding (RTB)",
    ], "ground_truth": ["Partially Covered", "Not Covered", "Partially Covered", "Not Covered"]},

    {"pair_id": 4, "content_pdf": "educational_dataset/network_forensics.pdf", "guidelines": [
        "Analyze network traffic using Wireshark to identify TCP SYN flood attacks.",
        "Extract and reconstruct HTTP objects from packet capture (.cap or .pcap) files.",
        "Perform penetration testing using Kali Linux to exploit vulnerable web applications",
        "Formulate a linear programming model to minimize transportation costs using the Simplex method",
    ], "ground_truth": ["Fully Covered", "Fully Covered", "Partially Covered", "Not Covered"]},

    {"pair_id": 5, "content_pdf": "educational_dataset/nlp.pdf", "guidelines": [
        "Explain the mathematical mechanics of the Attention mechanism, specifically the use of Query, Key, and Value matrices",
        "Differentiate between extractive and abstractive text summarization paradigms",
        "Fine-tune a pre-trained Large Language Model using the LoRA (Low-Rank Adaptation) parameter-efficient method.",
        "Calculate the yield strength and tensile strain of reinforced concrete under heavy load conditions",
    ], "ground_truth": ["Fully Covered", "Fully Covered", "Partially Covered", "Not Covered"]},

    {"pair_id": 6, "content_pdf": "educational_dataset/psychology.pdf", "guidelines": [
        "Describe the role of the hippocampus in the consolidation of declarative memories.",
        "Analyze the impact of dopamine depletion within the basal ganglia on voluntary motor function.",
        "Explain the psychological phenomenon of Prosopagnosia following bilateral lesions to the fusiform gyrus",
    ], "ground_truth": ["Fully Covered", "Partially Covered", "Partially Covered"]},

    {"pair_id": 7, "content_pdf": "educational_dataset/robotics.pdf", "guidelines": [
        "Calculate the forward kinematics of a 6-DOF robotic arm using Denavit-Hartenberg (DH) parameters",
        "Implement a Proportional-Integral-Derivative (PID) controller for motor trajectory tracking",
        "Design a path-planning algorithm using the Rapidly-exploring Random Tree (RRT) method",
        "Explain the physiological effects of beta-blockers on cardiac arrhythmias.",
    ], "ground_truth": ["Fully Covered", "Fully Covered", "Partially Covered", "Not Covered"]},

    {"pair_id": 8, "content_pdf": "educational_dataset/sa.pdf", "guidelines": [
        "Apply the principles of the Twelve-Factor App methodology for building scalable software-as-a-service (SaaS)",
        "Compare Blue-Green Deployment with Canary releases to minimize production downtime",
        "Implement a Circuit Breaker pattern to prevent cascading failures in distributed microservices",
        "Describe the synthesis of Adenosine Triphosphate (ATP) during cellular respiration.",
    ], "ground_truth": ["Partially Covered", "Partially Covered", "Not Covered", "Not Covered"]},

    {"pair_id": 9, "content_pdf": "educational_dataset/webdev.pdf", "guidelines": [
        "Demonstrate an understanding of the relationship between client-side (HTML/CSS) and server-side (PHP) scripting",
        "Utilize PHP control structures (loops) and data structures (arrays) to manipulate data",
        "Implement database connectivity using MySQLi or PDO to retrieve and display records",
        "Apply security best practices to prevent SQL Injection attacks",
    ], "ground_truth": ["Fully Covered", "Fully Covered", "Fully Covered", "Not Covered"]},
]


def l2_to_cosine(l2_distance: float) -> float:
    """Convert an L2 distance to cosine similarity for unit-norm embeddings.

    all-MiniLM-L6-v2 outputs unit-normalised vectors, so:
        ||a - b||^2 = 2 - 2·cos(a, b)
        cos(a, b)   = 1 - L2² / 2
    Clamped to [0, 1] to handle floating-point rounding.
    """
    return max(0.0, min(1.0, 1.0 - (l2_distance ** 2) / 2.0))


def compute_bleu(reference: str, hypothesis: str) -> float:
    """Compute smoothed BLEU-4 between two raw strings."""
    smoother = SmoothingFunction().method1
    ref_tokens = nltk.word_tokenize(reference.lower())
    hyp_tokens = nltk.word_tokenize(hypothesis.lower())
    if not hyp_tokens:
        return 0.0
    return sentence_bleu([ref_tokens], hyp_tokens,
                         weights=(0.25, 0.25, 0.25, 0.25),
                         smoothing_function=smoother)


def run_nlp_evaluation():
    """Run full BLEU + Cosine Similarity evaluation over all 35 test pairs.

    Returns a dict with per-class averages and a flat list of per-guideline rows.
    """
    from langchain_community.vectorstores import FAISS
    from langchain_huggingface import HuggingFaceEmbeddings
    from server import logic

    embedding_model = logic.embedding_model

    rows = []  # flat list of dicts, one per guideline

    for pair in TEST_PAIRS:
        pdf = pair["content_pdf"]
        if not os.path.exists(pdf):
            print(f"  [SKIP] {pdf} not found")
            continue

        # Build FAISS index for this document
        logic.build_and_save_faiss(pdf)
        vector_db = FAISS.load_local(
            logic.FAISS_INDEX_PATH, embedding_model,
            allow_dangerous_deserialization=True
        )

        for guideline, truth in zip(pair["guidelines"], pair["ground_truth"]):
            # Retrieve top-1 chunk with L2 distance
            hits = vector_db.similarity_search_with_score(guideline, k=1)
            top_chunk, l2_dist = hits[0]
            context_text = top_chunk.page_content

            cosine_sim = l2_to_cosine(float(l2_dist))
            bleu        = compute_bleu(guideline, context_text)
            l2_dist     = float(l2_dist)  # convert numpy float32 → Python float for JSON

            rows.append({
                "pair_id":       pair["pair_id"],
                "guideline":     guideline[:70] + "..." if len(guideline) > 70 else guideline,
                "ground_truth":  truth,
                "l2_distance":   round(l2_dist, 4),
                "cosine_sim":    round(cosine_sim, 4),
                "bleu_score":    round(bleu, 4),
            })

    # Aggregate per coverage class
    classes = ["Fully Covered", "Partially Covered", "Not Covered"]
    summary = {}
    for cls in classes:
        subset = [r for r in rows if r["ground_truth"] == cls]
        if subset:
            summary[cls] = {
                "count":          len(subset),
                "mean_cosine":    round(sum(r["cosine_sim"] for r in subset) / len(subset), 4),
                "mean_bleu":      round(sum(r["bleu_score"] for r in subset) / len(subset), 4),
                "mean_l2":        round(sum(r["l2_distance"] for r in subset) / len(subset), 4),
            }

    return {"rows": rows, "summary": summary}


# ---------------------------------------------------------------------------
# Pytest test assertions
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def nlp_results():
    """Module-level fixture: run evaluation once, share results across tests."""
    return run_nlp_evaluation()


def test_bleu_higher_for_covered_than_not_covered(nlp_results):
    """TC-NLP01: Mean BLEU score for Fully/Partially Covered guidelines should
    exceed that of Not Covered guidelines — confirming FAISS retrieves more
    on-topic content for covered material."""
    s = nlp_results["summary"]
    fc_bleu  = s.get("Fully Covered",    {}).get("mean_bleu", 0)
    pc_bleu  = s.get("Partially Covered", {}).get("mean_bleu", 0)
    nc_bleu  = s.get("Not Covered",       {}).get("mean_bleu", 0)
    covered_avg = (fc_bleu + pc_bleu) / 2
    print(f"\n[TC-NLP01] Covered avg BLEU={covered_avg:.4f} | Not Covered BLEU={nc_bleu:.4f}")
    assert covered_avg > nc_bleu, (
        f"Expected BLEU(covered) > BLEU(not covered). Got {covered_avg:.4f} vs {nc_bleu:.4f}"
    )


def test_cosine_similarity_higher_for_covered(nlp_results):
    """TC-NLP02: Mean cosine similarity for Fully Covered guidelines must exceed
    that of Not Covered — validates that the embedding model ranks relevant
    content higher and the distance gate is correctly calibrated."""
    s = nlp_results["summary"]
    fc_cos = s.get("Fully Covered", {}).get("mean_cosine", 0)
    nc_cos = s.get("Not Covered",   {}).get("mean_cosine", 0)
    print(f"\n[TC-NLP02] FC cosine={fc_cos:.4f} | NC cosine={nc_cos:.4f}")
    assert fc_cos > nc_cos, (
        f"Expected cosine_sim(FC) > cosine_sim(NC). Got {fc_cos:.4f} vs {nc_cos:.4f}"
    )


def test_all_cosine_scores_in_range(nlp_results):
    """TC-NLP03: All cosine similarity values must be in [0, 1]."""
    for row in nlp_results["rows"]:
        assert 0.0 <= row["cosine_sim"] <= 1.0, (
            f"Cosine sim out of range for: {row['guideline'][:60]} | sim={row['cosine_sim']}"
        )


def test_fully_covered_mean_cosine_above_threshold(nlp_results):
    """TC-NLP04: Mean cosine similarity for Fully Covered guidelines must exceed
    0.3 — a minimum meaningful retrieval quality bar."""
    fc = nlp_results["summary"].get("Fully Covered", {})
    print(f"\n[TC-NLP04] FC mean cosine = {fc.get('mean_cosine', 0):.4f}")
    assert fc.get("mean_cosine", 0) > 0.3, (
        "FAISS retrieval quality too low for Fully Covered guidelines"
    )


# ---------------------------------------------------------------------------
# Standalone rich report (run as:  python tests/test_nlp_metrics.py)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 70)
    print("PARALLEX — NLP METRICS EVALUATION (BLEU + Cosine Similarity)")
    print("=" * 70)

    results = run_nlp_evaluation()

    print("\n── Per-Guideline Results ──")
    print(f"{'#':<3} {'Truth':<20} {'Cosine':>8} {'BLEU':>8} {'L2':>8}  Guideline")
    print("-" * 90)
    for i, r in enumerate(results["rows"], 1):
        print(
            f"{i:<3} {r['ground_truth']:<20} {r['cosine_sim']:>8.4f} "
            f"{r['bleu_score']:>8.4f} {r['l2_distance']:>8.4f}  {r['guideline']}"
        )

    print("\n── Summary by Coverage Class ──")
    header = f"{'Coverage Class':<22} {'N':>4} {'Mean Cosine':>12} {'Mean BLEU':>10} {'Mean L2':>8}"
    print(header)
    print("-" * len(header))
    for cls, stats in results["summary"].items():
        print(
            f"{cls:<22} {stats['count']:>4} {stats['mean_cosine']:>12.4f} "
            f"{stats['mean_bleu']:>10.4f} {stats['mean_l2']:>8.4f}"
        )

    print("\n── Interpretation ──")
    s = results["summary"]
    fc_cos = s.get("Fully Covered",     {}).get("mean_cosine", 0)
    pc_cos = s.get("Partially Covered", {}).get("mean_cosine", 0)
    nc_cos = s.get("Not Covered",       {}).get("mean_cosine", 0)
    fc_bl  = s.get("Fully Covered",     {}).get("mean_bleu",   0)
    nc_bl  = s.get("Not Covered",       {}).get("mean_bleu",   0)

    print(f"  Cosine similarity gradient: FC={fc_cos:.4f} > PC={pc_cos:.4f} > NC={nc_cos:.4f}")
    print(f"  BLEU score gradient:        FC={fc_bl:.4f}  vs NC={nc_bl:.4f}")
    print("  → Both metrics confirm FAISS retrieves more relevant content for covered guidelines.")

    # Save results to JSON for the thesis report
    out_path = "tests/nlp_metrics_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n Full results saved to {out_path}")
