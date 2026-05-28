from __future__ import annotations

from typing import Any, TypedDict

from pydantic import BaseModel, Field, HttpUrl


class ColdEmail(TypedDict, total=False):
    subject: str
    body: str


class FollowUpEmail(TypedDict, total=False):
    subject: str
    body: str


class SwarmState(TypedDict, total=False):
    # Input
    founder_product: str
    founder_icp: str
    target_url: str

    # Agent 1 output
    company_info: dict[str, Any]

    # Agent 2 output
    fit_score: int
    fit_reasoning: str
    pain_points: list[str]
    why_they_need_this: str
    potential_objections: list[str]
    best_angle: str

    # Agent 3 output
    hook: str
    hook_source: str
    hook_type: str
    why_hook_works: str

    # Agent 4 output
    cold_email: ColdEmail
    whatsapp_message: str
    follow_up_email: FollowUpEmail
    linkedin_dm: str

    # Agent 5 output
    qualified: bool
    qualification_reason: str
    quality_gate_reason: str
    better_targets: list[dict[str, Any]]
    next_action: str

    # Agent 6 — Contact Finder
    contact_company_linkedin: str
    contact_person_name: str
    contact_role: str
    contact_linkedin: str
    contact_email: str
    contact_whatsapp: str

    # Meta
    errors: list[str]
    processing_time: float


class SwarmRequest(BaseModel):
    founder_product: str = Field(..., min_length=3)
    founder_icp: str = Field(..., min_length=3)
    target_url: HttpUrl


class SwarmResponse(BaseModel):
    founder_product: str
    founder_icp: str
    target_url: str
    company_info: dict[str, Any]
    fit_score: int
    fit_reasoning: str
    pain_points: list[str]
    hook: str
    hook_source: str
    cold_email: dict[str, str]
    whatsapp_message: str
    follow_up_email: dict[str, str]
    linkedin_dm: str
    qualified: bool
    qualification_reason: str
    quality_gate_reason: str
    better_targets: list[dict[str, str]]
    next_action: str
    contact_company_linkedin: str
    contact_person_name: str
    contact_role: str
    contact_linkedin: str
    contact_email: str
    contact_whatsapp: str
    errors: list[str]
    processing_time: float


DEFAULT_COMPANY_INFO: dict[str, Any] = {
    "company_name": "",
    "industry": "",
    "what_they_do": "",
    "company_size": "",
    "target_customers": "",
    "key_products": [],
    "pricing_model": "",
    "recent_news": [],
    "tech_stack": [],
    "hiring_signals": [],
    "content_themes": [],
    "apparent_challenges": [],
}


DEFAULT_COLD_EMAIL: ColdEmail = {
    "subject": "",
    "body": "",
}


def create_initial_state(
    founder_product: str,
    founder_icp: str,
    target_url: str,
) -> SwarmState:
    return {
        "founder_product": founder_product,
        "founder_icp": founder_icp,
        "target_url": target_url,
        "company_info": DEFAULT_COMPANY_INFO.copy(),
        "fit_score": 0,
        "fit_reasoning": "",
        "pain_points": [],
        "why_they_need_this": "",
        "potential_objections": [],
        "best_angle": "",
        "hook": "",
        "hook_source": "",
        "hook_type": "",
        "why_hook_works": "",
        "cold_email": DEFAULT_COLD_EMAIL.copy(),
        "whatsapp_message": "",
        "follow_up_email": {"subject": "", "body": ""},
        "linkedin_dm": "",
        "quality_gate_reason": "",
        "better_targets": [],
        "qualified": False,
        "qualification_reason": "",
        "next_action": "",
        "contact_company_linkedin": "",
        "contact_person_name": "",
        "contact_role": "",
        "contact_linkedin": "",
        "contact_email": "",
        "contact_whatsapp": "",
        "errors": [],
        "processing_time": 0.0,
    }


def ensure_complete_state(state: SwarmState) -> SwarmState:
    complete = create_initial_state(
        state.get("founder_product", ""),
        state.get("founder_icp", ""),
        state.get("target_url", ""),
    )
    complete.update(state)
    complete["company_info"] = {
        **DEFAULT_COMPANY_INFO,
        **(complete.get("company_info") or {}),
    }
    complete["cold_email"] = {
        **DEFAULT_COLD_EMAIL,
        **(complete.get("cold_email") or {}),
    }
    complete["follow_up_email"] = {
        "subject": "",
        "body": "",
        **(complete.get("follow_up_email") or {}),
    }
    complete["errors"] = list(complete.get("errors") or [])
    complete["pain_points"] = list(complete.get("pain_points") or [])
    complete["potential_objections"] = list(complete.get("potential_objections") or [])
    complete["better_targets"] = [
        t if isinstance(t, dict) else {"company_name": t, "website": t, "industry": "", "why_better_fit": ""}
        for t in (complete.get("better_targets") or [])
    ]
    for contact_field in (
        "contact_company_linkedin", "contact_person_name", "contact_role",
        "contact_linkedin", "contact_email", "contact_whatsapp",
    ):
        if not isinstance(complete.get(contact_field), str):
            complete[contact_field] = ""
    return complete

