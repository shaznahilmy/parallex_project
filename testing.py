# evaluate.py
# Run this from the project root: python evaluate.py

import os
import sys

# sys.path.insert adds the project root folder to python's search path.
# allows to import from the server folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from server import logic
#to create the classfication report and confusion matrix (the grid)
from sklearn.metrics import classification_report, confusion_matrix
#used for numerical operations on the confusion matrix
import numpy as np


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
            "Fully Covered",
            "Not Covered",
            "Fully Covered",
            "Not Covered",
        ]
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
            "Not Covered",
            "Not Covered",
        ]
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
            "Partially Covered",
            "Not Covered",
            "Partially Covered",
            "Not Covered",
        ]
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
            "Fully Covered",
            "Fully Covered",
            "Partially Covered",
            "Not Covered",
        ]
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
            "Fully Covered",
            "Partially Covered",
            "Not Covered",
        ]
    },
     {
        "pair_id": 6,
        "content_pdf": "educational_dataset/psychology.pdf",
        "guidelines": [
            "Describe the role of the hippocampus in the consolidation of declarative memories.",
            "Analyze the impact of dopamine depletion within the basal ganglia on voluntary motor function.",
            "Explain the psychological phenomenon of Prosopagnosia following bilateral lesions to the fusiform gyrus",         
        ],
        "ground_truth": [
            "Fully Covered",
            "Partially Covered",
            "Partially Covered",          
        ]
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
            "Fully Covered",
            "Fully Covered",
            "Partially Covered",
            "Not Covered",
        ]
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
            "Not Covered",
            "Not Covered",
        ]
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
            "Fully Covered",
            "Fully Covered",           
            "Fully Covered",
            "Not Covered",
        ]
    },
   
]


y_true = []   # adds all human assigned ground truth labels
y_pred = []   # adds all parallex predictions
failed_pairs = []

print("=" * 60)
print("PARALLEX EVALUATION SCRIPT")
print("=" * 60)

for pair in TEST_PAIRS:
    pair_id = pair["pair_id"]
    content_pdf = pair["content_pdf"]
    guidelines = pair["guidelines"]
    ground_truth = pair["ground_truth"]

    print(f"\n[Pair {pair_id}] Processing: {content_pdf}")

    # checking if the file exists
    if not os.path.exists(content_pdf):
        print(f" File not found: {content_pdf} — skipping")
        failed_pairs.append(pair_id)
        continue
    #checking if the guidelines match is length
    if len(guidelines) != len(ground_truth):
        print(f"  Mismatch: {len(guidelines)} guidelines but {len(ground_truth)} labels — skipping")
        failed_pairs.append(pair_id)
        continue

    try:
        # Building the FAISS index for this content document
        print(f"  → Building FAISS index...")
        logic.build_and_save_faiss(content_pdf)

        # Running the audit
        print(f"  → Running audit on {len(guidelines)} guidelines...")
        results = logic.run_analysis(guidelines)

        # getting the predictions and ehcking with ground truth
        for i, result in enumerate(results):
            predicted = result["match_status"].strip()
            expected = ground_truth[i].strip()

            # Normalising the predicted label because LLM can add . or ,
            if "Fully Covered" in predicted:
                predicted = "Fully Covered"
            elif "Partially Covered" in predicted:
                predicted = "Partially Covered"
            elif "Not Covered" in predicted:
                predicted = "Not Covered"
            else:
                predicted = "Not Covered"  # default if parsing failed
            
            #adding to list
            y_true.append(expected)
            y_pred.append(predicted)

            status_icon = "✅" if predicted == expected else "❌"
            print(f"  {status_icon} [{i+1}] Expected: '{expected}' | Got: '{predicted}'")

    except Exception as e:
        print(f"  ❌ Error on pair {pair_id}: {e}")
        failed_pairs.append(pair_id)


print("\n" + "=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)

if not y_true:
    print("No results to evaluate. Check your file paths.")
else:
    labels = ["Fully Covered", "Partially Covered", "Not Covered"]

    print(f"\nTotal guidelines tested: {len(y_true)}")
    print(f"Pairs skipped due to errors: {failed_pairs if failed_pairs else 'None'}")

    # checking accuracy
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    accuracy = correct / len(y_true) * 100
    print(f"\nOverall Accuracy: {correct}/{len(y_true)} = {accuracy:.1f}%")

    #  creating classification report
    # sklearn generates this automatically from y_true and y_pred.
    print("\n── Classification Report ──")
    print(classification_report(y_true, y_pred, labels=labels, zero_division=0))

    # Confusion matrix
    print("── Confusion Matrix ──")
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    print(f"{'':25} {'FC':>5} {'PC':>5} {'NC':>5}  ← Predicted")
    print(f"{'Fully Covered (actual)':25} {cm[0][0]:>5} {cm[0][1]:>5} {cm[0][2]:>5}")
    print(f"{'Partially Covered (act)':25} {cm[1][0]:>5} {cm[1][1]:>5} {cm[1][2]:>5}")
    print(f"{'Not Covered (actual)':25} {cm[2][0]:>5} {cm[2][1]:>5} {cm[2][2]:>5}")

    # Saving results to a text file
    with open("testing_results_gpt-4o-mini.txt", "w") as f:
        f.write(f"Total tested: {len(y_true)}\n")
        f.write(f"Overall Accuracy: {accuracy:.1f}%\n\n")
        f.write("Classification Report:\n")
        f.write(classification_report(y_true, y_pred, labels=labels, zero_division=0))
        f.write("\nAll predictions:\n")
        for i, (t, p) in enumerate(zip(y_true, y_pred)):
            match = "CORRECT" if t == p else "WRONG"
            f.write(f"  [{i+1}] True: {t:20} | Pred: {p:20} | {match}\n")

    print("\n✅ Results saved to file")






