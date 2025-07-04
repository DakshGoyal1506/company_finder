
"""Serialize results to various formats."""
import json
from pathlib import Path
from typing import List

import pandas as pd
from rich.console import Console
from rich.table import Table

from .info_extractor import CompanyRecord

class OutputWriter:
    def __init__(self):
        self.console = Console()

    def to_dataframe(self, records: List[CompanyRecord]) -> pd.DataFrame:
        return pd.DataFrame([r.__dict__ for r in records])

    def save_csv(self, records: List[CompanyRecord], path: str | Path):
        df = self.to_dataframe(records)
        df.to_csv(path, index=False)

    def save_excel(self, records: List[CompanyRecord], path: str | Path):
        df = self.to_dataframe(records)
        df.to_excel(path, index=False)

    def print_pretty(self, records: List[CompanyRecord]):
        table = Table(title="Company Finder Results")
        for col in ["name", "address", "phone", "email", "website"]:
            table.add_column(col, overflow="fold")
        for r in records:
            table.add_row(r.name, r.address or "", r.phone or "", r.email or "", r.website or "")
        self.console.print(table)

    def save_json(self, records: List[CompanyRecord], path: str | Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump([r.__dict__ for r in records], f, ensure_ascii=False, indent=2)
