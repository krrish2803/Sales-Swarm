from __future__ import annotations

import re

from models import SwarmState, ensure_complete_state


def _size_mismatch(company_size: str, icp: str) -> tuple[bool, str]:
    if not company_size:
        return False, ""

    size_text = company_size.lower()

    employee_match = re.search(r"(\d[\d,]*)\s*\+?\s*(employees?|people)", size_text)
    if employee_match:
        count = int(employee_match.group(1).replace(",", ""))
        if count > 1000:
            return True, f"The company has {count} employees, far beyond typical ICP range."
        if "50-500" in icp and count > 800:
            return True, f"The company has {count} employees, which is well above the 50-500 ICP range."

    if re.search(r"(over\s*1[,.]?\s*k|1[,.]?\s*400\+)", size_text):
        return True, "This company is far too large for the ICP range."

    return False, ""


async def qualifier_agent(state: SwarmState) -> SwarmState:
    state = ensure_complete_state(state)
    print("[Agent 3: Qualifier] Starting...")

    try:
        fit_score = int(state.get("fit_score", 0) or 0)
        info = state.get("company_info") or {}
        has_real_data = bool(info.get("company_name") and info.get("industry"))

        size_penalty, size_reason = _size_mismatch(
            info.get("company_size", ""), state.get("founder_icp", "")
        )
        if size_penalty and fit_score >= 5:
            fit_score = min(fit_score, 3)
            state["fit_score"] = fit_score
            print(f"[Agent 3] Size mismatch detected, forcing fit_score to {fit_score}")

        if not has_real_data:
            state["qualified"] = False
            state["fit_score"] = 0
            state["next_action"] = "skip_lead"
            state["qualification_reason"] = "Could not research this company."
            state["quality_gate_reason"] = (
                "SalesSwarm could not find any verifiable company data at the "
                "provided URL. The site may not exist, may block scrapers, or "
                "the URL may be incorrect."
            )
            state["better_targets"] = []
        elif fit_score >= 7:
            state["qualified"] = True
            state["next_action"] = "proceed_to_outreach"
            state["qualification_reason"] = "Strong fit. Worth reaching out."
            state["quality_gate_reason"] = ""
            state["better_targets"] = []
        elif fit_score >= 5:
            state["qualified"] = True
            state["next_action"] = "proceed_with_caution"
            state["qualification_reason"] = "Medium fit. Personalize heavily."
            state["quality_gate_reason"] = ""
            state["better_targets"] = []
        else:
            state["qualified"] = False
            state["next_action"] = "skip_lead"
            if size_penalty:
                state["qualification_reason"] = f"Weak fit. {size_reason}"
            else:
                state["qualification_reason"] = "Weak fit. Not worth your time."
            tech_stack = [item.lower() for item in state.get("company_info", {}).get("tech_stack", []) if isinstance(item, str)]
            known_competitors = ["freshworks", "zoho", "clevertap", "hubspot", "zendesk", "intercom", "salesforce"]
            matched = [comp for comp in known_competitors if any(comp in tech for tech in tech_stack)]
            if size_penalty:
                state["quality_gate_reason"] = size_reason
            elif matched:
                state["quality_gate_reason"] = (
                    f"Their tech stack shows they already use {matched[0].title()} or a similar competitor. "
                    "Reaching out now will likely get ignored."
                )
            else:
                state["quality_gate_reason"] = (
                    "Their profile and current situation suggest a weak fit for your product. "
                    "Reaching out now will likely get ignored."
                )
            state["better_targets"] = []
    except Exception as exc:
        state["errors"].append(f"Qualifier failed: {exc}")
        state["qualified"] = False
        state["next_action"] = "skip_lead"
        state["qualification_reason"] = "Qualification failed. Skipping lead to avoid wasting time."
        state["quality_gate_reason"] = "Could not validate lead quality. It is safer to skip this lead."
        state["better_targets"] = []

    print("[Agent 3: Qualifier] Done ✓")
    return ensure_complete_state(state)

