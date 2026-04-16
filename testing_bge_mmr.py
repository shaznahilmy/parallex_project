# testing_bge_mmr.py
# Evaluation script for the updated pipeline:
#   - Embedding model: BAAI/bge-small-en-v1.5  (was: all-MiniLM-L6-v2)
#   - Retrieval:       MMR k=5, fetch_k=20     (was: similarity k=3)

#   python testing_bge_mmr.py


import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from server import logic
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np


# Test dataset 
TEST_PAIRS = [
    {
        "pair_id": 1,
        "content_pdf": "educational_dataset/cloud.pdf",
        "guidelines": [
            "Explain the CAP Theorem and its implications on distributed databases, specifically regarding network partitions",
            "Design a containerized application using Docker and orchestrate it using Kubernetes deployments",
            "Compare and contrast the Strangler Fig pattern with the Anti-Corruption Layer pattern for monolith-to-microservices migration",
            "Implement a quantum cryptography key distribution protocol using Qiskit.",
        ],
        "ground_truth": [
            "Partially Covered",
            "Partially Covered",
            "Partially Covered",
            "Not Covered",
        ],
    },
    {
        "pair_id": 2,
        "content_pdf": "educational_dataset/concurrent.pdf",
        "guidelines": [
            "Differentiate between Processes and Threads, explaining memory models and context switching overheads using real-world analogies",
            "Implement thread safety using the `synchronized` keyword to prevent Race Conditions in shared-resource scenarios (e.g., Banking Systems)",
            "Analyse Deadlock scenarios and apply the **Banker's Algorithm** to mathematically prevent resource starvation",
            "Implement the **Actor Model** for distributed message passing as an alternative to shared-state concurrency",
        ],
        "ground_truth": [
            "Partially Covered",
            "Fully Covered",
            "Partially Covered",
            "Not Covered",
        ],
    },
    {
        "pair_id": 3,
        "content_pdf": "educational_dataset/dm.pdf",
        "guidelines": [
            "Calculate and interpret the Customer Acquisition Cost (CAC) to Lifetime Value (LTV) ratio for subscription-based businesses",
            "Apply the AARRR (Pirate Metrics) framework to analyze the customer lifecycle in a SaaS business model",
            "Differentiate between multi-touch attribution models, specifically Linear, Time Decay, and U-Shaped attribution",
            "Execute programmatic ad buying using Demand-Side Platforms (DSP) and RealTime Bidding (RTB)",
        ],
        "ground_truth": [
            "Fully Covered",
            "Partially Covered",
            "Fully Covered",
            "Not Covered",
        ],
    },
    {
        "pair_id": 4,
        "content_pdf": "educational_dataset/network_forensics.pdf",
        "guidelines": [
            "Analyze network traffic using Wireshark to identify TCP SYN flood attacks.",
            "Extract and reconstruct HTTP objects from packet capture (.cap or .pcap) files.",
            "Perform penetration testing using Kali Linux to exploit vulnerable web applications",
            "Formulate a linear programming model to minimize transportation costs using the Simplex method",
        ],
        "ground_truth": [
            "Partially Covered",
            "Fully Covered",
            "Partially Covered",
            "Not Covered",
        ],
    },
    {
        "pair_id": 5,
        "content_pdf": "educational_dataset/nlp.pdf",
        "guidelines": [
            "Explain the mathematical mechanics of the Attention mechanism, specifically the use of Query, Key, and Value matrices",
            "Differentiate between extractive and abstractive text summarization paradigms",
            "Fine-tune a pre-trained Large Language Model using the LoRA (Low-Rank Adaptation) parameter-efficient method.",
            "Calculate the yield strength and tensile strain of reinforced concrete under heavy load conditions",
        ],
        "ground_truth": [
            "Fully Covered",
            "Partially Covered",
            "Partially Covered",
            "Not Covered",
        ],
    },
    {
        "pair_id": 6,
        "content_pdf": "educational_dataset/psychology.pdf",
        "guidelines": [
            "Describe the role of the hippocampus in the consolidation of declarative memories.",
            "Analyze the impact of dopamine depletion within the basal ganglia on voluntary motor function.",
            "Explain the psychological phenomenon of Prosopagnosia following bilateral lesions to the fusiform gyrus",
            "Calculate the aerodynamic drag coefficient of a streamlined body at supersonic speeds.",
        ],
        "ground_truth": [
            "Fully Covered",
            "Partially Covered",
            "Partially Covered",
            "Not Covered",
        ],
    },
    {
        "pair_id": 7,
        "content_pdf": "educational_dataset/robotics.pdf",
        "guidelines": [
            "Calculate the forward kinematics of a 6-DOF robotic arm using Denavit-Hartenberg (DH) parameters",
            "Implement a Proportional-Integral-Derivative (PID) controller for motor trajectory tracking",
            "Design a path-planning algorithm using the Rapidly-exploring Random Tree (RRT) method",
            "Explain the physiological effects of beta-blockers on cardiac arrhythmias.",
        ],
        "ground_truth": [
            "Partially Covered",
            "Fully Covered",
            "Partially Covered",
            "Not Covered",
        ],
    },
    {
        "pair_id": 8,
        "content_pdf": "educational_dataset/sa.pdf",
        "guidelines": [
            "Apply the principles of the Twelve-Factor App methodology for building scalable software-as-a-service (SaaS)",
            "Compare Blue-Green Deployment with Canary releases to minimize production downtime",
            "Implement a Circuit Breaker pattern to prevent cascading failures in distributed microservices",
            "Describe the synthesis of Adenosine Triphosphate (ATP) during cellular respiration.",
        ],
        "ground_truth": [
            "Partially Covered",
            "Partially Covered",
            "Partially Covered",
            "Not Covered",
        ],
    },
    {
        "pair_id": 9,
        "content_pdf": "educational_dataset/webdev.pdf",
        "guidelines": [
            "Demonstrate an understanding of the relationship between client-side (HTML/CSS) and server-side (PHP) scripting",
            "Utilize PHP control structures (loops) and data structures (arrays) to manipulate data",
            "Implement database connectivity using MySQLi or PDO to retrieve and display records",
            "Apply security best practices to prevent SQL Injection attacks",
        ],
        "ground_truth": [
            "Partially Covered",
            "Partially Covered",
            "Partially Covered",
            "Fully Covered",
        ],
    },
]

