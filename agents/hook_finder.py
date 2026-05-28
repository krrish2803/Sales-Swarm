from __future__ import annotations

import json

from llm_utils import call_json_llm
from models import SwarmState, ensure_complete_state


async def hook_finder_agent(state: SwarmState) -> SwarmState:
    state = ensure_complete_state(state)
    print("[Agent 4: Hook Finder] Starting...")

    try:
        system_prompt = (
            "You are a world-class B2B sales personalization expert. Your job is "
            "to find the single best hook to open a cold outreach message with. "
            "A good hook is: specific, recent, relevant, and makes the prospect "
            "feel seen — not stalked. Always respond in valid JSON only."
        )
        info = state["company_info"]
        user_prompt = f"""
TARGET: {info.get("company_name", "")} – {info.get("what_they_do", "")[:150]}
NEWS: {info.get("recent_news", [])} | HIRING: {info.get("hiring_signals", [])}
CONTENT: {info.get("content_themes", [])} | CHALLENGES: {info.get("apparent_challenges", [])}
PRODUCTS: {info.get("key_products", [])}
PAIN POINTS: {state.get("pain_points", [])}
ANGLE: {state.get("best_angle", "")}

Find the single best personalization hook and return this exact JSON:
{{
  "hook": "<the opening line or reference>",
  "hook_source": "<where you found this: job posting / blog post / pricing page / product launch>",
  "hook_type": "<hiring_signal / content_signal / product_signal / growth_signal>",
  "why_this_works": "<one sentence>"
}}

Instructions:
- Prefer a date-specific, time-bound signal when available: recent job postings, a new launch, a funding announcement, or a fresh pricing change.
- If no obvious recent signal exists, fall back to a concrete job posting or a recent product update rather than generic company praise.
- Do not invent signals; only use what is plausible from the company info.
- Keep the hook precise and actionable, not vague.

Examples of great hooks:
- "Saw you're hiring 3 enterprise SDRs — looks like you're moving upmarket"
- "Read your blog post on reducing churn — resonated with what we're building"
- "Noticed you just launched a new pricing tier last week"
- "Saw you raised a Series A — congrats on the round"
"""
        parsed = await call_json_llm(system_prompt, user_prompt)

        state["hook"] = str(parsed.get("hook", "")).strip()
        state["hook_source"] = str(parsed.get("hook_source", "")).strip()
        state["hook_type"] = str(parsed.get("hook_type", "")).strip()
        state["why_hook_works"] = str(parsed.get("why_this_works", "")).strip()

        if not state["hook"]:
            company_name = state["company_info"].get("company_name") or "your company"
            state["hook"] = f"Noticed what {company_name} is building and thought this might be relevant."
            state["hook_source"] = "company website"
            state["hook_type"] = "company_signal"
            state["errors"].append("Hook Finder warning: missing hook from LLM, used fallback hook.")
    except Exception as exc:
        state["errors"].append(f"Hook Finder failed: {exc}")
        company_name = state["company_info"].get("company_name") or "your company"
        state["hook"] = f"Noticed what {company_name} is building and thought this might be relevant."
        state["hook_source"] = "company website"
        state["hook_type"] = "company_signal"
        state["why_hook_works"] = "It anchors the message in the target company's own context."

    print("[Agent 4: Hook Finder] Done ✓")
    return ensure_complete_state(state)

