from __future__ import annotations

import csv
import re
import tempfile
from pathlib import Path
from typing import Iterable


class CsvStore:
    def __init__(self, path: Path, fieldnames: list[str]):
        self.path = self._resolve_path(path)
        self.fieldnames = fieldnames
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, path: Path) -> Path:
        candidates = list(path.parent.glob(f"test_{path.stem}*{path.suffix}"))
        if not candidates:
            return path

        def rank(p: Path) -> tuple[int, float]:
            # Prefer higher explicit version suffix: test_<name>_v2.csv > test_<name>.csv
            match = re.search(r"_v(\d+)$", p.stem)
            version = int(match.group(1)) if match else 0
            return (version, p.stat().st_mtime)

        return max(candidates, key=rank)

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
