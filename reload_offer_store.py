from __future__ import annotations

import calendar
import json
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from utils import DATE_FMT, new_id, parse_date, today_str


def _date_to_text(value: date) -> str:
    return value.strftime(DATE_FMT)


def _text_to_date(value: str | None) -> date | None:
    parsed = parse_date(value or "")
    return parsed.date() if parsed is not None else None


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _weekday_name(index: int) -> str:
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    if 0 <= index < len(names):
        return names[index]
    return "Mon"


def _preview_value_pairs(values: dict[str, str]) -> list[str]:
    preferred_keys = [
        "bookie",
        "promo_name",
        "deposit_amount",
        "qb1_type",
        "qb1_amount",
        "has_qb2",
        "qb2_type",
        "qb2_amount",
        "bonus_type",
        "bonus_amount",
        "final_amount",
        "bank_status",
        "notes",
    ]
    lines: list[str] = []
    for key in preferred_keys:
        value = (values.get(key, "") or "").strip()
        if value:
            lines.append(f"{key}: {value}")
    if lines:
        return lines[:5]

    for key, value in values.items():
        value = (value or "").strip()
        if value:
            lines.append(f"{key}: {value}")
        if len(lines) >= 5:
            break
    return lines


class ReloadOfferStore:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "reload_offers.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self._default_db()
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return self._default_db()
        return self._normalize_db(data)

    def save(self, data: dict[str, Any]) -> None:
        normalized = self._normalize_db(data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=str(self.path.parent),
            prefix=".reload_offers_",
            suffix=".tmp",
        ) as tf:
            json.dump(normalized, tf, ensure_ascii=True, indent=2)
            temp = tf.name
        Path(temp).replace(self.path)

    def replace_templates(self, templates: list[dict[str, Any]]) -> dict[str, Any]:
        db = self.load()
        db["templates"] = [self._normalize_template(template) for template in templates]
        return self.ensure_schedule(db)

    def upsert_template(self, template: dict[str, Any]) -> dict[str, Any]:
        db = self.load()
        normalized = self._normalize_template(template)
        templates = db["templates"]
        for index, existing in enumerate(templates):
            if existing["id"] == normalized["id"]:
                templates[index] = normalized
                break
        else:
            templates.append(normalized)
        return self.ensure_schedule(db)

    def delete_template(self, template_id: str) -> dict[str, Any]:
        db = self.load()
        today = date.today()
        db["templates"] = [template for template in db["templates"] if template["id"] != template_id]
        db["instances"] = [
            instance
            for instance in db["instances"]
            if instance.get("template_id") != template_id or (_text_to_date(instance.get("scheduled_date")) or today) < today
        ]
        return self.ensure_schedule(db)

    def ensure_schedule(
        self,
        db: dict[str, Any] | None = None,
        *,
        history_days: int = 30,
        horizon_days: int = 180,
    ) -> dict[str, Any]:
        db = self._normalize_db(db or self.load())
        today = date.today()
        window_start = today - timedelta(days=history_days)
        window_end = today + timedelta(days=horizon_days)

        active_ids = {template["id"] for template in db["templates"] if template.get("enabled", True)}
        retained_instances: list[dict[str, Any]] = []
        for instance in db["instances"]:
            scheduled = _text_to_date(instance.get("scheduled_date"))
            if scheduled is None:
                continue
            if instance.get("template_id") not in active_ids and scheduled >= today:
                continue
            if window_start <= scheduled <= window_end or scheduled < today:
                retained_instances.append(self._normalize_instance(instance))

        existing_keys = {
            (instance.get("template_id"), instance.get("scheduled_date"))
            for instance in retained_instances
        }

        for template in db["templates"]:
            if not template.get("enabled", True):
                continue
            for occurrence in self._occurrence_dates(template, window_start, window_end):
                scheduled_text = _date_to_text(occurrence)
                key = (template["id"], scheduled_text)
                if key in existing_keys:
                    continue
                retained_instances.append(self._build_instance(template, occurrence))
                existing_keys.add(key)

        retained_instances.sort(key=lambda item: (item.get("scheduled_date", ""), item.get("template_name", "")))
        db["instances"] = retained_instances
        db["templates"] = [self._normalize_template(template) for template in db["templates"]]
        self.save(db)
        return db

    def instances_for_date(self, selected_date: date, db: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        db = self._normalize_db(db or self.load())
        key = _date_to_text(selected_date)
        return [instance for instance in db["instances"] if instance.get("scheduled_date") == key]

    def template_summary(self, template: dict[str, Any]) -> str:
        repeat_type = template.get("repeat_type", "weekly")
        if repeat_type in {"weekly", "biweekly"}:
            interval = "Every week" if repeat_type == "weekly" else "Every 2 weeks"
            weekday = _weekday_name(_safe_int(template.get("weekday"), 0))
            return f"{interval} on {weekday}"
        if repeat_type == "monthly":
            month_day = _safe_int(template.get("month_day"), 1)
            return f"Every month on day {month_day}"
        return "Manual"

    def instance_preview_lines(self, instance: dict[str, Any]) -> list[str]:
        lines = [f"Status: {instance.get('status', 'pending')}" ]
        values_obj = instance.get("values")
        values: dict[str, Any] = values_obj if isinstance(values_obj, dict) else {}
        lines.extend(_preview_value_pairs({k: str(v) for k, v in values.items()}))
        return lines

    def _default_db(self) -> dict[str, Any]:
        return {"templates": [], "instances": []}

    def _normalize_db(self, db: Any) -> dict[str, Any]:
        if not isinstance(db, dict):
            db = self._default_db()
        templates = db.get("templates")
        instances = db.get("instances")
        db["templates"] = [self._normalize_template(template) for template in templates] if isinstance(templates, list) else []
        db["instances"] = [self._normalize_instance(instance) for instance in instances] if isinstance(instances, list) else []
        return db

    def _normalize_template(self, template: Any) -> dict[str, Any]:
        if not isinstance(template, dict):
            template = {}
        fixed_fields = template.get("fixed_fields")
        if not isinstance(fixed_fields, dict):
            fixed_fields = {}
        anchor_date = template.get("anchor_date") or today_str()
        repeat_type = template.get("repeat_type") if template.get("repeat_type") in {"weekly", "biweekly", "monthly"} else "weekly"
        return {
            "id": str(template.get("id") or new_id()),
            "name": str(template.get("name") or "New Template"),
            "enabled": bool(template.get("enabled", True)),
            "anchor_date": anchor_date,
            "repeat_type": repeat_type,
            "weekday": _safe_int(template.get("weekday"), date.today().weekday()),
            "month_day": max(1, min(31, _safe_int(template.get("month_day"), date.today().day))),
            "fixed_fields": {str(key): str(value) for key, value in fixed_fields.items()},
        }

    def _normalize_instance(self, instance: Any) -> dict[str, Any]:
        if not isinstance(instance, dict):
            instance = {}
        values = instance.get("values")
        if not isinstance(values, dict):
            values = {}
        status = str(instance.get("status") or "pending")
        scheduled_date = instance.get("scheduled_date") or _date_to_text(date.today())
        return {
            "id": str(instance.get("id") or new_id()),
            "template_id": str(instance.get("template_id") or ""),
            "template_name": str(instance.get("template_name") or ""),
            "scheduled_date": str(scheduled_date),
            "status": status,
            "values": {str(key): str(value) for key, value in values.items()},
            "created_at": str(instance.get("created_at") or today_str()),
            "updated_at": str(instance.get("updated_at") or today_str()),
        }

    def _build_instance(self, template: dict[str, Any], scheduled_date: date) -> dict[str, Any]:
        values = {str(key): str(value) for key, value in template.get("fixed_fields", {}).items()}
        return {
            "id": new_id(),
            "template_id": template["id"],
            "template_name": template.get("name", ""),
            "scheduled_date": _date_to_text(scheduled_date),
            "status": "pending",
            "values": values,
            "created_at": today_str(),
            "updated_at": today_str(),
        }

    def _occurrence_dates(self, template: dict[str, Any], start: date, end: date) -> list[date]:
        anchor = _text_to_date(template.get("anchor_date")) or date.today()
        repeat_type = template.get("repeat_type", "weekly")
        if repeat_type in {"weekly", "biweekly"}:
            weekday = _safe_int(template.get("weekday"), anchor.weekday())
            interval_days = 7 if repeat_type == "weekly" else 14
            first = self._next_weekday_on_or_after(anchor, weekday)
            while first < start:
                first += timedelta(days=interval_days)
            occurrences: list[date] = []
            current = first
            while current <= end:
                if current >= anchor:
                    occurrences.append(current)
                current += timedelta(days=interval_days)
            return occurrences

        if repeat_type == "monthly":
            desired_day = _safe_int(template.get("month_day"), anchor.day)
            occurrences = []
            current = date(anchor.year, anchor.month, 1)
            while current <= end:
                last_day = calendar.monthrange(current.year, current.month)[1]
                candidate = date(current.year, current.month, min(desired_day, last_day))
                if candidate >= anchor and start <= candidate <= end:
                    occurrences.append(candidate)
                if current.month == 12:
                    current = date(current.year + 1, 1, 1)
                else:
                    current = date(current.year, current.month + 1, 1)
            return occurrences

        return []

    def _next_weekday_on_or_after(self, start: date, weekday: int) -> date:
        delta = (weekday - start.weekday()) % 7
        return start + timedelta(days=delta)
