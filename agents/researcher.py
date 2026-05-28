from __future__ import annotations

import asyncio
from urllib.parse import urljoin

from llm_utils import call_json_llm, list_of_strings
from models import DEFAULT_COMPANY_INFO, SwarmState, ensure_complete_state
from tools.scraper import scrape_url


def _clip_content(label: str, content: str, limit: int = 3000) -> str:
    if not content:
        return f"\n\n## {label}\nNo content found."
    return f"\n\n## {label}\n{content[:limit]}"


async def researcher_agent(state: SwarmState) -> SwarmState:
    state = ensure_complete_state(state)
    print("[Agent 1: Researcher] Starting...")

    try:
        target_url = state["target_url"]
        base_url = target_url.rstrip("/")

        homepage, about, pricing = await asyncio.gather(
            scrape_url(base_url),
            scrape_url(urljoin(f"{base_url}/", "about")),
            scrape_url(urljoin(f"{base_url}/", "pricing")),
        )

        combined_scraped_content = "\n".join(
            [
                _clip_content("Homepage", homepage),
                _clip_content("About", about),
                _clip_content("Pricing", pricing),
            ]
        )

        system_prompt = (
            "You are a B2B sales researcher. Extract structured information "
            "about a company from their website content. Always respond in valid JSON only."
        )
        user_prompt = f"""
Website content:
{combined_scraped_content}

Extract and return this exact JSON:
{{
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
  "apparent_challenges": []
}}
"""
        parsed = await call_json_llm(system_prompt, user_prompt)
        company_info = {
            **DEFAULT_COMPANY_INFO,
            **{key: parsed.get(key, default) for key, default in DEFAULT_COMPANY_INFO.items()},
        }
        for list_key in (
            "key_products",
            "recent_news",
            "tech_stack",
            "hiring_signals",
            "content_themes",
            "apparent_challenges",
        ):
            company_info[list_key] = list_of_strings(company_info.get(list_key))

        state["company_info"] = company_info
        if not any([homepage, about, pricing]):
            state["errors"].append("Researcher warning: no scrapeable content found for target URL.")
    except Exception as exc:
        state["errors"].append(f"Researcher failed: {exc}")
        state["company_info"] = DEFAULT_COMPANY_INFO.copy()

    print("[Agent 1: Researcher] Done ✓")
    return ensure_complete_state(state)

