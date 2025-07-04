
"""Main pipeline orchestrator."""
import asyncio
from typing import List

from .query_generator import QueryGenerator
from .search_client import SearchClient
from .page_scraper import PageScraper
from .info_extractor import InfoExtractor, CompanyRecord
from .deduplicator import Deduplicator
from .enricher import Enricher

class Orchestrator:
    def __init__(self):
        self.qg = QueryGenerator()
        self.sc = SearchClient()
        self.ps = PageScraper()
        self.ie = InfoExtractor()
        self.dd = Deduplicator()
        self.en = Enricher()

    # ------------------------------------------------
    async def _run_async(self, industry: str, location: str) -> List[CompanyRecord]:
        queries = self.qg.generate(industry, location)
        urls = await self.sc.search(queries)
        pages = await self.ps.scrape(urls)
        extracted = self.ie.extract(pages, industry_prompt=industry)
        deduped = self.dd.dedupe(extracted)
        enriched = await self.en.enrich(deduped)
        return enriched

    # ------------------------------------------------
    def run(self, industry: str, location: str) -> List[CompanyRecord]:
        return asyncio.run(self._run_async(industry, location))