# Evaluation loop 
y_true = []
y_pred = []
failed_pairs = []

print("=" * 60)
print("PARALLEX EVALUATION — bge-small-en-v1.5 + MMR k=5")
print("=" * 60)

for pair in TEST_PAIRS:
    pair_id = pair["pair_id"]
    content_pdf = pair["content_pdf"]
    guidelines = pair["guidelines"]
    ground_truth = pair["ground_truth"]

    print(f"\n[Pair {pair_id}] Processing: {content_pdf}")

    if not os.path.exists(content_pdf):
        print(f"  File not found: {content_pdf} — skipping")
        failed_pairs.append(pair_id)
        continue

    if len(guidelines) != len(ground_truth):
        print(f"  Mismatch: {len(guidelines)} guidelines but {len(ground_truth)} labels — skipping")
        failed_pairs.append(pair_id)
        continue

    try:
        # Each pair gets its own FAISS index path so runs don't overwrite each other
        session_faiss_path = f"temp/test_faiss_pair_{pair_id}"
        os.makedirs("temp", exist_ok=True)

        # print(f"  → Building FAISS index (bge-small-en-v1.5)...")
        logic.build_and_save_faiss(content_pdf, session_faiss_path)

        # print(f"  → Running audit on {len(guidelines)} guidelines (MMR k=5)...")
        results = logic.run_analysis(guidelines, session_faiss_path)

        for i, result in enumerate(results):
            predicted = result["match_status"].strip()
            expected = ground_truth[i].strip()

            # Normalise predicted label — LLM can append punctuation
            if "Fully Covered" in predicted:
                predicted = "Fully Covered"
            elif "Partially Covered" in predicted:
                predicted = "Partially Covered"
            elif "Not Covered" in predicted:
                predicted = "Not Covered"
            else:
                predicted = "Not Covered"

            y_true.append(expected)
            y_pred.append(predicted)

            symbol = "✓" if predicted == expected else "✗"
            print(f"  [{i+1}] {symbol} Expected: '{expected}' | Got: '{predicted}'")

    except Exception as e:
        print(f"  Error on pair {pair_id}: {e}")
        failed_pairs.append(pair_id)


# Summary

print("\n" + "=" * 60)
print("RESULTS SUMMARY — bge-small-en-v1.5 + MMR k=5")
print("=" * 60)

if not y_true:
    print("No results to evaluate. Check your file paths.")
else:
    labels = ["Fully Covered", "Partially Covered", "Not Covered"]

    print(f"\nTotal guidelines tested: {len(y_true)}")
    print(f"Pairs skipped due to errors: {failed_pairs if failed_pairs else 'None'}")

    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / len(y_true) * 100
    print(f"\nOverall Accuracy: {correct}/{len(y_true)} = {accuracy:.1f}%")

    print("\n── Classification Report ──")
    print(classification_report(y_true, y_pred, labels=labels, zero_division=0))

    print("── Confusion Matrix ──")
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    print(f"{'':25} {'FC':>5} {'PC':>5} {'NC':>5}  ← Predicted")
    print(f"{'Fully Covered (actual)':25} {cm[0][0]:>5} {cm[0][1]:>5} {cm[0][2]:>5}")
    print(f"{'Partially Covered (act)':25} {cm[1][0]:>5} {cm[1][1]:>5} {cm[1][2]:>5}")
    print(f"{'Not Covered (actual)':25} {cm[2][0]:>5} {cm[2][1]:>5} {cm[2][2]:>5}")

    output_file = "testing_results_bge_mmr_gpt-4.0_dual_agent.txt"
    with open(output_file, "w") as f:
        f.write("Pipeline: BAAI/bge-small-en-v1.5 + MMR (k=5, fetch_k=20, lambda=0.5)\n")
        f.write(f"Total tested: {len(y_true)}\n")
        f.write(f"Overall Accuracy: {accuracy:.1f}%\n\n")
        f.write("Classification Report:\n")
        f.write(classification_report(y_true, y_pred, labels=labels, zero_division=0))
        f.write("\nAll predictions:\n")
        for i, (t, p) in enumerate(zip(y_true, y_pred)):
            match = "CORRECT" if t == p else "WRONG"
            f.write(f"  [{i+1}] True: {t:20} | Pred: {p:20} | {match}\n")

    print(f"\n Results saved to {output_file}")   
