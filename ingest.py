import os
import re
import glob
import json
import uuid
from typing import Any, Dict, List, Optional

import chromadb
from rank_bm25 import BM25Okapi

from config import cfg


class MultiTenantIndexer:

    def __init__(
        self, persist_dir: str = cfg.CHROMA_PERSIST_DIR, collection_name: str = "enterprise_rag"
    ):
        self.client = chromadb.PersistentClient(path=persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )
        self.bm25_index_path = os.path.join(persist_dir, "bm25_corpus.json")
        self.bm25_corpus: List[Dict[str, Any]] = []
        self.bm25: Optional[BM25Okapi] = None
        self._load_bm25_index()

    def _tokenize(self, text: str) -> List[str]:
        # Clean non-alphanumeric chars and convert to lowercase
        tokens = re.findall(r'\b\w+\b', text.lower())
        # Strip common filler stop words like 'of', 'the', 'to' for BM25 matching
        stop_words = {"of", "the", "in", "at", "to", "a", "an"}
        return [t for t in tokens if t not in stop_words]
        
    def _load_bm25_index(self):
        """Loads BM25 corpus state from disk if present."""
        if os.path.exists(self.bm25_index_path):
            with open(self.bm25_index_path, "r", encoding="utf-8") as f:
                self.bm25_corpus = json.load(f)
            tokenized_corpus = [
                self._tokenize(doc["text"]) for doc in self.bm25_corpus
            ]
            if tokenized_corpus:
                self.bm25 = BM25Okapi(tokenized_corpus)

    def _save_bm25_index(self):
        """Persists BM25 corpus state to disk."""
        os.makedirs(os.path.dirname(self.bm25_index_path), exist_ok=True)
        with open(self.bm25_index_path, "w", encoding="utf-8") as f:
            json.dump(self.bm25_corpus, f, indent=2)

    def add_documents(
        self,
        texts: List[str],
        metadatas: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
    ) -> List[str]:
        """Adds documents with strict multi-tenant metadata tagging."""
        ids = [str(uuid.uuid4()) for _ in texts]

        for meta in metadatas:
            if "tenant_id" not in meta or "classification" not in meta:
                raise ValueError(
                    "Each document metadata must specify 'tenant_id' and 'classification'."
                )

        kwargs = {"documents": texts, "metadatas": metadatas, "ids": ids}
        if embeddings:
            kwargs["embeddings"] = embeddings

        self.collection.add(**kwargs)

        for i, text in enumerate(texts):
            self.bm25_corpus.append(
                {"id": ids[i], "text": text, "metadata": metadatas[i]}
            )

        tokenized_corpus = [
            self._tokenize(doc["text"]) for doc in self.bm25_corpus
        ]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self._save_bm25_index()

        return ids

    def ingest_data_directory(
        self,
        data_dir: str = "./data",
        default_tenant: str = "InsureLLM",
        default_classification: str = "internal",
    ) -> List[str]:
        """
        Recursively scans any directory structure under `./data/`.
        Reads all .md and .txt files and prepends document context headers to each chunk.
        """
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            print(f"Created '{data_dir}' folder. Drop your document folders inside it.")
            return []

        # Search recursively for all .md and .txt files inside data_dir
        file_paths = (
            glob.glob(os.path.join(data_dir, "**", "*.md"), recursive=True) +
            glob.glob(os.path.join(data_dir, "**", "*.txt"), recursive=True)
        )

        if not file_paths:
            print(f"No .md or .txt files found anywhere inside '{data_dir}'.")
            return []

        texts = []
        metadatas = []

        for path in file_paths:
            rel_path = os.path.relpath(path, data_dir)
            path_parts = rel_path.split(os.sep)

            # Extract category name from immediate subfolder
            category = path_parts[0].lower() if len(path_parts) > 1 else "general"

            # Derive clean subject title from filename (e.g. 'john_doe_resume.md' -> 'John Doe Resume')
            filename_clean = (
                os.path.basename(path)
                .replace(".md", "")
                .replace(".txt", "")
                .replace("_", " ")
                .replace("-", " ")
                .title()
            )

            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    continue

                # Paragraph-level splitting
                raw_paragraphs = [c.strip() for c in content.split("\n\n") if len(c.strip()) > 20]

                # ====================================================================
                # 👇 QUICK FIX: PREPEND SUBJECT CONTEXT HEADER TO EVERY CHUNK 👇
                # ====================================================================
                for chunk in raw_paragraphs:
                    grounded_chunk = f"Document Subject: {filename_clean}\nContent:\n{chunk}"

                    texts.append(grounded_chunk)
                    metadatas.append({
                        "tenant_id": default_tenant,
                        "classification": default_classification,
                        "category": category,
                        "source_file": os.path.basename(path),
                        "file_path": rel_path,
                    })

        if texts:
            print(f"Found {len(texts)} chunks across {len(file_paths)} files in '{data_dir}'.")
            return self.add_documents(texts, metadatas)
        return []


if __name__ == "__main__":
    indexer = MultiTenantIndexer()
    print("Ingesting all files and subfolders from ./data with context headers...")
    ids = indexer.ingest_data_directory("./data", default_tenant="InsureLLM")
    print(f"✅ Successfully ingested {len(ids)} grounded document chunks into Chroma DB and BM25.")