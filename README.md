# 🛡️ Sentinel RAG

## Security-Focused Multi-Tenant Agentic RAG

Sentinel RAG is a security-focused Retrieval-Augmented Generation (RAG) application built with Python and Gradio.

It demonstrates how an AI application can combine **role-based access control (RBAC), tenant isolation, hybrid retrieval, LLM reranking, agentic query processing, and automated evaluation** to provide controlled access to organizational knowledge.

> **Portfolio project:** This is a technical prototype demonstrating enterprise-oriented RAG and security patterns. It is not presented as a production-ready enterprise security system.

---

## ✨ What It Demonstrates

- 🔐 **Role-Based Access Control (RBAC)**
- 🏢 **Multi-Tenant Data Isolation**
- 🔎 **Hybrid Retrieval**
  - ChromaDB dense retrieval
  - BM25 keyword retrieval
  - Reciprocal Rank Fusion (RRF)
  - LLM-based reranking
- 🤖 **Agentic RAG Pipeline**
- 📊 **Retrieval Evaluation**
  - MRR
  - nDCG@4
  - LLM-as-a-Judge faithfulness
- 🧭 **Execution Trace Inspection**
- 🔑 **Environment-Based Authentication Configuration**
- 🗂️ **Reproducible Document Ingestion**
- 🎨 **Gradio Web Interface**

---

## 🏗️ Architecture

```text
                         ┌─────────────────────┐
                         │    Gradio Web UI    │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │ Authentication /    │
                         │ SecurityContext     │
                         └──────────┬──────────┘
                                    │
                         Tenant + Role Filtering
                                    │
                                    ▼
                    ┌──────────────────────────────┐
                    │     Agentic RAG Pipeline     │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                 ┌──────────────────────────────────┐
                 │        Hybrid Retrieval          │
                 │                                  │
                 │  ChromaDB Dense + BM25 Sparse    │
                 │             ↓                    │
                 │          RRF Fusion              │
                 │             ↓                    │
                 │       LLM Reranking              │
                 └────────────────┬─────────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Context + LLM   │
                         │     Answer      │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Trace / Metrics │
                         └─────────────────┘
````

---

## 🔐 Security Model

Documents are tagged with security metadata including:

* `tenant_id`
* `classification`
* document category
* source file

Retrieval is performed through a `SecurityContext`, allowing the application to restrict which documents a user role can access.

Example role model:

| Role        | Example Access                                        |
| ----------- | ----------------------------------------------------- |
| `employee`  | Company and product knowledge                         |
| `executive` | Company, products, contracts and employee information |
| `admin`     | Unrestricted access + evaluation controls             |

The important design principle is that authorization is applied **during retrieval**, rather than relying only on the LLM prompt to avoid exposing restricted information.

---

## 🔎 Retrieval Pipeline

Sentinel RAG combines multiple retrieval techniques:

```text
User Query
    │
    ├──► Dense Retrieval ──► ChromaDB
    │
    └──► Sparse Retrieval ─► BM25
                │
                ▼
        Reciprocal Rank Fusion
                │
                ▼
         LLM Reranking
                │
                ▼
        Authorized Context
                │
                ▼
          Agentic Answer
```

This hybrid approach combines semantic retrieval with keyword matching before the final reranking stage.

---

## 🧪 Evaluation

The project includes an automated evaluation suite covering retrieval and answer quality.

Current baseline on the included synthetic InsureLLM benchmark:

| Metric            |   Result |
| ----------------- | -------: |
| Mean MRR          | **1.00** |
| Mean nDCG@4       | **1.00** |
| Mean Faithfulness | **0.96** |
| Test Cases        |    **5** |

The benchmark currently evaluates questions against expected source files and uses an LLM judge to assess answer faithfulness.

> These results are a small demonstration benchmark, not a claim of production-level RAG performance.

---

## 📊 Example Evaluation Queries

The current benchmark includes questions such as:

* How many employees does Insurellm have?
* What products does Insurellm offer?
* What is Bizllm?
* What are the pricing tiers for Bizllm?
* What is the history of Insurellm?

---

## 📁 Repository Structure

```text
sentinel-rag/
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
│
├── app.py
├── config.py
├── ingest.py
│
├── core/
│   ├── __init__.py
│   ├── agent.py
│   ├── auth.py
│   ├── retriever.py
│   └── security.py
│
├── eval/
│   ├── __init__.py
│   ├── evaluator.py
│   └── metrics.py
│
└── data/
    └── InsureLLM/
        ├── company/
        ├── contracts/
        ├── employees/
        └── products/
