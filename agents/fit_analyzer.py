from __future__ import annotations

import json

from llm_utils import bounded_fit_score, call_json_llm, list_of_strings
from models import SwarmState, ensure_complete_state


async def fit_analyzer_agent(state: SwarmState) -> SwarmState:
    state = ensure_complete_state(state)
    print("[Agent 2: Fit Analyzer] Starting...")

    try:
        system_prompt = (
            "You are a B2B sales strategist who evaluates lead quality for startups. "
            "Always respond in valid JSON only."
        )
        info = state["company_info"]
        user_prompt = f"""
PRODUCT: {state["founder_product"]}
ICP: {state["founder_icp"]}
TARGET: {info.get("company_name", "")} | {info.get("industry", "")} | {info.get("what_they_do", "")[:200]}
SIZE: {info.get("company_size", "")} | CUSTOMERS: {info.get("target_customers", "")[:200]}
PRODUCTS: {info.get("key_products", [])} | PRICE: {info.get("pricing_model", "")}
CHALLENGES: {info.get("apparent_challenges", [])} | NEWS: {info.get("recent_news", [])}
TECH: {info.get("tech_stack", [])} | HIRING: {info.get("hiring_signals", [])}

Analyze the fit and return this exact JSON:
{{
  "fit_score": <integer 1-10>,
  "fit_reasoning": "<2-3 sentences explaining the score>",
  "pain_points": [
    "<specific pain point 1>",
    "<specific pain point 2>",
    "<specific pain point 3>"
  ],
  "why_they_need_this": "<one line>",
  "potential_objections": [
    "<objection 1>",
    "<objection 2>"
  ],
  "best_angle": "<the strongest reason to reach out>"
}}

Scoring guide:
9-10: Perfect fit, reach out immediately
7-8: Strong fit, good use of time
5-6: Medium fit, proceed with caution
3-4: Weak fit, low priority
1-2: Poor fit, skip this lead

Instructions:
- Use the target company details and likely business context, not broad generic language.
 - Remember: founder_icp is who the founder sells TO, not the company being analyzed.
 - Score fit by checking whether the target company matches the founder's ICP description.
- If the fit is weak, explain clearly why and what would need to change for outreach to make sense.
- Keep the reasoning human and actionable.
"""
        parsed = await call_json_llm(system_prompt, user_prompt)

        state["fit_score"] = bounded_fit_score(parsed.get("fit_score"))
        state["fit_reasoning"] = str(parsed.get("fit_reasoning", "")).strip()
        state["pain_points"] = list_of_strings(parsed.get("pain_points"))[:3]
        state["why_they_need_this"] = str(parsed.get("why_they_need_this", "")).strip()
        state["potential_objections"] = list_of_strings(parsed.get("potential_objections"))[:3]
        state["best_angle"] = str(parsed.get("best_angle", "")).strip()

        if state["fit_score"] == 0:
            state["fit_score"] = 1
            state["errors"].append("Fit Analyzer warning: invalid or missing fit_score, defaulted to 1.")
    except Exception as exc:
        state["errors"].append(f"Fit Analyzer failed: {exc}")
        state["fit_score"] = 1
        state["fit_reasoning"] = "Unable to analyze fit because the scoring agent failed."
        state["pain_points"] = []
        state["best_angle"] = ""

    print("[Agent 2: Fit Analyzer] Done ✓")
    return ensure_complete_state(state)
