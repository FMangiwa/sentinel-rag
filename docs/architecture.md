\# Sentinel RAG Architecture



\## 1. System Overview



Sentinel RAG is a security-focused, multi-tenant RAG application.



The system combines:



\- Authentication

\- Role-based authorization

\- Tenant-aware retrieval

\- Dense vector search

\- Sparse BM25 search

\- Reciprocal Rank Fusion

\- LLM reranking

\- Agentic answer generation

\- Retrieval and faithfulness evaluation



```text

User

&#x20;│

&#x20;▼

┌─────────────────────┐

│     Gradio UI       │

└──────────┬──────────┘

&#x20;          │

&#x20;          ▼

┌─────────────────────┐

│ Authentication      │

│ + Session State     │

└──────────┬──────────┘

&#x20;          │

&#x20;          ▼

┌─────────────────────┐

│   SecurityContext   │

│ tenant + role       │

└──────────┬──────────┘

&#x20;          │

&#x20;          ▼

┌─────────────────────────────┐

│     Agentic RAG Pipeline    │

└──────────────┬──────────────┘

&#x20;              │

&#x20;              ▼

&#x20;     ┌─────────────────┐

&#x20;     │ Hybrid Retrieval│

&#x20;     └────────┬────────┘

&#x20;              │

&#x20;      ┌───────┴────────┐

&#x20;      ▼                ▼

┌─────────────┐   ┌─────────────┐

│  ChromaDB   │   │    BM25     │

│ Dense Search│   │Sparse Search│

└──────┬──────┘   └──────┬──────┘

&#x20;      │                 │

&#x20;      └────────┬────────┘

&#x20;               ▼

&#x20;      ┌─────────────────┐

&#x20;      │   RRF Fusion    │

&#x20;      └────────┬────────┘

&#x20;               ▼

&#x20;      ┌─────────────────┐

&#x20;      │  LLM Reranking  │

&#x20;      └────────┬────────┘

&#x20;               ▼

&#x20;      ┌─────────────────┐

&#x20;      │ Authorized      │

&#x20;      │ Context         │

&#x20;      └────────┬────────┘

&#x20;               ▼

&#x20;      ┌─────────────────┐

&#x20;      │ LLM Generation  │

&#x20;      └────────┬────────┘

&#x20;               ▼

&#x20;      ┌─────────────────┐

&#x20;      │ Answer + Trace  │

&#x20;      └─────────────────┘

````



\---



\## 2. Authentication and Authorization



Authentication establishes the demo user's session.



Authorization is represented by a `SecurityContext` containing:



\* Tenant ID

\* User role



The retrieval layer uses this context when determining which documents can be returned.



Example roles:



| Role      | Access                                                |

| --------- | ----------------------------------------------------- |

| employee  | Company and product information                       |

| executive | Company, products, contracts and employee information |

| admin     | Unrestricted access and evaluation controls           |



The authentication implementation is intended for demonstration purposes.



Production deployments would require an appropriate identity provider and stronger authentication controls.



\---



\## 3. Document Ingestion



Documents are loaded from the `data/` directory.



Supported source formats:



\* Markdown

\* Text



The ingestion pipeline:



1\. Recursively discovers documents.

2\. Reads document contents.

3\. Splits content into paragraph-level chunks.

4\. Adds document subject context to each chunk.

5\. Attaches security metadata.

6\. Generates deterministic document IDs.

7\. Stores documents in ChromaDB.

8\. Adds documents to the BM25 corpus.



Example metadata:



```text

tenant\_id

classification

category

source\_file

file\_path

```



The generated ChromaDB persistence directory is excluded from Git and can be rebuilt from the source dataset.



\---



\## 4. Hybrid Retrieval



The retrieval system combines two complementary approaches.



\### Dense Retrieval



ChromaDB provides semantic vector retrieval.



This allows queries to retrieve documents based on semantic similarity rather than exact keyword matches.



\### Sparse Retrieval



BM25 provides keyword-based retrieval.



This is useful when queries contain specific names, terms, product names or other exact lexical matches.



\### Reciprocal Rank Fusion



The two retrieval results are combined using Reciprocal Rank Fusion (RRF).



```text

Dense Results ──┐

&#x20;               ├──► RRF ──► Candidate Documents

Sparse Results ─┘

```



This allows the system to benefit from both semantic and lexical retrieval.



\---



\## 5. LLM Reranking



After initial candidate retrieval, the system performs an LLM-based reranking step.



The reranker evaluates candidate relevance and determines which retrieved documents should receive higher priority before answer generation.



This creates a pipeline of:



```text

Retrieve broadly

&#x20;     ↓

Fuse candidates

&#x20;     ↓

Rerank candidates

&#x20;     ↓

Generate from selected context

```



\---



\## 6. Agentic RAG



The agent layer coordinates:



\* Security context

\* Retrieval

\* Context handling

\* Answer generation

\* Execution tracing



The goal is to keep security and retrieval concerns separate from the final language-model response.



The LLM should generate answers from the context that has already passed the retrieval and authorization stages.



\---



\## 7. Evaluation



Sentinel RAG includes an automated evaluation suite.



The current benchmark evaluates:



\* Mean Reciprocal Rank (MRR)

\* nDCG@4

\* LLM-as-a-Judge faithfulness



Current baseline:



| Metric            | Result |

| ----------------- | -----: |

| Mean MRR          |   1.00 |

| Mean nDCG@4       |   1.00 |

| Mean Faithfulness |   0.96 |

| Test Cases        |      5 |



These results are based on the included synthetic InsureLLM dataset.



The benchmark is intentionally small and should be treated as a demonstration baseline rather than a production performance guarantee.



\---



\## 8. Data Flow



A typical query follows this flow:



```text

User Query

&#x20;   ↓

Authentication

&#x20;   ↓

SecurityContext

&#x20;   ↓

Tenant / Role Authorization

&#x20;   ↓

Dense + Sparse Retrieval

&#x20;   ↓

RRF Fusion

&#x20;   ↓

LLM Reranking

&#x20;   ↓

Authorized Context

&#x20;   ↓

Agentic Answer Generation

&#x20;   ↓

Answer + Execution Trace

```



\---



\## 9. Design Principles



\### Security before generation



Authorization should be applied before restricted documents reach the answer-generation stage.



\### Hybrid retrieval



Dense and sparse retrieval solve different retrieval problems and can complement each other.



\### Reproducibility



The source dataset and ingestion pipeline are version-controlled while generated indexes remain rebuildable artifacts.



\### Evaluation-driven development



Retrieval and answer quality should be measured rather than judged only through manual testing.



\### Separation of concerns



Authentication, security, ingestion, retrieval, agent execution and evaluation are separated into distinct modules.



\---



\## 10. Production Considerations



This repository is a portfolio prototype.



A production implementation would require additional work around:



\* Identity and access management

\* Secrets management

\* Database infrastructure

\* Tenant isolation

\* Encryption

\* Audit logging

\* Monitoring

\* Rate limiting

\* Automated security testing

\* Retrieval evaluation at larger scale

\* Deployment infrastructure

\* Failure recovery



````



