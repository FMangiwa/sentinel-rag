"""
eval/metrics.py
Retrieval metrics (MRR, nDCG) and LLM-as-a-Judge evaluators.
"""

import json
import math
from typing import Any, Dict, List, Set
import litellm
from config import cfg


def calculate_mrr(
    retrieved_ids: List[str], ground_truth_ids: Set[str]
) -> float:
    """Calculates Mean Reciprocal Rank (MRR) for retrieved documents."""
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in ground_truth_ids:
            return 1.0 / rank
    return 0.0


def calculate_ndcg(
    retrieved_ids: List[str], ground_truth_ids: Set[str], k: int = 4
) -> float:
    """Calculates Normalized Discounted Cumulative Gain (nDCG@K)."""
    dcg = 0.0
    retrieved_unique = list(dict.fromkeys(retrieved_ids))

    dcg = 0.0
    for i, doc_id in enumerate(retrieved_unique[:k], start=1):
        rel = 1.0 if doc_id in ground_truth_ids else 0.0
        dcg += rel / math.log2(i + 1)

    ideal_relevant = min(len(ground_truth_ids), k)
    idcg = sum(
        1.0 / math.log2(i + 1)
        for i in range(1, ideal_relevant + 1)
    )
    return dcg / idcg if idcg > 0 else 0.0


def llm_judge_faithfulness(answer: str, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    LLM-as-a-Judge: Evaluates if the generated answer is faithful to the context (no hallucinations).
    """
    context_str = "\n".join([c["text"] for c in contexts])
    prompt = f"""
    You are an AI evaluator. Assess whether the generated answer is strictly grounded in the given context.
    
    Context:
    {context_str}

    Generated Answer:
    {answer}

    Return ONLY a JSON object with:
    - "score": float between 0.0 (total hallucination) and 1.0 (fully grounded)
    - "reasoning": brief explanation
    """
    try:
        response = litellm.completion(
            model=cfg.FAST_LLM,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"score": 0.0, "reasoning": f"Evaluation error: {e}"}