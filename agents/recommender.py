from __future__ import annotations

import json
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
JINA_SEARCH_BASE = "https://r.jina.ai/https://www.google.com/search?q="


async def _jina_search(query: str, timeout: float = 12.0) -> str:
    encoded = query.replace(" ", "+")
    url = f"{JINA_SEARCH_BASE}{encoded}"
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=JINA_HEADERS)
            response.raise_for_status()
            return response.text
    except Exception as exc:
        print(f"[Agent 6] Jina search failed for '{query}': {exc}")
        return ""


async def recommender_agent(state: SwarmState) -> SwarmState:
    state = ensure_complete_state(state)
    print("[Agent 6: Target Recommender] Starting...")

    try:
        search_query = await call_json_llm(
            "You generate precise Google search queries to find ideal B2B buyer companies.",
            f"""
Based on this founder's product and ICP, generate ONE Google search query to find
companies that would be perfect customers.

Founder product: {state['founder_product']}
Founder ICP: {state['founder_icp']}
Failed target industry: {state['company_info'].get('industry', '')}
Failed target reason: {state['qualification_reason']}

Rules:
- Query must find REAL companies, not articles
- Be specific to the ICP's industry and region
- Include India if ICP mentions Indian market
- Max 8 words
- Return ONLY the search query as a JSON string, nothing else: {{"query": "..."}}

Examples:
{{"query": "diagnostic centres management software India 2024"}}
{{"query": "D2C ecommerce brands India Series A funded"}}
{{"query": "B2B SaaS HR tools Mumbai Bangalore"}}
""",
        )
        search_query = search_query.get("query", "").strip()
        if not search_query:
            search_query = f"{state['founder_icp']} companies"
        print(f"[Agent 6] Search query: {search_query}")

        search_results = await _jina_search(search_query)

        second_query = search_query.replace("2024", "companies").replace("India", "Indian startups")
        if second_query == search_query:
            second_query = f"{search_query} companies"

        second_results = await _jina_search(second_query)
        combined_results = search_results + "\n\n" + second_results

        better_targets = await call_json_llm(
            "You extract real B2B company recommendations from search results. Return valid JSON only.",
            f"""
From these Google search results, extract 3 to 4 REAL companies that would be ideal
customers for this founder's product.

FOUNDER PRODUCT: {state['founder_product']}
FOUNDER ICP: {state['founder_icp']}

SEARCH RESULTS:
{combined_results[:2500]}

Rules:
- Only real companies with actual websites
- Must match the founder's ICP closely
- Prefer companies with 50-500 employees
- No Fortune 500 companies
- No news sites, blogs, or directories
- Each company must be a plausible buyer of the founder's product
- If results mention Indian companies, prefer those for Indian ICP

Return ONLY this exact JSON, no other text:
{{
  "better_targets": [
    {{
      "company_name": "exact company name",
      "website": "https://exactwebsite.com",
      "industry": "their industry in 3 words",
      "why_better_fit": "one specific sentence explaining why they need this product"
    }}
    // 3-4 items total
  ]
}}
""",
        )

        targets = better_targets.get("better_targets", []) if isinstance(better_targets, dict) else []
        if not isinstance(targets, list):
            targets = []

        validated = []
        for t in targets:
            if isinstance(t, dict) and t.get("company_name") and t.get("website"):
                validated.append({
                    "company_name": str(t.get("company_name", "")).strip(),
                    "website": str(t.get("website", "")).strip(),
                    "industry": str(t.get("industry", "")).strip(),
                    "why_better_fit": str(t.get("why_better_fit", "")).strip(),
                })

        print(f"[Agent 6] Found {len(validated)} better targets")
        state["better_targets"] = validated

    except Exception as exc:
        print(f"[Agent 6: Recommender] Error: {exc}")
        state["errors"].append(f"Target Recommender failed: {exc}")
        state["better_targets"] = []

    print("[Agent 6: Target Recommender] Done ✓")
    return ensure_complete_state(state)
