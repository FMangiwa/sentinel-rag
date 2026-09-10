```markdown
# 🛡️ Sentinel RAG: Multi-Tenant Enterprise Agentic RAG Platform

**Sentinel RAG** is a security-first, multi-tenant Retrieval-Augmented Generation (RAG) platform built with Python and Gradio. It enforces role-based metadata access control (RBAC) and strict tenant boundaries at retrieval time—preventing unauthorized access and privilege escalation across corporate document hierarchies.

---

## 🌟 Key Features

* **Session-Based Authentication:** State-managed login UI (`gr.State`) featuring eye-toggle password inputs and compact session controls.
* **Security-Enforced Retrieval:** Multi-tenant hybrid retrieval pipeline (ChromaDB dense search + BM25 keyword search + Reciprocal Rank Fusion + LiteLLM reranking) filtered dynamically via `SecurityContext`.
* **Data-Level RBAC Enforcement:** Role-based access rules preventing unauthorized access to sensitive datasets:
  * `employee`: Access to `products/` and `company/` directories.
  * `executive`: Access to `products/`, `company/`, `contracts/`, and `employees/`.
  * `admin`: Unrestricted retrieval across all directories + execution privileges for evaluation benchmarks.
* **Execution Trace Inspector:** Full visual breakdown of retrieval scores, doc IDs, and routing logic per query.
* **System Evaluation Benchmarks:** Built-in RAG suite evaluator (`RAGSuiteEvaluator`) assessing system faithfulness and retrieval precision.

---

## 📁 Repository Structure

```text
5_sentinel_RAG/
├── Readme.md                   # Project documentation & setup guide
├── requirements.txt            # Python dependencies (gradio, litellm, chromadb, etc.)
├── app.py                      # Main Gradio dashboard
├── config.py                   # Centralized application configurations
├── ingest.py                   # Multi-tenant document indexer
├── core/
│   ├── security.py             # RBAC SecurityContext
│   ├── auth.py                 # User authentication & credentials
│   ├── retriever.py            # Hybrid RAG retriever (Dense + Sparse + RRF)
│   └── agent.py                # Agentic execution pipeline
├── eval/
│   ├── metrics.py              # Math metrics (MRR, nDCG) & LLM-as-a-Judge
│   └── evaluator.py            # Benchmark suite runner
└── data/
    └── InsureLLM/              # Active tenant storage directory
        ├── company/            # Corporate policies & handbooks
        ├── contracts/          # Client MSAs & vendor agreements
        ├── employees/          # Executive compensation & payroll
        └── products/           # Product specifications```

---

## 🚀 Quickstart Guide

### 1. Prerequisites & Environment Setup

Ensure you are running **Python 3.12+** and have your environment managed via `uv` or `venv`.

```bash
# Clone the repository and navigate into the project root
cd 5_sentinel_RAG

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt

```

### 2. Configure API Keys

Set your target LLM provider API key in your environment variables:

```bash
# OpenAI (Default)
export OPENAI_API_KEY="your-openai-api-key"

# Windows PowerShell
$env:OPENAI_API_KEY="your-openai-api-key"

```

### 3. Dataset & Index Vector Store

Run ingestion:

# Ingest and index documents into ChromaDB
uv run ingest.py

```

### 4. Launch Application

Start the web interface:

```bash
uv run app.py

```

Access the UI locally at `http://127.0.0.1:7860`.

---

## 🔐 Default Test Credentials

| Username | Password | Role | Tenant | Access |
|---|---|---|---|---|
| `alice` | Set via `DEMO_ADMIN_PASSWORD` | `admin` | `InsureLLM` | Unrestricted + System Evaluation Benchmarking |
| `bob` | Set via `DEMO_EMPLOYEE_PASSWORD` | `employee` | `InsureLLM` | Products & Company knowledge only |
| `carol` | Set via `DEMO_EXECUTIVE_PASSWORD` | `executive` | `InsureLLM` | All documents (Financials, Contracts, Payroll) |

> **Demo only:** Authentication credentials are configured through environment variables. This project demonstrates application-level tenant and role-based access controls; it is not intended to represent production-grade authentication.

---

## 🧪 System Evaluation & Benchmarking

Admin users can run the automated evaluation suite via the **📈 System Evaluation** tab inside the dashboard. It measures retrieval faithfulness, chunk relevance, and guardrail enforcement against pre-defined ground-truth test cases.

```

```