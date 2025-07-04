
"""Merge probable duplicates via semantic clustering."""
from collections import defaultdict
from typing import List

import hdbscan
from sentence_transformers import SentenceTransformer
from .info_extractor import CompanyRecord

class Deduplicator:
    def __init__(self, embed_model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.embedder = SentenceTransformer(embed_model)

    def dedupe(self, records: List[CompanyRecord]) -> List[CompanyRecord]:
        if not records:
            return records
        texts = [f"{r.name} {r.address or ''}" for r in records]
        embeddings = self.embedder.encode(texts, normalize_embeddings=True)
        clusterer = hdbscan.HDBSCAN(min_cluster_size=2, metric="euclidean").fit(embeddings)
        clusters = defaultdict(list)
        for idx, label in enumerate(clusterer.labels_):
            clusters[label].append(records[idx])

        unique: List[CompanyRecord] = []
        for label, group in clusters.items():
            if label == -1:
                unique.extend(group)
            else:
                best = max(group, key=lambda r: r.industry_score)
                # merge contacts
                for rec in group:
                    if rec is not best:
                        if not best.phone and rec.phone:
                            best.phone = rec.phone
                        if not best.email and rec.email:
                            best.email = rec.email
                        if not best.address and rec.address:
                            best.address = rec.address
                unique.append(best)
        return unique