```

### Core components

| File                | Purpose                                 |
| ------------------- | --------------------------------------- |
| `app.py`            | Gradio application and user interaction |
| `config.py`         | Centralized configuration               |
| `ingest.py`         | Document ingestion and indexing         |
| `core/security.py`  | Tenant and role authorization           |
| `core/auth.py`      | Demo authentication                     |
| `core/retriever.py` | Hybrid retrieval and reranking          |
| `core/agent.py`     | Agentic RAG execution                   |
| `eval/metrics.py`   | MRR, nDCG and LLM evaluation            |
| `eval/evaluator.py` | Benchmark suite execution               |

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/FMangiwa/sentinel-rag.git
cd sentinel-rag
```

### 2. Create a virtual environment

#### Windows

```powershell
py -m venv .venv
.venv\Scripts\activate
```

#### macOS / Linux

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to `.env` and provide your API key.

#### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

Then edit `.env`:

```text
OPENAI_API_KEY=your-api-key
```

Do **not** commit `.env`.

### 5. Build the local indexes

```bash
python ingest.py
```

This creates the local ChromaDB and BM25 indexes.

The generated `chroma_db/` directory is intentionally excluded from Git because it can be recreated from the source dataset.

### 6. Launch the application

```bash
python app.py
```

Open:

```text
http://127.0.0.1:7860
```

---

## 🧪 Running the Evaluation

After launching the application, an administrator can access the evaluation functionality from the dashboard.

The evaluation pipeline measures:

* Retrieval ranking
* Source relevance
* nDCG@4
* Answer faithfulness

The benchmark uses the source documents included in this repository.

---

## 🗃️ Dataset

The repository includes an **InsureLLM synthetic demonstration corpus** containing fictional:

* company information
* products
* contracts
* employee profiles

The dataset is included so the RAG pipeline can be reproduced without requiring external documents.

**The data is fictional/synthetic and is not intended to represent a real organization or confidential client information.**

---

## 🔑 Authentication

Authentication credentials are configured through environment variables.

Example:

```text
DEMO_ADMIN_PASSWORD=change-me-admin
DEMO_EMPLOYEE_PASSWORD=change-me-employee
DEMO_EXECUTIVE_PASSWORD=change-me-executive
```

The included authentication system is intended for demonstration purposes.

For a production system, authentication should be integrated with an appropriate identity provider and the authorization model should be enforced at the application/data layer.

---

## ⚙️ Configuration

Important configuration values are centralized in `config.py`.

Examples include:

* LLM provider/model
* embedding model
* reranking model
* Chroma persistence path
* retrieval parameters
* role permissions

API credentials are loaded from environment variables rather than hard-coded into the source code.

---

## 🧠 Engineering Highlights

This project demonstrates several patterns relevant to real-world AI engineering work:

### Secure RAG

Authorization is considered part of the retrieval pipeline rather than simply being expressed as an instruction to the LLM.

### Hybrid Search

Dense and sparse retrieval are combined to improve coverage across semantic and exact keyword matches.

### Reranking

Retrieved candidates are passed through an LLM-based reranking stage before being provided to the answer-generation pipeline.

### Agentic RAG

The system separates security context, retrieval, reasoning and answer generation into distinct components.

### Evaluation

The project includes deterministic retrieval metrics and an LLM-based faithfulness judge instead of relying solely on subjective manual testing.

---

## ⚠️ Limitations

This project is a portfolio prototype.

It does **not** claim to provide:

* production-grade authentication
* enterprise identity management
* comprehensive penetration testing
* formal security certification
* production-scale infrastructure
* guaranteed retrieval accuracy

The security architecture demonstrates patterns that can be extended for production systems, but additional infrastructure, testing and security controls would be required.

---

## 🛠️ Technology Stack

* **Python**
* **Gradio**
* **ChromaDB**
* **BM25 / rank-bm25**
* **LiteLLM**
* **LLM-based reranking**
* **Retrieval-Augmented Generation**
* **Role-Based Access Control**
* **Multi-Tenant Architecture**

---

## 👨‍💻 Portfolio Context

Sentinel RAG was built as an AI engineering portfolio project focused on **secure enterprise-oriented RAG systems**.

It demonstrates practical experience with:

`RAG` · `Hybrid Search` · `RBAC` · `Multi-Tenancy` · `LLM Reranking` · `Agentic AI` · `Evaluation` · `Python`

---

## 📄 License

See `LICENSE`.

````
