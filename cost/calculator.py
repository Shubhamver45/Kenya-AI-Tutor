"""
Stage 7: Capacity Planning & Cost Calculator (Section 11).

Workload parameters from the Kenya Class Tutor architecture document:
  - Total registered learners: 38,400
  - Daily active rate: 25% (9,600 active pupils/day)
  - Questions per learner: 3 questions/day (28,800 questions/day)
  - Tokens per question turn: 900 tokens (curriculum context + conversation + answer)
  - Total tokens/day: 9,600 * 3 * 900 = 25,920,000 tokens/day (~777.6 Million tokens/month)

Takes 3 key variables:
  1. GPU throughput (tokens/second, e.g., 120-500 tok/s with vLLM continuous batching)
  2. GPU hourly price ($/hour, e.g., $0.85 for L4, $2.20 for A100, or edge instance)
  3. Average utilization factor (accounting for 8am-4pm school hours peak vs nighttime idle)

Outputs:
  - Total monthly GPU cost ($)
  - Cost per question ($)
  - Cost per learner per month ($)
  - Scenario comparison: Low (conservative), Base (realistic), High (optimized)
"""

from __future__ import annotations

import math
from typing import Any

# Default Architectural Assumptions from Section 11
TOTAL_LEARNERS = 38_400
ACTIVE_PERCENT = 0.25
DAILY_QUESTIONS_PER_LEARNER = 3
TOKENS_PER_QUESTION = 900
DAYS_PER_MONTH = 30
HOURS_PER_MONTH = 24 * DAYS_PER_MONTH  # 720 hours


def calculate_capacity(
    gpu_tokens_per_sec: float = 200.0,
    gpu_hourly_price: float = 1.00,
    utilization_rate: float = 0.60,
    school_hours_peak_factor: float = 2.5,
) -> dict[str, Any]:
    """
    Computes capacity planning metrics.
    school_hours_peak_factor: traffic during school hours (8am - 4pm) is higher than 24h average.
    """
    active_learners_daily = TOTAL_LEARNERS * ACTIVE_PERCENT
    daily_questions = active_learners_daily * DAILY_QUESTIONS_PER_LEARNER
    monthly_questions = daily_questions * DAYS_PER_MONTH
    
    daily_tokens = daily_questions * TOKENS_PER_QUESTION
    monthly_tokens = daily_tokens * DAYS_PER_MONTH

    # Effective throughput per GPU per second considering utilization
    effective_tok_per_sec = gpu_tokens_per_sec * max(utilization_rate, 0.05)
    
    # Peak tokens per second during school hours (e.g. 8-hour window with peak concurrency)
    # Average 8-hour rate = (daily_tokens / (8 * 3600)) * peak_factor
    peak_tok_per_sec = (daily_tokens / (8 * 3600)) * (school_hours_peak_factor / 2.0)

    # Number of GPUs needed to sustain peak school hours without queue buildup
    gpus_needed_peak = max(1, math.ceil(peak_tok_per_sec / gpu_tokens_per_sec))
    
    # Monthly cost with baseline reserved/autoscaled fleet
    # Average GPUs needed across 24h:
    avg_tokens_per_sec_24h = daily_tokens / (24 * 3600)
    gpus_needed_avg = max(1, math.ceil(avg_tokens_per_sec_24h / effective_tok_per_sec))
    
    # Fleet model: Base reserved fleet (avg) + Peak bursting instances during school hours
    # 8 peak hours/day with peak GPUs, 16 off-peak hours with 1 standby GPU
    monthly_gpu_hours = (8 * gpus_needed_peak + 16 * 1) * DAYS_PER_MONTH
    monthly_cost = monthly_gpu_hours * gpu_hourly_price

    cost_per_question = monthly_cost / monthly_questions
    cost_per_learner = monthly_cost / TOTAL_LEARNERS
    cost_per_active_learner = monthly_cost / active_learners_daily

    return {
        "inputs": {
            "gpu_tokens_per_sec": gpu_tokens_per_sec,
            "gpu_hourly_price": gpu_hourly_price,
            "utilization_rate": utilization_rate,
        },
        "traffic": {
            "total_learners": TOTAL_LEARNERS,
            "active_learners_daily": int(active_learners_daily),
            "daily_questions": int(daily_questions),
            "monthly_questions": int(monthly_questions),
            "daily_tokens": int(daily_tokens),
            "monthly_tokens": int(monthly_tokens),
            "peak_tokens_per_sec": round(peak_tok_per_sec, 1),
        },
        "hardware": {
            "gpus_needed_peak": gpus_needed_peak,
            "gpus_needed_avg": gpus_needed_avg,
            "monthly_gpu_hours": monthly_gpu_hours,
        },
        "financials": {
            "monthly_cost_usd": round(monthly_cost, 2),
            "cost_per_question_usd": round(cost_per_question, 5),
            "cost_per_learner_monthly_usd": round(cost_per_learner, 4),
            "cost_per_active_learner_monthly_usd": round(cost_per_active_learner, 4),
            "cost_per_1m_tokens_usd": round((monthly_cost / (monthly_tokens / 1_000_000)), 3),
        }
    }


def get_three_scenarios() -> dict[str, Any]:
    """
    Computes Low, Base, and High efficiency scenarios as recommended by section 11.
      - Low (Conservative / Unoptimized): 120 tok/s, $1.50/hr, 35% utilization
      - Base (Realistic vLLM / L4 cloud): 220 tok/s, $0.90/hr, 60% utilization
      - High (Optimized Edge / Batching): 450 tok/s, $0.65/hr (spot/edge), 80% utilization
    """
    low = calculate_capacity(gpu_tokens_per_sec=120, gpu_hourly_price=1.50, utilization_rate=0.35)
    base = calculate_capacity(gpu_tokens_per_sec=220, gpu_hourly_price=0.90, utilization_rate=0.60)
    high = calculate_capacity(gpu_tokens_per_sec=450, gpu_hourly_price=0.65, utilization_rate=0.80)

    return {
        "low_scenario": {
            "name": "Conservative (Unbatched/On-Demand)",
            "gpu": "120 tok/s @ $1.50/hr (35% util)",
            **low["financials"],
            "gpus_peak": low["hardware"]["gpus_needed_peak"],
        },
        "base_scenario": {
            "name": "Base (vLLM Continuous Batching on L4)",
            "gpu": "220 tok/s @ $0.90/hr (60% util)",
            **base["financials"],
            "gpus_peak": base["hardware"]["gpus_needed_peak"],
        },
        "high_scenario": {
            "name": "Optimized (Edge Caching + Quantized 4-bit)",
            "gpu": "450 tok/s @ $0.65/hr (80% util)",
            **high["financials"],
            "gpus_peak": high["hardware"]["gpus_needed_peak"],
        },
    }


if __name__ == "__main__":
    print("\n" + "="*70)
    print("STAGE 7: CAPACITY PLANNING & COST CALCULATOR (Section 11)")
    print("="*70)
    scenarios = get_three_scenarios()
    for key, sc in scenarios.items():
        print(f"\n--- {sc['name']} ---")
        print(f"  Configuration : {sc['gpu']}")
        print(f"  Monthly Cost  : ${sc['monthly_cost_usd']:,.2f}")
        print(f"  Cost / Question: ${sc['cost_per_question_usd']:.5f}")
        print(f"  Cost / Learner : ${sc['cost_per_learner_monthly_usd']:.4f} / month")
        print(f"  Peak GPUs     : {sc['gpus_peak']}")
