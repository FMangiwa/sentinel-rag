"""
core/retriever.py
Hybrid Retriever combining Dense Vector Search (Chroma DB) and
Sparse Keyword Search (BM25) via Reciprocal Rank Fusion (RRF),
followed by LiteLLM Reranking.
"""

import json
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import litellm

from config import cfg
from ingest import MultiTenantIndexer
from core.security import SecurityContext


class HybridRetriever:
    def __init__(self, indexer: MultiTenantIndexer):
        self.indexer = indexer

    def _reciprocal_rank_fusion(
        self, 
        dense_results: List[Dict[str, Any]], 
        sparse_results: List[Dict[str, Any]], 
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Merges dense and sparse search results using Reciprocal Rank Fusion (RRF).
        RRF Score = sum(1 / (k + rank))
        """
        rrf_scores: Dict[str, float] = {}
        doc_map: Dict[str, Dict[str, Any]] = {}

        # Process Dense Vector Results
        for rank, doc in enumerate(dense_results):
            doc_id = doc["id"]
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))

        # Process Sparse BM25 Results
        for rank, doc in enumerate(sparse_results):
            doc_id = doc["id"]
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + (1.0 / (k + rank + 1))

        # Sort documents by accumulated RRF score
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        fused_docs = []
        for doc_id in sorted_doc_ids:
            doc = doc_map[doc_id]
            doc["rrf_score"] = rrf_scores[doc_id]
            fused_docs.append(doc)

        return fused_docs

    def _dense_search(self, query: str, security_ctx: SecurityContext, top_k: int) -> List[Dict[str, Any]]:
        """Executes Chroma vector query with tenant security filters applied."""
        where_clause = security_ctx.build_chroma_where_clause()
        
        results = self.indexer.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=where_clause
        )

        dense_docs = []
        if results and results["ids"] and len(results["ids"][0]) > 0:
            for idx in range(len(results["ids"][0])):
                dense_docs.append({
                    "id": results["ids"][0][idx],
                    "text": results["documents"][0][idx],
                    "metadata": results["metadatas"][0][idx]
                })
        return dense_docs

    def _sparse_search(self, query: str, security_ctx: SecurityContext, top_k: int) -> List[Dict[str, Any]]:
        """Executes BM25 search over tenant-filtered subset of documents."""
        filtered_corpus = security_ctx.filter_bm25_corpus(self.indexer.bm25_corpus)
        if not filtered_corpus:
            return []

        tokenized_corpus = [doc["text"].lower().split() for doc in filtered_corpus]
        bm25_filtered = BM25Okapi(tokenized_corpus)

        tokenized_query = query.lower().split()
        scores = bm25_filtered.get_scores(tokenized_query)
        
        # Zip scores with filtered documents and sort
        scored_docs = list(zip(scores, filtered_corpus))
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        sparse_docs = []
        for score, doc in scored_docs[:top_k]:
            if score > 0.0:  # Only include non-zero keyword matches
                sparse_docs.append(doc)
        return sparse_docs

    def rerank_documents(self, query: str, docs: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
        """
        Uses LiteLLM to rank context snippets by relevance to the target query.
        """
        if not docs:
            return []

        prompt = f"""
        You are a relevance scoring engine.
        Query: "{query}"

        Score each candidate document below from 0 to 10 based on how well it answers the query.
        Return ONLY a JSON list of objects with keys "doc_id" and "score".

        Candidates:
        {json.dumps([{"doc_id": d["id"], "text": d["text"]} for d in docs], indent=2)}
        """

        try:
            response = litellm.completion(
                model=cfg.RERANK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            raw_content = response.choices[0].message.content
            scores_data = json.loads(raw_content)
            
            # Extract scores array (handles object wrappers if returned)
            score_list = scores_data.get("scores", scores_data if isinstance(scores_data, list) else [])
            score_map = {item["doc_id"]: item["score"] for item in score_list if "doc_id" in item and "score" in item}

            for doc in docs:
                doc["rerank_score"] = score_map.get(doc["id"], 0.0)

            reranked_docs = sorted(docs, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            return reranked_docs[:top_k]

        except Exception as e:
            print(f"[Reranker Warning] LLM reranking fallback due to error: {e}")
            return docs[:top_k]

    def retrieve(self, query: str, security_ctx: SecurityContext) -> List[Dict[str, Any]]:
        """
        Full Retrieval Pipeline:
        1. Multi-tenant Dense Vector Search
        2. Multi-tenant Sparse BM25 Search
        3. Reciprocal Rank Fusion (RRF)
        4. LiteLLM LLM-based Reranking
        """
        dense_docs = self._dense_search(query, security_ctx, top_k=cfg.VECTOR_TOP_K)
        sparse_docs = self._sparse_search(query, security_ctx, top_k=cfg.BM25_TOP_K)
        
        fused_docs = self._reciprocal_rank_fusion(dense_docs, sparse_docs)
        reranked_docs = self.rerank_documents(query, fused_docs, top_k=cfg.RERANK_TOP_K)
        
        return reranked_docs


if __name__ == "__main__":
    # Test Hybrid Retrieval Pipeline
    indexer = MultiTenantIndexer()
    retriever = HybridRetriever(indexer)
    sec_ctx = SecurityContext(tenant_id="InsureLLM", user_role="admin")

    results = retriever.retrieve("What is the Q3 revenue performance?", sec_ctx)
    print(f"Retrieved {len(results)} relevant documents:")
    for doc in results:
        print(f"- [Score: {doc.get('rerank_score')}] {doc['text']}")