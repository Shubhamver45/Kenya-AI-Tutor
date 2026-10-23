"""
Stage 5: Orchestration Pipeline with Bounded Retry Loop.
Wires:
  1. Stage 3 (Follow-up Query Rewriting)
  2. Stage 2 (Hybrid Search: BM25 + Dense Vectors + Metadata Filter)
  3. Stage 4 (Grounded Answering with Honest Refusal)
  4. Stage 5 (Grounding Validation with Maximum 1 Retry)
  5. Stage 6 (Trace Collection for Observability)
"""

from __future__ import annotations

import time
from typing import Any
from retrieval.hybrid_search import hybrid_search
from llm.client import rewrite_query, answer, validate_grounding
from telemetry.collector import Trace, trace_store

# Maximum retries: bounded strictly to 1, exactly as required by the reference document
MAX_RETRIES = 1


def run_pipeline(
    question: str,
    history: list[dict] | None = None,
    grade: int | None = None,
    subject: str | None = None,
    simulate_initial_hallucination: bool = False,
) -> Trace:
    """
    Executes the full tutor pipeline and stores the execution trace.
    
    If simulate_initial_hallucination is True (for testing Stage 5 demo):
      - Attempt 1 deliberately fails validation
      - Pipeline automatically retries once (Attempt 2) with grounded correction
      - Demonstrates the bounded retry loop in action!
    """
    history = history or []
    trace = Trace()
    trace.original_question = question
    t_start = time.perf_counter()

    q_lower = question.strip().lower()
    is_greeting = q_lower in {
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
        "how are you", "hujambo", "habari", "sasa", "mambo", "thanks", "thank you", "asante"
    }
    if is_greeting:
        trace.rewritten_query = question
        trace.rewrite_usage = {"mode": "greeting_passthrough", "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "latency_ms": 0}
        trace.chunks = []
        trace.retrieval_ms = 0.0
        trace.retrieval_mode = "conversational_direct"
        ans_text, ans_usage = answer(query=question, chunks=[])
        trace.answer = ans_text
        trace.answer_usage = ans_usage
        trace.model = ans_usage.get("model", "gemini-3.5-flash-lite")
        trace.validation_passed = True
        trace.total_ms = round((time.perf_counter() - t_start) * 1000, 2)
        trace.total_tokens = ans_usage.get("total_tokens", 0)
        trace_store.add(trace)
        return trace

    # ──────────────────────────────────────────────────────────────────────────
    # Stage 3: Query Rewriting
    # ──────────────────────────────────────────────────────────────────────────
    if history:
        rewritten, rw_usage = rewrite_query(history, question)
        trace.rewritten_query = rewritten
        trace.rewrite_usage = rw_usage
    else:
        trace.rewritten_query = question
        trace.rewrite_usage = {
            "mode": "first_turn_passthrough",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "latency_ms": 0,
        }

    search_query = trace.rewritten_query

    # ──────────────────────────────────────────────────────────────────────────
    # Stage 2: Hybrid Retrieval (BM25 + Semantic Vectors + Filters)
    # ──────────────────────────────────────────────────────────────────────────
    chunks, retrieval_ms, backend = hybrid_search(
        query=search_query,
        top_k=3,
        grade=grade,
        subject=subject,
    )
    trace.chunks = chunks
    trace.retrieval_ms = retrieval_ms
    trace.retrieval_mode = backend

    # ──────────────────────────────────────────────────────────────────────────
    # Stage 4 + Stage 5: Answer Generation + Validation with Bounded Retry (Max 1)
    # ──────────────────────────────────────────────────────────────────────────
    attempt = 0
    while attempt <= MAX_RETRIES:
        is_first_and_hallucinating = (attempt == 0 and simulate_initial_hallucination)
        
        ans_text, ans_usage = answer(
            query=search_query,
            chunks=chunks,
            force_hallucination=is_first_and_hallucinating,
        )
        trace.answer = ans_text
        trace.answer_usage = ans_usage
        trace.model = ans_usage.get("model", "llama-3.1-8b-instant")
        trace.attempts = attempt + 1

        is_grounded, val_usage = validate_grounding(ans_text, chunks)
        trace.validation_passed = is_grounded
        trace.validation_usage = val_usage

        if is_grounded:
            # Succeeded! Bounded loop terminates cleanly
            break

        if attempt < MAX_RETRIES:
            # Trigger exactly one retry
            trace.retried = True
            attempt += 1
            # Next iteration generates a strictly grounded answer
            simulate_initial_hallucination = False
        else:
            # Exceeded fixed retry budget -> stop (bounded loop safeguard)
            break

    # Calculate Totals for Observability (Stage 6)
    trace.total_ms = round((time.perf_counter() - t_start) * 1000, 2)
    trace.total_tokens = (
        trace.rewrite_usage.get("total_tokens", 0)
        + trace.answer_usage.get("total_tokens", 0)
        + trace.validation_usage.get("total_tokens", 0)
    )

    # Save to in-memory trace store
    trace_store.add(trace)
    return trace
