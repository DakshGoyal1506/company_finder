"""Optional enrichment using external APIs (Google Places or OSM/Nominatim)."""
import aiohttp
import os
from typing import List
import asyncio

from .config import CONFIG
from .info_extractor import CompanyRecord

GOOGLE_PLACES_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
NOMINATIM_URL      = "https://nominatim.openstreetmap.org/search"

class Enricher:
    def __init__(self, api_key: str | None = None):
        # if you have a key, this is Google; else fallback to Nominatim
        self.google_key = api_key or CONFIG.google_places_key
        # Nominatim doesn’t need a key but *does* require a User-Agent
        self.ua = CONFIG.user_agent

    async def enrich(self, records: List[CompanyRecord]) -> List[CompanyRecord]:
        if self.google_key:
            return await self._enrich_google(records)
        return await self._enrich_nominatim(records)

    async def _enrich_google(self, records: List[CompanyRecord]) -> List[CompanyRecord]:
        async with aiohttp.ClientSession() as session:
            tasks = [self._enrich_one_google(session, r) for r in records]
            return await asyncio.gather(*tasks, return_exceptions=False)

    async def _enrich_one_google(self, session: aiohttp.ClientSession, rec: CompanyRecord) -> CompanyRecord:
        params = {
            "input": rec.name,
            "inputtype": "textquery",
            "fields": "formatted_address,website,name,formatted_phone_number",
            "key": self.google_key,
        }
        try:
            async with session.get(GOOGLE_PLACES_URL, params=params, headers={"User-Agent": self.ua}) as resp:
                data = await resp.json()
                if data.get("candidates"):
                    c = data["candidates"][0]
                    rec.address = c.get("formatted_address", rec.address)
                    rec.phone   = c.get("formatted_phone_number", rec.phone)
                    rec.website = c.get("website", rec.website)
        except Exception:
            pass
        return rec

    async def _enrich_nominatim(self, records: List[CompanyRecord]) -> List[CompanyRecord]:
        headers = {"User-Agent": self.ua}
        async with aiohttp.ClientSession(headers=headers) as session:
            tasks = [self._enrich_one_nominatim(session, r) for r in records]
            return await asyncio.gather(*tasks, return_exceptions=False)

    async def _enrich_one_nominatim(self, session: aiohttp.ClientSession, rec: CompanyRecord) -> CompanyRecord:
        # query = name + maybe address fragment
        q = rec.name + (f" {rec.address}" if rec.address else "")
        params = {
            "q": q,
            "format": "json",
            "limit": 1,
        }
        try:
            async with session.get(NOMINATIM_URL, params=params) as resp:
                data = await resp.json()
                if data:
                    top = data[0]
                    # Nominatim returns display_name, lat, lon, osm_url etc.
                    rec.address = top.get("display_name", rec.address)
                    # stick the OSM link into website field if empty
                    if not rec.website:
                        rec.website = f"https://www.openstreetmap.org/{top.get('osm_type')[0]}/{top.get('osm_id')}"
        except Exception:
            pass
        return rec