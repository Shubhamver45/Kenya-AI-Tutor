"""
Flask Web Application for Kenya Class Tutor Lite.
Exposes:
  - Web UI for Interactive Tutoring, Live Trace Panel, Cost Calculator, and Eval Suite
  - REST APIs for chat pipeline, retrieval inspection, capacity calculation, and eval runs
"""

from __future__ import annotations

import sys
from pathlib import Path
from flask import Flask, render_template, request, jsonify

# Add root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline import run_pipeline
from retrieval.hybrid_search import hybrid_search, compare_retrieval, load_corpus
from telemetry.collector import trace_store
from cost.calculator import calculate_capacity, get_three_scenarios
from evaluation.eval_suite import run_evaluation
from llm.client import configure_llm, get_llm_config

BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    question = data.get("question", "").strip()
    history = data.get("history", [])
    grade = data.get("grade")
    subject = data.get("subject")
    simulate_hallucination = data.get("simulate_hallucination", False)

    if not question:
        return jsonify({"error": "Question is required"}), 400

    if grade is not None and str(grade).isdigit():
        grade = int(grade)
    else:
        grade = None

    try:
        trace = run_pipeline(
            question=question,
            history=history,
            grade=grade,
            subject=subject,
            simulate_initial_hallucination=simulate_hallucination,
        )
        return jsonify({
            "answer": trace.answer,
            "trace": trace.to_dict(),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/traces/latest", methods=["GET"])
def api_latest_trace():
    trace = trace_store.get_latest()
    if not trace:
        return jsonify({"trace": None})
    return jsonify({"trace": trace.to_dict()})


@app.route("/api/traces/history", methods=["GET"])
def api_trace_history():
    return jsonify({"traces": trace_store.get_all()})


@app.route("/api/retrieval/compare", methods=["POST"])
def api_compare_retrieval():
    data = request.get_json() or {}
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400
    res = compare_retrieval(query, top_k=3)
    return jsonify(res)


@app.route("/api/curriculum", methods=["GET"])
def api_curriculum():
    corpus = load_corpus()
    return jsonify({"total": len(corpus), "items": corpus})


@app.route("/api/cost/calculate", methods=["POST"])
def api_cost_calculate():
    data = request.get_json() or {}
    gpu_tokens_per_sec = float(data.get("gpu_tokens_per_sec", 220))
    gpu_hourly_price = float(data.get("gpu_hourly_price", 0.90))
    utilization_rate = float(data.get("utilization_rate", 0.60))

    calc = calculate_capacity(
        gpu_tokens_per_sec=gpu_tokens_per_sec,
        gpu_hourly_price=gpu_hourly_price,
        utilization_rate=utilization_rate,
    )
    scenarios = get_three_scenarios()
    return jsonify({
        "custom": calc,
        "scenarios": scenarios,
    })


@app.route("/api/evaluation/run", methods=["POST"])
def api_run_eval():
    results = run_evaluation()
    return jsonify(results)


@app.route("/api/config", methods=["GET", "POST"])
def api_config():
    if request.method == "POST":
        data = request.get_json() or {}
        configure_llm(
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            model=data.get("model"),
        )
    cfg = get_llm_config()
    # Mask API key for security
    masked_key = ""
    if cfg["api_key"]:
        masked_key = cfg["api_key"][:4] + "..." + cfg["api_key"][-4:] if len(cfg["api_key"]) > 8 else "***"
    return jsonify({
        "has_api_key": bool(cfg["api_key"]),
        "masked_key": masked_key,
        "base_url": cfg["base_url"],
        "model": cfg["model"],
    })


if __name__ == "__main__":
    print("[Kenya Class Tutor Lite] Starting server on http://localhost:5050 ...")
    app.run(host="0.0.0.0", port=5050, debug=True)
