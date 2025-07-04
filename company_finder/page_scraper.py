
"""Download & clean web pages asynchronously."""
import asyncio
import re
from typing import Dict

import aiohttp
from bs4 import BeautifulSoup

from .config import CONFIG

class PageScraper:
    def __init__(self, concurrency: int = 20, timeout: int = 15):
        self.semaphore = asyncio.Semaphore(concurrency)
        self.timeout = timeout

    async def _fetch(self, session: aiohttp.ClientSession, url: str) -> str:
        async with self.semaphore:
            try:
                async with session.get(url, timeout=self.timeout) as resp:
                    if resp.status != 200 or "text/html" not in resp.headers.get("Content-Type", ""):
                        return ""
                    return await resp.text()
            except Exception:
                return ""

    @staticmethod
    def _clean(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "meta", "link"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r"\s{2,}", " ", text)
        return text

    async def scrape(self, urls: list[str]) -> Dict[str, str]:
        async with aiohttp.ClientSession(headers={"User-Agent": CONFIG.user_agent}) as session:
            tasks = [asyncio.create_task(self._fetch(session, url)) for url in urls]
            html_pages = await asyncio.gather(*tasks, return_exceptions=False)
        return {url: self._clean(html) for url, html in zip(urls, html_pages) if html}
