"""
core/agent.py
Agentic Workflow Engine featuring:
- Sub-query decomposition (Multi-hop planning)
- Iterative hybrid retrieval under SecurityContext
- Verification & Hallucination checks
- Self-correction query refinement loops
"""

import json
from typing import Dict, Any, List, Optional
import litellm

from config import cfg
from core.security import SecurityContext
from core.retriever import HybridRetriever


class AgenticRAGPipeline:

    def __init__(self, retriever: HybridRetriever):
        self.retriever = retriever
        
    def expand_query_aliases(query: str) -> str:
        """
        Expands common entity permutations for hybrid keyword search.
        """
        # Simple rule-based or quick LLM query transformation step
        if "manchester university" in query.lower():
            return f"{query} 'University of Manchester'"
        return query

    def _decompose_query(self, user_query: str) -> List[str]:
        """
        Breaks down a complex multi-part query into targeted sub-queries.
        """
        prompt = f"""
        You are an expert query planning agent.
        Analyze the following complex user request and break it down into 1 to 3 distinct, concise sub-queries needed to fully retrieve the relevant facts.

        User Request: "{user_query}"

        Return ONLY a JSON list of strings. Example: ["sub_query_1", "sub_query_2"]
        """
        try:
            response = litellm.completion(
                model=cfg.FAST_LLM,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            parsed = json.loads(content)
            queries = parsed.get(
                "queries", parsed if isinstance(parsed, list) else [user_query]
            )
            return queries if queries else [user_query]
        except Exception as e:
            print(
                f"[Agent Warning] Query decomposition fallback due to error: {e}"
            )
            return [user_query]

    def _check_evidence_sufficiency(
        self, query: str, contexts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Evaluates whether the retrieved context passages contain enough factual evidence 
        to accurately answer the query without hallucinating.
        """
        context_str = "\n---\n".join([doc["text"] for doc in contexts])

        prompt = f"""
        Target Query: "{query}"

        Retrieved Contexts:
        {context_str}

        Task: Evaluate if the contexts contain sufficient factual info to answer the target query.
        Return ONLY a JSON object with:
        - "sufficient": boolean (true/false)
        - "missing_aspects": string (explanation of missing details if false, else empty)
        - "suggested_refinement": string (a refined search query to find missing info if false)
        """
        try:
            response = litellm.completion(
                model=cfg.FAST_LLM,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"[Agent Warning] Evidence check failed: {e}")
            return {
                "sufficient": True,
                "missing_aspects": "",
                "suggested_refinement": "",
            }

    def _generate_grounded_answer(
        self, user_query: str, contexts: List[Dict[str, Any]]
    ) -> str:
        """
        Generates final answer constrained strictly to retrieved context.
        """
        context_str = "\n\n".join(
            [
                f"[Document: {doc.get('metadata', {}).get('source_file', 'Source')}] {doc['text']}"
                for doc in contexts
            ]
        )

        prompt = f"""
        You are an enterprise assistant. Answer the user query using ONLY the provided context passages below.
        Integrate citations naturally using document or source names (e.g., "According to the HR policy..."). 
        DO NOT print raw internal system IDs or UUIDs like "[Source ID: ...]".
        If the context does not contain enough evidence, state what is missing clearly.

        Context Passages:
        {context_str}

        User Query: {user_query}
        """

        response = litellm.completion(
            model=cfg.REASONING_LLM,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content

    def run(
        self,
        user_query: str,
        security_ctx: SecurityContext,
        max_correction_loops: int = 1,
    ) -> Dict[str, Any]:
        """
        Main Agentic Workflow:
        1. Query Planning & Decomposition
        2. Security-Filtered Hybrid Retrieval
        3. Evidence Sufficiency & Hallucination Verification
        4. Self-Correction Loop (Refine query & re-fetch if evidence is insufficient)
        5. Grounded Answer Synthesis
        """
        execution_trace = []

        # 1. Decompose Query
        sub_queries = self._decompose_query(user_query)
        execution_trace.append(
            {"step": "decomposition", "sub_queries": sub_queries}
        )

        accumulated_contexts: Dict[str, Dict[str, Any]] = {}

        # 2. Multi-hop Retrieval across sub-queries
        for sq in sub_queries:
            retrieved = self.retriever.retrieve(sq, security_ctx)
            for doc in retrieved:
                accumulated_contexts[doc["id"]] = doc

        current_contexts = list(accumulated_contexts.values())

        # 3. Evidence Verification & Self-Correction Loop
        for loop in range(max_correction_loops + 1):
            eval_result = self._check_evidence_sufficiency(
                user_query, current_contexts
            )
            execution_trace.append(
                {
                    "step": f"evidence_check_loop_{loop}",
                    "eval_result": eval_result,
                }
            )

            if eval_result.get("sufficient") or loop == max_correction_loops:
                break

            # If insufficient, execute Self-Correction
            refined_query = eval_result.get("suggested_refinement")
            if refined_query:
                execution_trace.append(
                    {
                        "step": f"self_correction_loop_{loop}",
                        "refined_query": refined_query,
                    }
                )
                additional_docs = self.retriever.retrieve(
                    refined_query, security_ctx
                )
                for doc in additional_docs:
                    accumulated_contexts[doc["id"]] = doc
                current_contexts = list(accumulated_contexts.values())

        # 4. Generate Answer
        final_answer = self._generate_grounded_answer(
            user_query, current_contexts
        )

        return {
            "answer": final_answer,
            "contexts": current_contexts,
            "trace": execution_trace,
        }


if __name__ == "__main__":
    # Test Agentic Pipeline Run
    from ingest import MultiTenantIndexer

    indexer = MultiTenantIndexer()
    retriever = HybridRetriever(indexer)
    agent = AgenticRAGPipeline(retriever)

    sec_ctx = SecurityContext(tenant_id="InsureLLM", user_role="admin")
    result = agent.run(
        "Compare Q3 performance and check policy leave days", sec_ctx
    )

    print("\n--- FINAL ANSWER ---")
    print(result["answer"])
    print("\n--- EXECUTION TRACE ---")
    print(json.dumps(result["trace"], indent=2))