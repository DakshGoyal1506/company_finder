
import os
from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class Config:
    serp_api_key: str = field(default_factory=lambda: os.getenv("SERP_API_KEY", ""))
    google_places_key: str = field(default_factory=lambda: os.getenv("GOOGLE_PLACES_KEY", ""))
    user_agent: str = "Mozilla/5.0 (compatible; CompanyFinder/0.1)"
    max_search_results: int = 50

    @staticmethod
    def load() -> "Config":
        return Config()

# expose a global config instance
CONFIG = Config.load()
