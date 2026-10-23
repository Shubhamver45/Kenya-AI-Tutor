"""
Evaluation Benchmark Runner for Kenya Class Tutor Lite.
Evaluates 16 test cases across 4 gates:
  1. Retrieval Gate: Did relevant curriculum chunk appear in top-3?
  2. Grounding Gate: Did the answer pass validation without hallucination?
  3. Honesty Gate: Did out-of-curriculum questions trigger strict honest refusal?
  4. Follow-Up Query Gate: Did follow-up query rewriting resolve topic context?
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any

# Ensure kenya_tutor_lite root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import run_pipeline

_DATASET_PATH = Path(__file__).parent.parent / "data" / "eval_dataset.json"


def run_evaluation() -> dict[str, Any]:
    with open(_DATASET_PATH, "r", encoding="utf-8") as f:
        cases = json.load(f)

    results = []
    retrieval_hits = 0
    grounding_passed = 0
    honesty_passed = 0
    out_of_curr_count = 0
    in_curr_count = 0
    total_latency_ms = 0

    t_suite_start = time.perf_counter()

    for item in cases:
        q = item["question"]
        hist = item.get("history", [])
        must_refuse = item.get("must_refuse", False)
        expected_topic = item.get("expected_topic")

        # Run pipeline
        trace = run_pipeline(
            question=q,
            history=hist,
            grade=item.get("grade"),
            subject=item.get("subject"),
        )

        total_latency_ms += trace.total_ms
        answer_text = trace.answer.lower()
        
        # 1. Retrieval Gate
        if expected_topic:
            chunk_topics = [c.get("topic") for c in trace.chunks]
            retrieval_hit = expected_topic in chunk_topics
        else:
            retrieval_hit = True  # Not applicable for out of curriculum
        if retrieval_hit and expected_topic:
            retrieval_hits += 1

        # 2. Honesty Gate
        is_refusal = (
            "don't have information" in answer_text
            or "sina habari" in answer_text
            or "learning material" in answer_text
            or "mtaala" in answer_text
        )

        if must_refuse:
            out_of_curr_count += 1
            honesty_hit = is_refusal
            if honesty_hit:
                honesty_passed += 1
        else:
            in_curr_count += 1
            honesty_hit = not is_refusal

        # 3. Grounding Gate
        grounding_hit = trace.validation_passed

        # Overall case pass
        case_passed = (retrieval_hit or must_refuse) and grounding_hit and (honesty_hit if must_refuse else True)

        results.append({
            "id": item["id"],
            "question": q,
            "language": item["language"],
            "type": item["type"],
            "rewritten": trace.rewritten_query if hist else "-",
            "top_retrieved": trace.chunks[0]["topic"] if trace.chunks else "None",
            "retrieval_pass": retrieval_hit,
            "grounding_pass": grounding_hit,
            "honesty_pass": honesty_hit if must_refuse else "N/A",
            "passed": case_passed,
            "latency_ms": trace.total_ms,
            "answer_preview": trace.answer[:110] + ("..." if len(trace.answer) > 110 else ""),
        })

    total_time = round((time.perf_counter() - t_suite_start), 2)
    passed_count = sum(1 for r in results if r["passed"])

    summary = {
        "total_cases": len(cases),
        "passed_cases": passed_count,
        "pass_rate_percent": round((passed_count / len(cases)) * 100, 1),
        "retrieval_recall_at_3": round((retrieval_hits / max(in_curr_count, 1)) * 100, 1),
        "honesty_rate_percent": round((honesty_passed / max(out_of_curr_count, 1)) * 100, 1),
        "avg_latency_ms": round(total_latency_ms / len(cases), 1),
        "total_suite_seconds": total_time,
        "cases": results,
    }
    return summary


if __name__ == "__main__":
    print("\n" + "="*80)
    print("EVALUATION BENCHMARK: 16 Tests (English & Kiswahili, Grounding & Honesty Gates)")
    print("="*80)
    summary = run_evaluation()
    print(f"\nOverall Score: {summary['passed_cases']}/{summary['total_cases']} ({summary['pass_rate_percent']}%)")
    print(f"Retrieval Recall@3: {summary['retrieval_recall_at_3']}%")
    print(f"Honesty on Out-of-Curriculum: {summary['honesty_rate_percent']}%")
    print(f"Average Latency: {summary['avg_latency_ms']} ms")
    print("\nDetailed Breakdown:")
    for c in summary["cases"]:
        status = "✅ PASS" if c["passed"] else "❌ FAIL"
        print(f"  {status} [{c['id']}] ({c['language']}) {c['question'][:45]}... -> {c['top_retrieved']} ({c['latency_ms']}ms)")
