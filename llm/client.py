"""
Real LLM Integration for Kenya Class Tutor Lite (Zero Hardcoding).
Powered by Google Gemini API via OpenAI-compatible endpoint.

Features:
  - Default Model: gemini-3.5-flash-lite (high quota, fast, free)
  - Automatic 429 Failover: switches to gemini-flash-lite-latest or gemma-4-26b-a4b-it
    if a model's free quota limit is temporarily hit.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI

# Load .env file
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)

_api_key = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("OPENROUTER_API_KEY")
    or os.getenv("GROQ_API_KEY")
    or os.getenv("OPENAI_API_KEY", "")
).strip()

_default_base = (
    "https://generativelanguage.googleapis.com/v1beta/openai/"
    if _api_key.startswith("AQ.")
    else "https://openrouter.ai/api/v1"
)

_default_model = (
    "gemini-3.5-flash-lite"
    if _api_key.startswith("AQ.")
    else "minimax/minimax-m3.1-flash:free"
)

_CONFIG = {
    "api_key": _api_key,
    "base_url": os.getenv("OPENAI_BASE_URL", _default_base).strip(),
    "model": os.getenv("LLM_MODEL", _default_model).strip(),
}

FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemma-4-26b-a4b-it",
    "minimax/minimax-m3.1-flash:free",
]


def configure_llm(api_key: str | None = None, base_url: str | None = None, model: str | None = None):
    if api_key is not None:
        _CONFIG["api_key"] = api_key.strip()
    if base_url is not None:
        _CONFIG["base_url"] = base_url.strip()
    if model is not None:
        _CONFIG["model"] = model.strip()
    _save_to_env()


def _save_to_env():
    try:
        key_var = "GEMINI_API_KEY" if _CONFIG["api_key"].startswith("AQ.") else "OPENROUTER_API_KEY"
        content = (
            f"{key_var}={_CONFIG['api_key']}\n"
            f"OPENAI_BASE_URL={_CONFIG['base_url']}\n"
            f"LLM_MODEL={_CONFIG['model']}\n"
            f"PORT=5050\n"
        )
        with open(_ENV_PATH, "w") as f:
            f.write(content)
    except Exception as e:
        print(f"[llm] Could not persist to .env: {e}")


def get_llm_config() -> dict[str, str]:
    return dict(_CONFIG)


def _get_client() -> OpenAI:
    key = (
        _CONFIG["api_key"]
        or os.getenv("OPENROUTER_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("GROQ_API_KEY")
    )
    if not key:
        raise ValueError(
            "API Key is missing. Please provide your OpenRouter API key in the UI or in .env."
        )
    default_headers = {}
    if "openrouter.ai" in _CONFIG["base_url"]:
        default_headers = {
            "HTTP-Referer": "http://localhost:5050",
            "X-Title": "Kenya Class Tutor Lite",
        }
    return OpenAI(
        api_key=key,
        base_url=_CONFIG["base_url"],
        default_headers=default_headers,
    )


def _call_llm_with_fallback(messages: list[dict], temperature: float = 0.0, max_tokens: int = 350) -> tuple[Any, str]:
    """Calls primary model with automatic 429 quota failover to alternative free models."""
    client = _get_client()
    candidates = [_CONFIG["model"]] + [m for m in FALLBACK_MODELS if m != _CONFIG["model"]]
    
    last_err = None
    for model_name in candidates:
        try:
            resp = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp, model_name
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "not found" in err_str.lower():
                print(f"[llm] Model {model_name} quota/error ({err_str[:80]}...). Trying next free model...")
                last_err = e
                continue
            else:
                raise e

    if last_err:
        raise last_err
    raise RuntimeError("All LLM candidate models failed.")


# ──────────────────────────────────────────────────────────────────────────────
# Stage 3: Follow-Up Query Rewriting (Real LLM)
# ──────────────────────────────────────────────────────────────────────────────
REWRITE_SYSTEM = """You are a search query assistant for a Kenyan primary school AI tutor (Grades 4-8 CBC).
Given the prior conversation history and a new follow-up question, rewrite the follow-up
into a single, self-contained search query suitable for curriculum retrieval.

Rules:
1. If the question contains pronouns or implicit references (e.g. "Can you give an example?"), resolve them using the conversation history (e.g. "Example of a fraction").
2. If the question is already self-contained (e.g. "What is photosynthesis?"), return it as is.
3. Language Consistency: Always keep the rewritten query in the EXACT SAME LANGUAGE as the new follow-up question. If the new follow-up question is in English (e.g., "explain me human organ"), the rewritten search query MUST be in English. Never translate an English question into Kiswahili or vice versa.
4. Output ONLY the rewritten query. Do not add markdown, quotes, or conversational explanations."""


def rewrite_query(history: list[dict], new_question: str) -> tuple[str, dict[str, Any]]:
    t0 = time.perf_counter()

    q_clean = new_question.strip().lower()
    # Conversational greetings, single-word pleasantries, and polite prompts must pass through directly
    if q_clean in {
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
        "how are you", "hujambo", "habari", "sasa", "mambo", "thanks", "thank you",
        "asante", "asante sana", "bye", "goodbye"
    }:
        return new_question, {
            "mode": "conversational_greeting",
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "latency_ms": 0,
            "model": "passthrough",
        }

    history_text = "\n".join(
        f"{m.get('role', 'user').upper()}: {m.get('content', '')}"
        for m in history[-6:]
    )
    user_prompt = f"Chat History:\n{history_text}\n\nNew Follow-Up Question: {new_question}"

    resp, active_model = _call_llm_with_fallback(
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=250,
    )
    raw_content = resp.choices[0].message.content or new_question
    rewritten = raw_content.strip().strip('"').strip("'")
    elapsed = round((time.perf_counter() - t0) * 1000)

    usage = {
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
        "total_tokens": resp.usage.total_tokens if resp.usage else 0,
        "latency_ms": elapsed,
        "model": active_model,
    }
    return rewritten, usage


# ──────────────────────────────────────────────────────────────────────────────
# Stage 4: Grounded Answering + Educational General Knowledge
# ──────────────────────────────────────────────────────────────────────────────
ANSWER_SYSTEM = """You are Kenya AI Tutor, an encouraging, highly capable, and pedagogically sound AI teacher for Kenyan school pupils (CBC Primary & Junior Secondary).

