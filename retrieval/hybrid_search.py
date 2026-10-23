"""
Stage 2: Hybrid Search — BM25 (keyword) + Dense Semantic Embeddings + Metadata Filter.
Combines exact lexical matching with semantic dense vectors using Reciprocal Rank Fusion (RRF).

Includes:
  - Multilingual stopword filtering to avoid false positives on filler words (e.g. "what you should do")
  - Confidence relevance thresholding to ensure low-confidence noise is discarded
  - sentence-transformers or fast scikit-learn multilingual vectorizer
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any
import numpy as np
from rank_bm25 import BM25Okapi

_CURRICULUM_PATH = Path(__file__).parent.parent / "data" / "curriculum.json"

_corpus: list[dict] | None = None
_bm25: BM25Okapi | None = None
_vector_backend: str = "unknown"
_vector_encoder: Any = None
_corpus_embeddings: np.ndarray | None = None

STOPWORDS = {
    # English
    "what", "is", "a", "an", "the", "in", "on", "at", "for", "with", "about", "to", "from",
    "you", "your", "should", "do", "can", "tell", "me", "are", "of", "and", "or", "it",
    "this", "that", "how", "why", "who", "which", "will", "would", "be", "been", "have", "has",
    "had", "i", "we", "they", "he", "she", "there", "their", "so", "just", "please",
    # Kiswahili
    "ni", "ya", "wa", "kwa", "katika", "na", "au", "za", "la", "cha", "vya", "kama", "je",
    "hivi", "yake", "kufanya", "tu", "tafadhali"
}


def load_corpus() -> list[dict]:
    global _corpus
    if _corpus is None:
        with open(_CURRICULUM_PATH, "r", encoding="utf-8") as f:
            _corpus = json.load(f)
    return _corpus


def _tokenize_text(text: str) -> list[str]:
    """Tokenize and filter out non-informative stopwords."""
    words = re.findall(r"\b\w+\b", text.lower())
    filtered = [w for w in words if w not in STOPWORDS and len(w) > 1]
    return filtered if filtered else words


def _get_bm25() -> BM25Okapi:
    global _bm25
    if _bm25 is None:
        corpus = load_corpus()
        tokenized = [
            _tokenize_text(
                f"Grade {doc.get('grade', '')} {doc.get('subject', '')} {doc.get('strand', '')} {doc.get('substrand', '')} {doc.get('topic', '')} {doc.get('text', '')}"
            )
            for doc in corpus
        ]
        _bm25 = BM25Okapi(tokenized)
    return _bm25


def _init_vector_engine():
    global _vector_backend, _vector_encoder, _corpus_embeddings
    if _corpus_embeddings is not None:
        return

    corpus = load_corpus()
    passages = [
        f"Grade {d.get('grade', '')} {d.get('subject', '')} - {d.get('strand', '')} - {d.get('substrand', '')} ({d.get('topic', '')}): {d.get('text', '')}"
        for d in corpus
    ]

    try:
        from sentence_transformers import SentenceTransformer
        print("[retrieval] Loading sentence-transformers model (intfloat/multilingual-e5-small)...")
        model = SentenceTransformer("intfloat/multilingual-e5-small")
        embs = model.encode([f"passage: {p}" for p in passages], normalize_embeddings=True)
        _vector_encoder = model
        _corpus_embeddings = embs
        _vector_backend = "multilingual-e5-small (Dense Neural Transformer)"
    except Exception as e:
        from sklearn.feature_extraction.text import TfidfVectorizer
        print(f"[retrieval] Using fast multilingual semantic n-gram vectorizer ({e})...")
        vec = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            sublinear_tf=True,
            norm="l2"
        )
        embs = vec.fit_transform(passages).toarray()
        _vector_encoder = vec
        _corpus_embeddings = embs
        _vector_backend = "Multilingual Semantic Vectorizer (Sublinear N-Gram / Cosine)"


def _encode_query(query: str) -> np.ndarray:
    _init_vector_engine()
    if _vector_backend.startswith("multilingual-e5"):
        q_emb = _vector_encoder.encode([f"query: {query}"], normalize_embeddings=True)[0]
        return q_emb
    else:
        q_vec = _vector_encoder.transform([query]).toarray()[0]
        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm
        return q_vec


def _rrf(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)


def hybrid_search(
    query: str,
    top_k: int = 3,
    grade: int | None = None,
    subject: str | None = None,
) -> tuple[list[dict], float, str]:
    """
    Executes hybrid search with stopword filtering and relevance thresholding.
    Returns: (results_list, latency_ms, vector_backend)
    """
    t0 = time.perf_counter()
    corpus = load_corpus()
    _init_vector_engine()

    # Apply Metadata Filters
    if grade is not None or (subject and subject.strip()):
        candidate_idx = [
            i for i, doc in enumerate(corpus)
            if (grade is None or doc["grade"] == grade)
            and (not subject or doc["subject"].strip().lower() == subject.strip().lower())
        ]
    else:
        candidate_idx = list(range(len(corpus)))

    if not candidate_idx:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        return [], elapsed, _vector_backend

    # 1. BM25 keyword scoring with filtered query tokens
    q_tokens = [w for w in re.findall(r"\b\w+\b", query.lower()) if w not in STOPWORDS]
    bm25 = _get_bm25()
    
    if q_tokens:
        all_bm25 = bm25.get_scores(q_tokens)
    else:
        all_bm25 = np.zeros(len(corpus))

    bm25_sorted = sorted(candidate_idx, key=lambda i: all_bm25[i], reverse=True)

    # 2. Vector semantic scoring
    q_vec = _encode_query(query)
    sims = _corpus_embeddings @ q_vec
    vec_sorted = sorted(candidate_idx, key=lambda i: sims[i], reverse=True)

    # 3. Reciprocal Rank Fusion
    rrf_scores: dict[int, float] = {}
    bm25_rank_map: dict[int, int] = {}
    vec_rank_map: dict[int, int] = {}

    for rank, idx in enumerate(bm25_sorted):
        bm25_rank_map[idx] = rank + 1
        rrf_scores[idx] = rrf_scores.get(idx, 0.0) + _rrf(rank + 1)

    for rank, idx in enumerate(vec_sorted):
        vec_rank_map[idx] = rank + 1
        rrf_scores[idx] = rrf_scores.get(idx, 0.0) + _rrf(rank + 1)

    # Strict Relevance Filter:
    # A candidate is only valid if it has real BM25 lexical match (> 0.3) OR strong vector cosine similarity (> 0.18)
    valid_candidates = [
        idx for idx in candidate_idx
        if (all_bm25[idx] > 0.3) or (sims[idx] >= 0.18 and len(q_tokens) > 0)
    ]

    # If filtered candidate_idx yielded no valid match, try searching the entire curriculum
    if not valid_candidates and len(candidate_idx) < len(corpus):
        candidate_idx = list(range(len(corpus)))
        bm25_sorted = sorted(candidate_idx, key=lambda i: all_bm25[i], reverse=True)
        vec_sorted = sorted(candidate_idx, key=lambda i: sims[i], reverse=True)
        rrf_scores = {}
        bm25_rank_map = {}
        vec_rank_map = {}
        for rank, idx in enumerate(bm25_sorted):
            bm25_rank_map[idx] = rank + 1
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + _rrf(rank + 1)
        for rank, idx in enumerate(vec_sorted):
            vec_rank_map[idx] = rank + 1
            rrf_scores[idx] = rrf_scores.get(idx, 0.0) + _rrf(rank + 1)

        valid_candidates = [
            idx for idx in candidate_idx
            if (all_bm25[idx] > 0.3) or (sims[idx] >= 0.18 and len(q_tokens) > 0)
        ]

    # If no substantive tokens or no candidate passed the relevance threshold
    if not valid_candidates or not q_tokens:
        elapsed = round((time.perf_counter() - t0) * 1000, 2)
        return [], elapsed, _vector_backend

    top_indices = sorted(valid_candidates, key=lambda i: rrf_scores[i], reverse=True)[:top_k]

    results = []
    for idx in top_indices:
        doc = dict(corpus[idx])
        doc["bm25_score"] = round(float(all_bm25[idx]), 4)
        doc["vector_score"] = round(float(sims[idx]), 4)
        doc["rrf_score"] = round(float(rrf_scores[idx]), 6)
        doc["bm25_rank"] = bm25_rank_map.get(idx, -1)
        doc["vector_rank"] = vec_rank_map.get(idx, -1)
        results.append(doc)

    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    return results, elapsed, _vector_backend


def compare_retrieval(query: str, top_k: int = 3) -> dict[str, Any]:
    corpus = load_corpus()
    _init_vector_engine()
    
    q_tokens = [w for w in re.findall(r"\b\w+\b", query.lower()) if w not in STOPWORDS]
    bm25 = _get_bm25()
    all_bm25 = bm25.get_scores(q_tokens) if q_tokens else np.zeros(len(corpus))
    
    bm25_top_idx = sorted(range(len(corpus)), key=lambda i: all_bm25[i], reverse=True)[:top_k]
    bm25_results = [
        {"id": corpus[i]["id"], "topic": corpus[i]["topic"], "score": round(float(all_bm25[i]), 3), "text": corpus[i]["text"][:90] + "..."}
        for i in bm25_top_idx if all_bm25[i] > 0
    ]

    q_vec = _encode_query(query)
    sims = _corpus_embeddings @ q_vec
    vec_top_idx = sorted(range(len(corpus)), key=lambda i: sims[i], reverse=True)[:top_k]
    vec_results = [
        {"id": corpus[i]["id"], "topic": corpus[i]["topic"], "score": round(float(sims[i]), 3), "text": corpus[i]["text"][:90] + "..."}
        for i in vec_top_idx
    ]

    hybrid_res, latency, backend = hybrid_search(query, top_k=top_k)

    return {
        "query": query,
        "bm25_top": bm25_results,
        "vector_top": vec_results,
        "hybrid_top": hybrid_res,
        "backend": backend,
        "latency_ms": latency,
    }
