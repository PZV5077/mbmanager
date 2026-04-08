from __future__ import annotations

import csv
import tempfile
from pathlib import Path
from typing import Iterable


class CsvStore:
    def __init__(self, path: Path, fieldnames: list[str]):
        self.path = path
        self.fieldnames = fieldnames
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def ensure_exists(self) -> None:
        if self.path.exists():
            return
        self.save([])

    def load(self) -> list[dict[str, str]]:
        self.ensure_exists()
        rows: list[dict[str, str]] = []
        with self.path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                rows.append({field: (raw.get(field, "") or "") for field in self.fieldnames})
        return rows

    def save(self, records: Iterable[dict[str, str]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            newline="",
            encoding="utf-8",
            delete=False,
            dir=str(self.path.parent),
            prefix=f".{self.path.stem}_",
            suffix=".tmp",
        ) as tf:
            writer = csv.DictWriter(tf, fieldnames=self.fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow({field: (record.get(field, "") or "") for field in self.fieldnames})
            temp = tf.name
        Path(temp).replace(self.path)
