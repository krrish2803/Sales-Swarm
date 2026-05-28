from __future__ import annotations

import os
import json
import re
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

load_dotenv()


def get_llm() -> Any:
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        temperature=0.2,
        max_tokens=2048,
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
    )


async def call_json_llm(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    response = await get_llm().ainvoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    content = response.content
    if isinstance(content, list):
        content = "\n".join(str(part) for part in content)
    return parse_json_object(str(content))


def parse_json_object(raw: str) -> dict[str, Any]:
    print("RAW LLM OUTPUT START ---")
    print(raw)
    print("RAW LLM OUTPUT END ---")
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def list_of_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def bounded_fit_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        if isinstance(value, str):
            match = re.search(r"\d+", value)
            if match:
                score = int(match.group(0))
                return max(0, min(10, score))
        return 0
    return max(0, min(10, score))
