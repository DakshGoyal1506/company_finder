
"""Wrap a search‑engine API (SerpAPI by default)."""
import asyncio
import json
from typing import List

import aiohttp
from .config import CONFIG

SERP_ENDPOINT = "https://serpapi.com/search.json"

class SearchClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or CONFIG.serp_api_key

    async def _fetch(self, session: aiohttp.ClientSession, query: str) -> List[str]:
        params = {
            "api_key": self.api_key,
            "engine": "google",
            "q": query,
            "num": CONFIG.max_search_results,
        }
        async with session.get(SERP_ENDPOINT, params=params) as resp:
            data = await resp.json()
            return [r["link"] for r in data.get("organic_results", [])]

    async def search(self, queries: List[str]) -> List[str]:
        async with aiohttp.ClientSession(headers={"User-Agent": CONFIG.user_agent}) as session:
            tasks = [asyncio.create_task(self._fetch(session, q)) for q in queries]
            results = await asyncio.gather(*tasks, return_exceptions=False)
        flat = [url for sub in results for url in sub]
        # Deduplicate early
        seen = set()
        unique = []
        for url in flat:
            if url not in seen:
                seen.add(url)
                unique.append(url)
        return unique
