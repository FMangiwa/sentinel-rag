import os
from dataclasses import dataclass, field
from typing import Dict, List, Set

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Environment & API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Storage Settings
    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

    # LLM Models (Managed via LiteLLM)
    FAST_LLM: str = "gpt-4o-mini"
    REASONING_LLM: str = "gpt-4o"
    RERANK_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-large"

    # Multi-Tenant & RBAC Policy Rules
    # Defines role hierarchy and default dynamic dynamic filters
    ROLE_PERMISSIONS: Dict[str, Set[str]] = field(
        default_factory=lambda: {
            "admin": {"public", "internal", "executive", "confidential"},
            "executive": {"public", "internal", "executive"},
            "employee": {"public", "internal"},
            "guest": {"public"},
        }
    )

    # Retrieval Defaults
    VECTOR_TOP_K: int = 10
    BM25_TOP_K: int = 10
    RERANK_TOP_K: int = 4
    ALPHA_DENSE_WEIGHT: float = 0.5  # Weight balance between dense and sparse scores


cfg = Config()