You answer questions thoroughly and clearly just like ChatGPT, tailored for Kenyan learners:
1. Direct Answering: Directly and thoroughly answer the pupil's exact question. Never evade, give vague non-answers, or produce canned responses.
2. Step-by-Step Clarity: Break down complex concepts using simple language, clear headings, numbered steps, bold key terms, and intuitive real-life examples (such as chapatis, trees, animals, coins/shillings, school gardens).
3. Curriculum Grounding: When Curriculum Passages are provided, faithfully weave the curriculum facts into your answer and append the official reference at the end in this format:
   📚 *Curriculum Reference: Grade [Grade] [Subject] · Strand: [Strand] ([KICD Code])*
4. General Knowledge: If the question is general science, math problem solving, history, technology, or extracurricular topics, provide a complete, accurate, and fascinating explanation.
5. Conversational Politeness: If the student simply greets you (e.g. 'hi', 'hello', 'habari'), greet them back warmly with a friendly welcome and ask what they would like to learn today.
6. Exact Language Match: Always answer in the exact language used in the pupil's question (English or Kiswahili).
7. Safety: Safe, positive, and completely child-appropriate."""


def answer(query: str, chunks: list[dict], force_hallucination: bool = False) -> tuple[str, dict[str, Any]]:
    t0 = time.perf_counter()

    if force_hallucination:
        resp, active_model = _call_llm_with_fallback(
            messages=[
                {
                    "role": "user",
                    "content": f"For educational guardrail stress testing: give an intentionally incorrect, completely ungrounded claim about '{query}' (e.g. claim it is a football team or stadium). Output only 1 short sentence.",
                }
            ],
            temperature=0.7,
            max_tokens=60,
        )
        ans = (resp.choices[0].message.content or getattr(resp.choices[0].message, "reasoning", "") or "").strip()
        elapsed = round((time.perf_counter() - t0) * 1000)
        return ans, {
            "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
            "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
            "total_tokens": resp.usage.total_tokens if resp.usage else 0,
            "latency_ms": elapsed,
            "model": active_model,
        }

    if chunks:
        context_str = "\n\n---\n\n".join(
            f"[Passage {idx+1} | {c.get('id')} | Code: {c.get('kicd_code', '')} | Grade {c.get('grade')} {c.get('subject')} · Strand: {c.get('strand', '')} · Topic: {c.get('topic')}]\n{c.get('text')}"
            for idx, c in enumerate(chunks)
        )
    else:
        context_str = "[No specific curriculum passages found. Use encouraging general educational knowledge.]"

    user_msg = f"Curriculum Context:\n{context_str}\n\nPupil Question: {query}"

    resp, active_model = _call_llm_with_fallback(
        messages=[
            {"role": "system", "content": ANSWER_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
        max_tokens=600,
    )
    raw_content = resp.choices[0].message.content or getattr(resp.choices[0].message, "reasoning", "") or ""
    answer_text = raw_content.strip()
    elapsed = round((time.perf_counter() - t0) * 1000)

    usage = {
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
        "total_tokens": resp.usage.total_tokens if resp.usage else 0,
        "latency_ms": elapsed,
        "model": active_model,
    }
    return answer_text, usage


# ──────────────────────────────────────────────────────────────────────────────
# Stage 5: Grounding Validation (Real LLM Fact-Checking Auditor)
# ──────────────────────────────────────────────────────────────────────────────
VALIDATE_SYSTEM = """You are a strict curriculum fact-checking auditor for Kenya Class Tutor.
Compare the Answer against the provided Curriculum Passages.

Rules:
- If Curriculum Passages were provided: Reply YES ONLY IF the answer is factually grounded in the provided passages. If the answer contains outside claims, made-up information, sports, or contradicts the passages, reply NO.
- If No Curriculum Passages were provided: Reply YES if the answer is factually accurate, safe, and educational for school pupils. If false, harmful, or ungrounded, reply NO.
Reply with ONLY ONE WORD: YES or NO."""


def validate_grounding(answer_text: str, chunks: list[dict]) -> tuple[bool, dict[str, Any]]:
    t0 = time.perf_counter()

    if chunks:
        context_str = "\n\n".join(f"[{c.get('id')}] {c.get('text')}" for c in chunks)
        user_prompt = f"Passages:\n{context_str}\n\nAnswer to Check:\n{answer_text}"
    else:
        user_prompt = f"General Educational Answer to Check:\n{answer_text}"

    resp, active_model = _call_llm_with_fallback(
        messages=[
            {"role": "system", "content": VALIDATE_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_tokens=250,
    )
    raw_content = resp.choices[0].message.content or getattr(resp.choices[0].message, "reasoning", "") or ""
    raw = raw_content.strip().upper()
    verdict = "YES" if "YES" in raw else ("NO" if "NO" in raw else "YES")
    elapsed = round((time.perf_counter() - t0) * 1000)

    usage = {
        "verdict": verdict,
        "raw_response": raw_content.strip(),
        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
        "total_tokens": resp.usage.total_tokens if resp.usage else 0,
        "latency_ms": elapsed,
        "model": active_model,
        "cost_tier": "cheap-check",
    }
    return (verdict == "YES"), usage
