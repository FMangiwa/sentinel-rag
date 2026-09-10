"""
eval/evaluator.py
Executes benchmark test suites and aggregates metrics across runs.
"""

from typing import Any, Dict, List
from core.agent import AgenticRAGPipeline
from core.security import SecurityContext
from eval.metrics import calculate_mrr, calculate_ndcg, llm_judge_faithfulness


class RAGSuiteEvaluator:

    def __init__(self, agent_pipeline: AgenticRAGPipeline):
        self.pipeline = agent_pipeline

    def run_benchmark(
        self, test_cases: List[Dict[str, Any]], tenant_id: str = "InsureLLM"
    ) -> Dict[str, Any]:
        """
        Runs evaluation across a suite of ground-truth test cases.
        Each test_case should have: 'query', 'expected_doc_ids', 'role'
        """
        results = []

        for test in test_cases:
            sec_ctx = SecurityContext(
                tenant_id=tenant_id, user_role=test.get("role", "admin")
            )
            output = self.pipeline.run(test["query"], sec_ctx)

            retrieved_ids = [c["id"] for c in output["contexts"]]
            expected_sources = set(test.get("expected_sources", []))

            retrieved_sources = [
                c["metadata"].get("source_file", "")
                for c in output["contexts"]
            ]

            mrr = calculate_mrr(retrieved_sources, expected_sources)
            ndcg = calculate_ndcg(retrieved_sources, expected_sources)
            judge = llm_judge_faithfulness(output["answer"], output["contexts"])

            results.append(
                {
                    "query": test["query"],
                    "mrr": mrr,
                    "ndcg": ndcg,
                    "faithfulness_score": judge.get("score", 0.0),
                    "reasoning": judge.get("reasoning", ""),
                }
            )

        avg_mrr = sum(r["mrr"] for r in results) / len(results) if results else 0.0
        avg_ndcg = sum(r["ndcg"] for r in results) / len(results) if results else 0.0
        avg_faith = (
            sum(r["faithfulness_score"] for r in results) / len(results)
            if results
            else 0.0
        )

        return {
            "summary": {
                "mean_mrr": round(avg_mrr, 4),
                "mean_ndcg": round(avg_ndcg, 4),
                "mean_faithfulness": round(avg_faith, 4),
                "total_test_cases": len(results),
            },
            "details": results,
        }