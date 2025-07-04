
"""Generate high‑quality search phrases from (industry, location)."""
import re
from typing import List, Sequence

import nltk
nltk.download("stopwords", quiet=True)
from sentence_transformers import SentenceTransformer, util

_STOPWORDS = set(nltk.corpus.stopwords.words("english"))

class QueryGenerator:
    """Expand and rank search queries."""

    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.embedder = SentenceTransformer(model_name)

    # ------------------------
    # Public API
    # ------------------------
    def generate(self, industry: str, location: str, k: int = 8) -> List[str]:
        tokens = self._tokenize(industry)
        synonyms = self._expand(tokens)
        prompts = self._compose_prompts(synonyms, location)
        ranked = self._rank(prompts, f"{industry} in {location}", top_k=k)
        return ranked

    # ------------------------
    # Internals
    # ------------------------
    @staticmethod
    def _tokenize(text: str) -> List[str]:
        text = re.sub(r"[^A-Za-z0-9 ]+", " ", text.lower())
        return [tok for tok in text.split() if tok not in _STOPWORDS]

    def _expand(self, tokens: Sequence[str]) -> List[str]:
        """Return tokens + top semantic neighbours for each token."""
        base_emb = self.embedder.encode(tokens, convert_to_tensor=True, normalize_embeddings=True)
        # Very small toy list – in production you would query a pre‑built vocab embedding matrix.
        candidates = ["artificial intelligence", "data science", "analytics", "computer vision",
                      "deep learning", "machine learning", "nlp", "natural language processing"]
        cand_emb = self.embedder.encode(candidates, convert_to_tensor=True, normalize_embeddings=True)
        similarities = util.cos_sim(base_emb.mean(dim=0), cand_emb)[0].tolist()
        scored = sorted(zip(candidates, similarities), key=lambda t: t[1], reverse=True)
        return list({*tokens, *[c for c, s in scored[:5]]})

    @staticmethod
    def _compose_prompts(synonyms: Sequence[str], city: str) -> List[str]:
        patterns = [
            "{syn} companies in {city}",
            "top {syn} startups near {city}",
            "{syn} firms {city}",
            "best {syn} agencies in {city}"
        ]
        prompts = []
        for syn in synonyms:
            for pat in patterns:
                prompts.append(pat.format(syn=syn, city=city))
        return prompts

    def _rank(self, prompts: Sequence[str], query_intent: str, top_k: int) -> List[str]:
        intent_emb = self.embedder.encode(query_intent, convert_to_tensor=True, normalize_embeddings=True)
        prompt_emb = self.embedder.encode(prompts, convert_to_tensor=True, normalize_embeddings=True)
        sims = util.cos_sim(intent_emb, prompt_emb)[0].tolist()
        ranked = [p for p, _ in sorted(zip(prompts, sims), key=lambda t: t[1], reverse=True)]
        return ranked[:top_k]
