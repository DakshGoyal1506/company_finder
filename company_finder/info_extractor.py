
"""Convert cleaned page text into structured `CompanyRecord`s."""
import re
from dataclasses import dataclass
from typing import List, Dict

import transformers
from transformers import pipeline
from sentence_transformers import SentenceTransformer, util

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s-]?)?(?:\d{3,4}[\s-]?){2,3}")
_PIN_RE = re.compile(r"\b\d{6}\b")

@dataclass
class CompanyRecord:
    name: str
    address: str | None
    phone: str | None
    email: str | None
    website: str | None
    source_url: str
    industry_score: float

class InfoExtractor:
    def __init__(self,
                 ner_model: str = "dslim/bert-base-NER",
                 industry_classifier: str = "facebook/bart-large-mnli",
                 embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.ner = pipeline("ner", model=ner_model, aggregation_strategy="simple")
        self.classifier = pipeline("zero-shot-classification", model=industry_classifier)
        self.embedder = SentenceTransformer(embed_model)

    # ---------------------
    def extract(self, pages: Dict[str, str], industry_prompt: str) -> List[CompanyRecord]:
        records: List[CompanyRecord] = []
        for url, text in pages.items():
            ents = self.ner(text[:20000])  # limit text for speed
            names = [e["word"] for e in ents if e["entity_group"] == "ORG"]
            locs  = [e["word"] for e in ents if e["entity_group"] == "LOC"]
            name  = names[0] if names else ""
            address_match = _PIN_RE.search(text)
            address = None
            if address_match:
                start = max(0, address_match.start() - 50)
                end = address_match.end() + 50
                address = text[start:end]
            phone = _PHONE_RE.search(text)
            email = _EMAIL_RE.search(text)
            industry_score = self._score_industry(text, industry_prompt)
            records.append(CompanyRecord(
                name=name,
                address=address,
                phone=phone.group(0) if phone else None,
                email=email.group(0) if email else None,
                website=url,
                source_url=url,
                industry_score=industry_score,
            ))
        return records

    def _score_industry(self, text: str, industry_prompt: str) -> float:
        result = self.classifier(text[:10000],
                                 candidate_labels=[industry_prompt],
                                 multi_label=False)
        return float(result["scores"][0])
