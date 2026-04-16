# Parallex: Dual-Agent Adversarial RAG for Curriculum Alignment
Parallex is an automated curriculum alignment verification system built for higher education. It utilizes a novel **Dual-Agent Adversarial Retrieval-Augmented Generation (RAG)** framework fortified by a **Natural Language Inference (NLI) tripwire** to cross-examine course content against official syllabi with 97.1% accuracy.

## The Problem & Solution
Standard LLMs suffer from leniency and hallucination when grading academic content. Parallex solves this by introducing a "Devil's Advocate" architecture. 
1. An **Advocate Agent** retrieves content via FAISS and proposes an alignment score.
2. A local **DeBERTa-v3 NLI Model** mathematically verifies if the extracted quote actually entails the guideline.
3. If a contradiction is detected, an **Adversary Agent** is triggered to aggressively cross-examine the evidence and unilaterally downgrade hallucinated claims.

## Key Features
- **Deterministic Pipeline:** Strict JSON output parsing via Pydantic (`Match Status`, `Reasoning`, `Exact Quote`).
- **NLI Failsafes:** Algorithmic protection against LLM hallucination using HuggingFace cross-encoders.
- **Thread-Safe Sessions:** UUID-isolated FAISS vector generation for safe concurrent usage.
- **Dynamic PDF Annotation:** NLTK span-expansion mathematically maps LLM outputs back to the original uploaded PDF, generating a downloadable, highlighted audit report.

## Technology Stack
* **Frontend:** React, Tailwind CSS
* **Backend:** FastAPI, Python
* **Generative AI:** OpenAI GPT-4o (via Azure Inference), LangChain
* **Vector DB & NLP:** FAISS, HuggingFace (`BAAI/bge-small-en-v1.5`, `cross-encoder/nli-deberta-v3-base`), PyMuPDF (`fitz`), NLTK

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js & npm
- OpenAI API Key (or Azure Inference Token)

### Backend Setup
1. Clone the repository and navigate to the backend directory:
   ```bash
   git clone [https://github.com/YourUsername/parallex.git](https://github.com/shaznahilmy/parallex.git)
   cd parallex/backend
