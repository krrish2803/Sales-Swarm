from __future__ import annotations

import os

import httpx

from llm_utils import call_json_llm
from models import SwarmState, ensure_complete_state

JINA_API_KEY = os.getenv("JINA_API_KEY", "").strip()
JINA_HEADERS = {
    "Authorization": f"Bearer {JINA_API_KEY}",
    "Accept": "text/plain",
    "X-Return-Format": "markdown",
}
JINA_SEARCH_BASE = "https://r.jina.ai/https://html.duckduckgo.com/html/?q="


async def _jina_search(query: str, timeout: float = 12.0) -> str:
    encoded = query.replace(" ", "+")
    url = f"{JINA_SEARCH_BASE}{encoded}"
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=JINA_HEADERS)
            response.raise_for_status()
            return response.text
    except Exception as exc:
        print(f"[ContactFinder] Search failed for '{query}': {exc}")
        return ""


async def _jina_read(url: str, timeout: float = 15.0) -> str:
    """Read a direct URL via Jina AI Reader."""
    read_url = f"https://r.jina.ai/{url}"
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(read_url, headers=JINA_HEADERS)
            response.raise_for_status()
            return response.text
    except Exception as exc:
        print(f"[ContactFinder] Read failed for '{url}': {exc}")
        return ""


async def contact_finder_agent(state: SwarmState) -> SwarmState:
    state = ensure_complete_state(state)
    print("[Agent: Contact Finder] Starting...")

    company_name = state.get("company_info", {}).get("company_name", "").strip()
    if not company_name:
        company_name = state.get("target_url", "").strip()

    try:
        import asyncio
        import re

        # ── Try direct LinkedIn company page (most reliable) ──
        def _slugify(name: str) -> str:
            slug = name.lower().strip()
            slug = re.sub(r"[^a-z0-9\s-]", "", slug)
            slug = re.sub(r"\s+", "-", slug)
            return slug.strip("-")

        company_slug = _slugify(company_name.split(".")[0].split("//")[-1])
        company_lnkd_url = f"https://www.linkedin.com/company/{company_slug}"

        company_page = await _jina_read(company_lnkd_url)
        company_linkedin_found = ""
        if company_page and "linkedin.com/company" in company_page[:500]:
            print(f"[ContactFinder] Found company LinkedIn page directly: {company_lnkd_url}")
            company_linkedin_found = company_lnkd_url

        # ── Single web search via DuckDuckGo (no rate limits) ──
        query = f"{company_name} CEO founder LinkedIn"
        search_result = await _jina_search(query)

        combined_parts = []
        if company_page:
            combined_parts.append(f"--- COMPANY LINKEDIN PAGE ---\n{company_page[:3000]}")
        if search_result:
            combined_parts.append(f"--- SEARCH RESULTS ---\n{search_result[:3000]}")
        combined = "\n\n".join(combined_parts) or ""

        # ── First LLM pass: extract company LinkedIn + person from search results ──
        contact_info = await call_json_llm(
            "You extract contact information for B2B outreach from search results. Return valid JSON only.",
            f"""
From these search results, extract contact details for reaching out to {company_name}.

SEARCH RESULTS:
{combined[:5000]}

COMPANY: {company_name}
INDUSTRY: {state.get("company_info", {}).get("industry", "")}

Return ONLY this exact JSON, no other text:
{{
  "company_linkedin": "https://linkedin.com/company/... or empty string if not found",
  "person_name": "full name of a relevant person (CEO/Founder/HR/Owner) or empty",
  "person_role": "their role (CEO / Founder / HR Head / Owner) or empty",
  "person_linkedin": "https://linkedin.com/in/... or empty",
  "person_email": "email address or empty",
  "person_whatsapp": "phone number with country code or empty"
}}

Rules:
- Only real LinkedIn profiles, never guess or invent
- Prefer CEO/Founder/HR roles
- person_email should be a real email format (e.g., name@company.com) or empty
- person_whatsapp should be a phone number with country code (e.g., +91...) or empty
- Set fields to empty string "" if you cannot find them
""",
        )

        if not isinstance(contact_info, dict):
            contact_info = {}

        raw_company_linkedin = str(contact_info.get("company_linkedin", "")).strip()
        raw_person_linkedin = str(contact_info.get("person_linkedin", "")).strip()
        raw_person_name = str(contact_info.get("person_name", "")).strip()
        raw_person_role = str(contact_info.get("person_role", "")).strip()
        raw_email = str(contact_info.get("person_email", "")).strip()
        raw_whatsapp = str(contact_info.get("person_whatsapp", "")).strip()

        # ── Second pass: if we have company LinkedIn but no person, scrape it ──
        if raw_company_linkedin and "linkedin.com/company" in raw_company_linkedin and not raw_person_name:
            print(f"[ContactFinder] Scraping company LinkedIn page for employees...")
            scraped = await _jina_read(raw_company_linkedin)
            if scraped:
                person_fill = await call_json_llm(
                    "You extract a key person's LinkedIn profile from a company LinkedIn page. Return valid JSON only.",
                    f"""
From this company LinkedIn page, find ONE relevant person (CEO/Founder/HR Head) at {company_name}.

COMPANY PAGE:
{scraped[:4000]}

Return ONLY this exact JSON, no other text:
{{
  "person_name": "full name or empty",
  "person_role": "their role (CEO/Founder/HR Head) or empty",
  "person_linkedin": "https://linkedin.com/in/... or empty",
  "person_email": "email address or empty",
  "person_whatsapp": "phone number with country code or empty"
}}
""",
                )
                if isinstance(person_fill, dict):
                    raw_person_name = raw_person_name or str(person_fill.get("person_name", "")).strip()
                    raw_person_role = raw_person_role or str(person_fill.get("person_role", "")).strip()
                    raw_person_linkedin = raw_person_linkedin or str(person_fill.get("person_linkedin", "")).strip()
                    raw_email = raw_email or str(person_fill.get("person_email", "")).strip()
                    raw_whatsapp = raw_whatsapp or str(person_fill.get("person_whatsapp", "")).strip()

        # ── Third pass: if we now have a person LinkedIn URL, scrape it too ──
        if raw_person_linkedin and "linkedin.com/in" in raw_person_linkedin:
            print(f"[ContactFinder] Scraping person LinkedIn profile for contact details...")
            scraped_person = await _jina_read(raw_person_linkedin)
            if scraped_person:
                person_details = await call_json_llm(
                    "You extract email and phone from a LinkedIn profile page. Return valid JSON only.",
                    f"""
From this LinkedIn profile page, extract contact info.

PROFILE PAGE:
{scraped_person[:3000]}

Return ONLY this exact JSON, no other text:
{{
  "person_email": "email address or empty",
  "person_whatsapp": "phone number with country code or empty"
}}

Look for email in the About section and phone/WhatsApp in the Contact Info section.
""",
                )
                if isinstance(person_details, dict):
                    raw_email = raw_email or str(person_details.get("person_email", "")).strip()
                    raw_whatsapp = raw_whatsapp or str(person_details.get("person_whatsapp", "")).strip()

        def _clean_linkedin(url: str) -> str:
            url = url.strip().rstrip("/")
            if not url or "linkedin.com" not in url.lower():
                return ""
            if not url.startswith("http"):
                url = "https://" + url
            return url

        # Use directly-read company LinkedIn as fallback if LLM didn't extract it
        final_company_linkedin = _clean_linkedin(raw_company_linkedin) or company_linkedin_found

        state["contact_company_linkedin"] = final_company_linkedin
        state["contact_person_name"] = raw_person_name
        state["contact_role"] = raw_person_role
        state["contact_linkedin"] = _clean_linkedin(raw_person_linkedin)
        state["contact_email"] = raw_email if "@" in raw_email else ""
        state["contact_whatsapp"] = raw_whatsapp if any(c.isdigit() for c in raw_whatsapp) else ""

        print(f"[ContactFinder] Found: {state['contact_person_name'] or 'no person'} | "
              f"Person LinkedIn: {'yes' if state['contact_linkedin'] else 'no'} | "
              f"Company LinkedIn: {'yes' if state['contact_company_linkedin'] else 'no'} | "
              f"Email: {'yes' if state['contact_email'] else 'no'} | "
              f"WhatsApp: {'yes' if state['contact_whatsapp'] else 'no'}")

    except Exception as exc:
        print(f"[ContactFinder] Error: {exc}")
        state["errors"].append(f"Contact Finder failed: {exc}")

    print("[Agent: Contact Finder] Done ✓")
    return ensure_complete_state(state)
