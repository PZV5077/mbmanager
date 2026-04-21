from __future__ import annotations

from typing import Iterable

from PySide6.QtWidgets import QLabel, QTableWidget

from .utils import status_feedback_group


def selected_record_ids(
    table: QTableWidget,
    row_to_record_id: dict[int, str],
    preferred: list[str] | None = None,
) -> list[str]:
    if preferred:
        return list(dict.fromkeys(preferred))

    selection = table.selectionModel()
    rows = {index.row() for index in selection.selectedRows()} if selection is not None else set()
    ids = [rid for row in sorted(rows) if (rid := row_to_record_id.get(row)) is not None]
    if ids:
        return ids

    current_row = table.currentRow()
    current_id = row_to_record_id.get(current_row)
    return [current_id] if current_id else []


def status_group_counts(records: Iterable[dict[str, str]]) -> dict[str, int]:
    counts = {"action": 0, "progress": 0, "success": 0, "risk": 0, "neutral": 0}
    for record in records:
        counts[status_feedback_group(record.get("status", "NotStarted"))] += 1
    return counts


def set_metric_chip(chip: QLabel, label: str, value: int, state: str) -> None:
    chip.setText(f"{label}: {value}")
    chip.setProperty("state", state)
    chip.style().unpolish(chip)
    chip.style().polish(chip)
    chip.update()


def view_hint_text(sort_field: str, sort_ascending: bool, total: int, neutral: int, selected: int) -> str:
    sort_label = sort_field.replace("_", " ").title()
    sort_order = "ASC" if sort_ascending else "DESC"
    return f"Sort: {sort_label} {sort_order} · Visible: {total} · Idle: {neutral} · Selected: {selected}"
