"""
Stage 6: Trace collector for observability.
Captures each stage of the pipeline:
  original question -> rewritten query -> retrieved chunks + scores
  -> model answer -> validation verdict -> latencies -> token usage.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class Trace:
    trace_id: str = field(default_factory=lambda: f"tr_{int(time.time()*1000)}")
    timestamp: float = field(default_factory=time.time)
    original_question: str = ""
    rewritten_query: str = ""
    rewrite_usage: dict[str, Any] = field(default_factory=dict)
    
    # Retrieval
    chunks: list[dict[str, Any]] = field(default_factory=list)
    retrieval_ms: float = 0.0
    retrieval_mode: str = "hybrid (BM25 + Dense Semantic RRF)"
    
    # Generation & Validation
    model: str = "llama-3.1-8b-instant"
    answer: str = ""
    answer_usage: dict[str, Any] = field(default_factory=dict)
    
    attempts: int = 1
    retried: bool = False
    validation_passed: bool = True
    validation_usage: dict[str, Any] = field(default_factory=dict)
    
    # Totals
    total_ms: float = 0.0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        # Format human-friendly timestamp
        data["formatted_time"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))
        return data

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


class TraceStore:
    """In-memory trace history store with optional persistence."""
    def __init__(self, max_traces: int = 50):
        self._traces: list[Trace] = []
        self._max_traces = max_traces

    def add(self, trace: Trace) -> None:
        self._traces.insert(0, trace)
        if len(self._traces) > self._max_traces:
            self._traces.pop()

    def get_latest(self) -> Trace | None:
        return self._traces[0] if self._traces else None

    def get_all(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self._traces]

    def get_by_id(self, trace_id: str) -> dict[str, Any] | None:
        for t in self._traces:
            if t.trace_id == trace_id:
                return t.to_dict()
        return None


# Global trace store for the application
trace_store = TraceStore()
