from __future__ import annotations

import asyncio
import os
from urllib.parse import urljoin

import httpx
from dotenv import load_dotenv

load_dotenv()

JINA_READER_BASE = "https://r.jina.ai/"
SCRAPE_TIMEOUT_SECONDS = 4.0


def _normalize_url(url: str) -> str:
    cleaned = url.strip()
    if not cleaned.startswith(("http://", "https://")):
        cleaned = f"https://{cleaned}"
    return cleaned.rstrip("/")


def _reader_url(url: str) -> str:
    return f"{JINA_READER_BASE}{_normalize_url(url)}"


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "text/plain",
        "X-Return-Format": "markdown",
    }
    jina_api_key = os.getenv("JINA_API_KEY", "").strip()
    if jina_api_key:
        headers["Authorization"] = f"Bearer {jina_api_key}"
    return headers


def _clean_markdown(markdown: str) -> str:
    lines = [line.rstrip() for line in markdown.splitlines()]
    compact: list[str] = []
    blank_seen = False

    for line in lines:
        if not line.strip():
            if not blank_seen:
                compact.append("")
            blank_seen = True
            continue
        compact.append(line)
        blank_seen = False

    return "\n".join(compact).strip()


async def scrape_url(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=SCRAPE_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(_reader_url(url), headers=_headers())
            response.raise_for_status()
            return _clean_markdown(response.text)
    except Exception as exc:
        print(f"[Scraper] Failed to scrape {url}: {exc}")
        return ""


async def _first_result(urls: list[str]) -> str:
    results = await asyncio.gather(*[scrape_url(u) for u in urls], return_exceptions=True)
    for r in results:
        if isinstance(r, str) and r.strip():
            return r
    return ""


async def scrape_jobs_page(url: str) -> str:
    base_url = _normalize_url(url)
    return await _first_result([
        urljoin(f"{base_url}/", "careers"),
        urljoin(f"{base_url}/", "jobs"),
    ])


async def scrape_blog(url: str) -> str:
    base_url = _normalize_url(url)
    return await _first_result([
        urljoin(f"{base_url}/", "blog"),
        urljoin(f"{base_url}/", "changelog"),
    ])

