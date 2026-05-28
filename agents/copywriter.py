from __future__ import annotations

import json

from llm_utils import call_json_llm
from models import DEFAULT_COLD_EMAIL, SwarmState, ensure_complete_state


def _fallback_email(state: SwarmState) -> dict[str, str]:
    company_name = state["company_info"].get("company_name") or "your team"
    hook = state.get("hook") or f"Noticed what {company_name} is building."
    best_angle = state.get("best_angle") or "there may be a clear fit with what we are building"
    return {
        "subject": "Quick idea for your team",
        "body": (
            f"{hook}\n\n"
            f"{best_angle}.\n\n"
            f"We help {state.get('founder_icp', 'teams like yours')} with "
            f"{state.get('founder_product', 'a focused workflow improvement')}.\n\n"
            "Worth a quick 15-minute chat this week?"
        ),
    }


def _fallback_follow_up_email(state: SwarmState) -> dict[str, str]:
    original_subject = state["cold_email"].get("subject", "Quick idea for your team")
    return {
        "subject": f"Re: {original_subject}",
        "body": (
            "Just wanted to follow up on this — "
            "happy to share a quick example if you want."
        ),
    }


async def copywriter_agent(state: SwarmState) -> SwarmState:
    state = ensure_complete_state(state)
    print("[Agent 5: Copywriter] Starting...")

    try:
        company_name = state["company_info"].get("company_name", "")
        system_prompt = (
            "You are an elite B2B copywriter who specializes in cold outreach "
            "for early-stage startups. You write messages that sound human, "
            "not like AI. Short, punchy, specific. Never generic. Never salesy. "
            "Always respond in valid JSON only."
        )
        info = state["company_info"]
        user_prompt = f"""
PRODUCT: {state["founder_product"]}
ICP: {state["founder_icp"]}
TARGET: {company_name} – {info.get("industry", "")}
PAIN: {state.get("pain_points", [])}
ANGLE: {state.get("best_angle", "")}
HOOK: {state["hook"]} ({state.get("hook_source", "")})
FIT: {state.get("fit_reasoning", "")[:200]}

Write outreach in these formats and return this exact JSON:
{{
    "cold_email": {{
        "subject": "<compelling subject line, max 8 words>",
        "body": "<email body, max 75 words total, start with the specific hook only, then explain why this matters and close with a soft founder-style ask>"
    }},
    "whatsapp_message": "<WhatsApp message, casual and concise, max 55 words, use the hook, end with a question>",
    "follow_up_email": {{
        "subject": "<format: Re: [original subject]>",
        "body": "<short follow-up, 2 lines max, soft bump, no pressure>"
    }},
    "linkedin_dm": "<professional but warm, max 75 words, mention something specific about their work, soft ask>"
}}

Rules:
 - Write like a founder sending a message to another founder/owner.
 - Use the company name or a specific signal from the hook in the first sentence.
 - Reference one clear research insight from the target company in at least one message.
 - Be warm, concise, and grounded in the target company's context.
 - Avoid generic phrases like 'hope this finds you well', 'synergy', or 'quick question'.
 - Make each message feel clearly written for this company only.
 - Never compliment the company generically.
 - Never say "impressive" or "bold".
 - Start the cold email body with the specific hook only.
 - Keep the cold email under 75 words total.
 - Sound like a busy founder wrote this in 5 minutes, not a sales team.
"""
        parsed = await call_json_llm(system_prompt, user_prompt)
        cold_email = parsed.get("cold_email") if isinstance(parsed.get("cold_email"), dict) else {}

        state["cold_email"] = {
            "subject": str(cold_email.get("subject", "")).strip(),
            "body": str(cold_email.get("body", "")).strip(),
        }
        state["whatsapp_message"] = str(parsed.get("whatsapp_message", "")).strip()
        state["follow_up_email"] = {
            "subject": str(parsed.get("follow_up_email", {}).get("subject", "")).strip(),
            "body": str(parsed.get("follow_up_email", {}).get("body", "")).strip(),
        }
        state["linkedin_dm"] = str(parsed.get("linkedin_dm", "")).strip()

        if not state["cold_email"]["subject"] or not state["cold_email"]["body"]:
            state["cold_email"] = _fallback_email(state)
            state["errors"].append("Copywriter warning: missing cold email from LLM, used fallback email.")
        if not state["whatsapp_message"]:
            state["whatsapp_message"] = (
                f"{state['hook']} We help {state['founder_icp']} with "
                f"{state['founder_product']}. Worth a quick chat?"
            )
            state["errors"].append("Copywriter warning: missing WhatsApp message, used fallback message.")
        if not state["follow_up_email"].get("body"):
            state["follow_up_email"] = _fallback_follow_up_email(state)
            state["errors"].append("Copywriter warning: missing follow-up email, used fallback message.")
        if not state["linkedin_dm"]:
            state["linkedin_dm"] = (
                f"{state['hook']} Thought there may be a fit because "
                f"{state.get('best_angle', 'your team is working on a relevant problem')}. "
                "Open to a quick 15-minute chat?"
            )
            state["errors"].append("Copywriter warning: missing LinkedIn DM, used fallback DM.")
    except Exception as exc:
        state["errors"].append(f"Copywriter failed: {exc}")
        state["cold_email"] = _fallback_email(state)
        state["whatsapp_message"] = (
            f"{state['hook']} We help {state['founder_icp']} with "
            f"{state['founder_product']}. Worth a quick chat?"
        )
        state["follow_up_email"] = _fallback_follow_up_email(state)
        state["linkedin_dm"] = (
            f"{state['hook']} Thought this could be relevant to your team. "
            "Open to a quick 15-minute chat?"
        )

    state["cold_email"] = {**DEFAULT_COLD_EMAIL, **state.get("cold_email", {})}
    print("[Agent 5: Copywriter] Done ✓")
    return ensure_complete_state(state)
