from __future__ import annotations

import sqlite3
from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from .constants import (
    BETTING_BANK_VALUES,
    BETTING_B_EXCHANGES,
    BETTING_B_TYPES,
    BETTING_Q_EXCHANGES,
    BETTING_Q_TYPES,
    BETTING_STATUS_VALUES,
)
from .utils import CASINO_STATUS_ORDER, fmt_decimal, new_id, parse_date, parse_decimal

BETTING_TEXT_FIELDS = {
    "id",
    "status",
    "start_at",
    "bookie",
    "promo_name",
    "q_result_at",
    "q_event",
    "q_type",
    "q_target",
    "q_exchange",
    "b_result_at",
    "b_event",
    "b_type",
    "b_target",
    "b_exchange",
    "bank",
    "notes",
}

BETTING_NUMERIC_FIELDS = {"deposit_amount", "q_amount", "b_amount", "profit"}
BETTING_BOOL_FIELDS = {"q_is_placed", "q_is_completed", "b_is_placed", "b_is_completed"}

BETTING_DB_COLUMNS = [
    "id",
    "status",
    "start_at",
    "bookie",
    "promo_name",
    "deposit_amount",
    "q_result_at",
    "q_event",
    "q_type",
    "q_amount",
    "q_target",
    "q_exchange",
    "q_is_placed",
    "q_is_completed",
    "b_result_at",
    "b_event",
    "b_type",
    "b_amount",
    "b_target",
    "b_exchange",
    "b_is_placed",
    "b_is_completed",
    "profit",
    "bank",
    "notes",
    "created_at",
    "updated_at",
]

CASINO_DB_COLUMNS = [
    "id",
    "status",
    "bookie",
    "promo_start_date",
    "promo_name",
    "deposit_amount",
    "final_amount",
    "bank_status",
    "profit",
    "notes",
    "created_at",
    "updated_at",
]

CASINO_TEXT_FIELDS = {
    "id",
    "status",
    "bookie",
    "promo_start_date",
    "promo_name",
    "deposit_amount",
    "final_amount",
    "bank_status",
    "profit",
    "notes",
}

CASINO_STATUS_VALUES = ["NotStarted", "NeedDeposit", "NeedFinal", "WaitBank", "Done", "Error"]
CASINO_BANK_STATUS_VALUES = ["Unconfirmed", "Received", "Issue"]

RELOAD_TEMPLATE_COLUMNS = [
    "id",
    "enabled",
    "start_at",
    "bookie",
    "promo_name",
    "repeat_mode",
    "repeat_weekday",
    "repeat_monthday",
    "deposit_amount",
    "bet_amount",
    "bet_type",
    "bonus_amount",
    "bonus_type",
    "notes",
    "created_at",
    "updated_at",
]

RELOAD_INSTANCE_COLUMNS = [
    "id",
    "template_id",
    "scheduled_date",
    "start_at",
    "bookie",
    "promo_name",
    "deposit_amount",
    "bet_amount",
    "bet_type",
    "bonus_amount",
    "bonus_type",
    "notes",
    "betting_record_id",
    "created_at",
    "updated_at",
]

_RELOAD_REPEAT_MODES = {"weekly", "monthly"}


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _as_text(value: Any) -> str:
    return str(value or "").strip()


def _as_bool(value: Any) -> int:
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, int):
        return 1 if value != 0 else 0
    text = _as_text(value).lower()
    return 1 if text in {"1", "true", "yes", "y"} else 0


def _as_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _as_text(value)
    if not text:
        return None
    dec = parse_decimal(text)
    if dec is None:
        raise ValueError(f"Invalid numeric value: {value}")
    return float(dec)


def _sql_quoted(values: list[str]) -> str:
    return ", ".join(f"'{value.replace("'", "''")}'" for value in values)


class AppDatabase:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "mbmanager.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        q_types = _sql_quoted(BETTING_Q_TYPES)
        b_types = _sql_quoted(BETTING_B_TYPES)
        q_exchanges = _sql_quoted(BETTING_Q_EXCHANGES)
        b_exchanges = _sql_quoted(BETTING_B_EXCHANGES)
        banks = _sql_quoted(BETTING_BANK_VALUES)
        reload_repeat_modes = _sql_quoted(sorted(_RELOAD_REPEAT_MODES))

        self.conn.executescript(
            f"""
            PRAGMA journal_mode = WAL;
            PRAGMA foreign_keys = ON;
            PRAGMA synchronous = NORMAL;

            CREATE TABLE IF NOT EXISTS betting_records (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'NotStarted',
                start_at TEXT NOT NULL DEFAULT '',
                bookie TEXT NOT NULL DEFAULT '',
                promo_name TEXT NOT NULL DEFAULT '',
                deposit_amount REAL,
                q_result_at TEXT NOT NULL DEFAULT '',
                q_event TEXT NOT NULL DEFAULT '',
                q_type TEXT NOT NULL DEFAULT '' CHECK (q_type IN ({q_types})),
                q_amount REAL,
                q_target TEXT NOT NULL DEFAULT '',
                q_exchange TEXT NOT NULL DEFAULT '' CHECK (q_exchange IN ({q_exchanges})),
                q_is_placed INTEGER NOT NULL DEFAULT 0 CHECK (q_is_placed IN (0, 1)),
                q_is_completed INTEGER NOT NULL DEFAULT 0 CHECK (q_is_completed IN (0, 1)),
                b_result_at TEXT NOT NULL DEFAULT '',
                b_event TEXT NOT NULL DEFAULT '',
                b_type TEXT NOT NULL DEFAULT '' CHECK (b_type IN ({b_types})),
                b_amount REAL,
                b_target TEXT NOT NULL DEFAULT '',
                b_exchange TEXT NOT NULL DEFAULT '' CHECK (b_exchange IN ({b_exchanges})),
                b_is_placed INTEGER NOT NULL DEFAULT 0 CHECK (b_is_placed IN (0, 1)),
                b_is_completed INTEGER NOT NULL DEFAULT 0 CHECK (b_is_completed IN (0, 1)),
                profit REAL,
                bank TEXT NOT NULL DEFAULT 'Uncon' CHECK (bank IN ({banks})),
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_betting_status_start ON betting_records(status, start_at DESC);
            CREATE INDEX IF NOT EXISTS idx_betting_bookie ON betting_records(bookie);
            CREATE INDEX IF NOT EXISTS idx_betting_promo ON betting_records(promo_name);
            CREATE INDEX IF NOT EXISTS idx_betting_q_date ON betting_records(q_result_at);
            CREATE INDEX IF NOT EXISTS idx_betting_b_date ON betting_records(b_result_at);
            CREATE INDEX IF NOT EXISTS idx_betting_bank ON betting_records(bank);

            CREATE TABLE IF NOT EXISTS casino_records (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'NotStarted',
                bookie TEXT NOT NULL DEFAULT '',
                promo_start_date TEXT NOT NULL DEFAULT '',
                promo_name TEXT NOT NULL DEFAULT '',
                deposit_amount TEXT NOT NULL DEFAULT '',
                final_amount TEXT NOT NULL DEFAULT '',
                bank_status TEXT NOT NULL DEFAULT 'Unconfirmed',
                profit TEXT NOT NULL DEFAULT '',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_casino_status_start ON casino_records(status, promo_start_date DESC);
            CREATE INDEX IF NOT EXISTS idx_casino_bookie ON casino_records(bookie);
            """
        )
        self._ensure_reload_offer_schema(q_types, b_types, reload_repeat_modes)

    def close(self) -> None:
        self.conn.close()

    def _ensure_reload_offer_schema(self, q_types: str, b_types: str, reload_repeat_modes: str) -> None:
        template_columns = {str(row[1]) for row in self.conn.execute("PRAGMA table_info(reload_offer_templates)")}
        instance_columns = {str(row[1]) for row in self.conn.execute("PRAGMA table_info(reload_offer_instances)")}

        expected_template_columns = {
            "id",
            "enabled",
            "start_at",
            "bookie",
            "promo_name",
            "repeat_mode",
            "repeat_weekday",
            "repeat_monthday",
            "deposit_amount",
            "bet_amount",
            "bet_type",
            "bonus_amount",
            "bonus_type",
            "notes",
            "created_at",
            "updated_at",
        }
        expected_instance_columns = {
            "id",
            "template_id",
            "scheduled_date",
            "start_at",
            "bookie",
            "promo_name",
            "deposit_amount",
            "bet_amount",
            "bet_type",
            "bonus_amount",
            "bonus_type",
            "notes",
            "betting_record_id",
            "created_at",
            "updated_at",
        }

        if template_columns != expected_template_columns:
            with self.conn:
                self.conn.execute("DROP TABLE IF EXISTS reload_offer_templates")
                self.conn.execute(
                    f"""
                    CREATE TABLE reload_offer_templates (
                        id TEXT PRIMARY KEY,
                        enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
                        start_at TEXT NOT NULL DEFAULT '',
                        bookie TEXT NOT NULL DEFAULT '',
                        promo_name TEXT NOT NULL DEFAULT '',
                        repeat_mode TEXT NOT NULL DEFAULT 'weekly' CHECK (repeat_mode IN ({reload_repeat_modes})),
                        repeat_weekday INTEGER NOT NULL DEFAULT 0 CHECK (repeat_weekday BETWEEN 0 AND 6),
                        repeat_monthday INTEGER NOT NULL DEFAULT 1 CHECK (repeat_monthday BETWEEN 1 AND 31),
                        deposit_amount REAL,
                        bet_amount REAL,
                        bet_type TEXT NOT NULL DEFAULT '' CHECK (bet_type IN ({q_types})),
                        bonus_amount REAL,
                        bonus_type TEXT NOT NULL DEFAULT '' CHECK (bonus_type IN ({b_types})),
                        notes TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                self.conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_reload_template_enabled ON reload_offer_templates(enabled, repeat_mode)"
                )
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_reload_template_bookie ON reload_offer_templates(bookie)")

        if instance_columns != expected_instance_columns:
            with self.conn:
                self.conn.execute("DROP TABLE IF EXISTS reload_offer_instances")
                self.conn.execute(
                    f"""
                    CREATE TABLE reload_offer_instances (
                        id TEXT PRIMARY KEY,
                        template_id TEXT NOT NULL,
                        scheduled_date TEXT NOT NULL,
                        start_at TEXT NOT NULL DEFAULT '',
                        bookie TEXT NOT NULL DEFAULT '',
                        promo_name TEXT NOT NULL DEFAULT '',
                        deposit_amount REAL,
                        bet_amount REAL,
                        bet_type TEXT NOT NULL DEFAULT '' CHECK (bet_type IN ({q_types})),
                        bonus_amount REAL,
                        bonus_type TEXT NOT NULL DEFAULT '' CHECK (bonus_type IN ({b_types})),
                        notes TEXT NOT NULL DEFAULT '',
                        betting_record_id TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        FOREIGN KEY(template_id) REFERENCES reload_offer_templates(id) ON DELETE CASCADE
                    )
                    """
                )
                self.conn.execute(
                    "CREATE UNIQUE INDEX IF NOT EXISTS idx_reload_instance_template_date ON reload_offer_instances(template_id, scheduled_date)"
                )
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_reload_instance_date ON reload_offer_instances(scheduled_date)")
                self.conn.execute("CREATE INDEX IF NOT EXISTS idx_reload_instance_betting ON reload_offer_instances(betting_record_id)")

    def fetch_betting_records(
        self,
        *,
        search: str = "",
        status: str = "Any",
        bank: str = "Any",
        sort_field: str = "start_at",
        ascending: bool = True,
    ) -> list[dict[str, str]]:
        where: list[str] = ["1=1"]
        params: list[Any] = []

        if status and status != "Any":
            where.append("status = ?")
            params.append(status)

        if bank and bank != "Any":
            where.append("bank = ?")
            params.append(bank)

        term = _as_text(search)
        if term:
            like = f"%{term}%"
            where.append(
                "(" + " OR ".join(
                    [
                        "bookie LIKE ?",
                        "promo_name LIKE ?",
                        "notes LIKE ?",
                        "q_target LIKE ?",
                        "b_target LIKE ?",
                    ]
                ) + ")"
            )
            params.extend([like, like, like, like, like])

        order_sql = self._betting_order_sql(sort_field, ascending)
        query = f"SELECT * FROM betting_records WHERE {' AND '.join(where)} {order_sql}"  # noqa: S608
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_betting_record(row) for row in rows]

    def list_betting_bookies(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT bookie FROM betting_records WHERE TRIM(bookie) != '' ORDER BY LOWER(bookie)"
        ).fetchall()
        return [str(row[0]) for row in rows]

    def get_betting_record(self, record_id: str) -> dict[str, str] | None:
        row = self.conn.execute("SELECT * FROM betting_records WHERE id = ?", (record_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_betting_record(row)

    def insert_betting_record(self, record: dict[str, Any]) -> None:
        payload = self._normalize_betting_payload(record)
        now = _now_text()
        payload["created_at"] = _as_text(record.get("created_at")) or now
        payload["updated_at"] = _as_text(record.get("updated_at")) or now

        cols = ", ".join(BETTING_DB_COLUMNS)
        holders = ", ".join(["?"] * len(BETTING_DB_COLUMNS))
        values = [payload[column] for column in BETTING_DB_COLUMNS]
        with self.conn:
            self.conn.execute(f"INSERT INTO betting_records ({cols}) VALUES ({holders})", values)  # noqa: S608

    def update_betting_record(self, record_id: str, record: dict[str, Any]) -> None:
        payload = self._normalize_betting_payload(record)
        payload["updated_at"] = _now_text()

        assignments = [
            "status = ?",
            "start_at = ?",
            "bookie = ?",
            "promo_name = ?",
            "deposit_amount = ?",
            "q_result_at = ?",
            "q_event = ?",
            "q_type = ?",
            "q_amount = ?",
            "q_target = ?",
            "q_exchange = ?",
            "q_is_placed = ?",
            "q_is_completed = ?",
            "b_result_at = ?",
            "b_event = ?",
            "b_type = ?",
            "b_amount = ?",
            "b_target = ?",
            "b_exchange = ?",
            "b_is_placed = ?",
            "b_is_completed = ?",
            "profit = ?",
            "bank = ?",
            "notes = ?",
            "updated_at = ?",
        ]
        values = [
            payload["status"],
            payload["start_at"],
            payload["bookie"],
            payload["promo_name"],
            payload["deposit_amount"],
            payload["q_result_at"],
            payload["q_event"],
            payload["q_type"],
            payload["q_amount"],
            payload["q_target"],
            payload["q_exchange"],
            payload["q_is_placed"],
            payload["q_is_completed"],
            payload["b_result_at"],
            payload["b_event"],
            payload["b_type"],
            payload["b_amount"],
            payload["b_target"],
            payload["b_exchange"],
            payload["b_is_placed"],
            payload["b_is_completed"],
            payload["profit"],
            payload["bank"],
            payload["notes"],
            payload["updated_at"],
            record_id,
        ]
        with self.conn:
            self.conn.execute(
                f"UPDATE betting_records SET {', '.join(assignments)} WHERE id = ?",  # noqa: S608
                values,
            )

    def delete_betting_records(self, record_ids: list[str]) -> None:
        if not record_ids:
            return
        holders = ", ".join(["?"] * len(record_ids))
        with self.conn:
            self.conn.execute(f"DELETE FROM betting_records WHERE id IN ({holders})", record_ids)  # noqa: S608

    def snapshot_betting_records(self) -> list[dict[str, str]]:
        rows = self.conn.execute("SELECT * FROM betting_records ORDER BY created_at, id").fetchall()
        return [self._row_to_betting_record(row, include_meta=True) for row in rows]

    def replace_betting_records(self, records: Iterable[dict[str, Any]]) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM betting_records")
            for record in records:
                payload = self._normalize_betting_payload(record)
                payload["created_at"] = _as_text(record.get("created_at")) or _now_text()
                payload["updated_at"] = _as_text(record.get("updated_at")) or _now_text()
                cols = ", ".join(BETTING_DB_COLUMNS)
                holders = ", ".join(["?"] * len(BETTING_DB_COLUMNS))
                values = [payload[column] for column in BETTING_DB_COLUMNS]
                self.conn.execute(f"INSERT INTO betting_records ({cols}) VALUES ({holders})", values)  # noqa: S608

    def load_casino_records(self) -> list[dict[str, str]]:
        rows = self.conn.execute("SELECT * FROM casino_records ORDER BY created_at, id").fetchall()
        out: list[dict[str, str]] = []
        for row in rows:
            out.append(
                {
                    "id": _as_text(row["id"]),
                    "status": _as_text(row["status"]),
                    "bookie": _as_text(row["bookie"]),
                    "promo_start_date": _as_text(row["promo_start_date"]),
                    "promo_name": _as_text(row["promo_name"]),
                    "deposit_amount": _as_text(row["deposit_amount"]),
                    "final_amount": _as_text(row["final_amount"]),
                    "bank_status": _as_text(row["bank_status"]),
                    "profit": _as_text(row["profit"]),
                    "notes": _as_text(row["notes"]),
                }
            )
        return out

    def fetch_casino_records(
        self,
        *,
        search: str = "",
        status: str = "Any",
        bank_status: str = "Any",
        sort_field: str = "promo_start_date",
        ascending: bool = True,
    ) -> list[dict[str, str]]:
        where: list[str] = ["1=1"]
        params: list[Any] = []

        if status and status != "Any":
            where.append("status = ?")
            params.append(status)

        if bank_status and bank_status != "Any":
            where.append("bank_status = ?")
            params.append(bank_status)

        term = _as_text(search)
        if term:
            like = f"%{term}%"
            where.append("(bookie LIKE ? OR promo_name LIKE ?)")
            params.extend([like, like])

        order_sql = self._casino_order_sql(sort_field, ascending)
        query = f"SELECT * FROM casino_records WHERE {' AND '.join(where)} {order_sql}"  # noqa: S608
        rows = self.conn.execute(query, params).fetchall()
        return [self._row_to_casino_record(row) for row in rows]

    def list_casino_bookies(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT DISTINCT bookie FROM casino_records WHERE TRIM(bookie) != '' ORDER BY LOWER(bookie)"
        ).fetchall()
        return [str(row[0]) for row in rows]

    def get_casino_record(self, record_id: str) -> dict[str, str] | None:
        row = self.conn.execute("SELECT * FROM casino_records WHERE id = ?", (record_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_casino_record(row)

    def insert_casino_record(self, record: dict[str, Any]) -> None:
        payload = self._normalize_casino_payload(record)
        now = _now_text()
        payload["created_at"] = _as_text(record.get("created_at")) or now
        payload["updated_at"] = _as_text(record.get("updated_at")) or now

        cols = ", ".join(CASINO_DB_COLUMNS)
        holders = ", ".join(["?"] * len(CASINO_DB_COLUMNS))
        values = [payload[column] for column in CASINO_DB_COLUMNS]
        with self.conn:
            self.conn.execute(f"INSERT INTO casino_records ({cols}) VALUES ({holders})", values)  # noqa: S608

    def update_casino_record(self, record_id: str, record: dict[str, Any]) -> None:
        payload = self._normalize_casino_payload(record)
        payload["updated_at"] = _now_text()

        assignments = [
            "status = ?",
            "bookie = ?",
            "promo_start_date = ?",
            "promo_name = ?",
            "deposit_amount = ?",
            "final_amount = ?",
            "bank_status = ?",
            "profit = ?",
            "notes = ?",
            "updated_at = ?",
        ]
        values = [
            payload["status"],
            payload["bookie"],
            payload["promo_start_date"],
            payload["promo_name"],
            payload["deposit_amount"],
            payload["final_amount"],
            payload["bank_status"],
            payload["profit"],
            payload["notes"],
            payload["updated_at"],
            record_id,
        ]
        with self.conn:
            self.conn.execute(
                f"UPDATE casino_records SET {', '.join(assignments)} WHERE id = ?",  # noqa: S608
                values,
            )

    def delete_casino_records(self, record_ids: list[str]) -> None:
        if not record_ids:
            return
        holders = ", ".join(["?"] * len(record_ids))
        with self.conn:
            self.conn.execute(f"DELETE FROM casino_records WHERE id IN ({holders})", record_ids)  # noqa: S608

    def snapshot_casino_records(self) -> list[dict[str, str]]:
        rows = self.conn.execute("SELECT * FROM casino_records ORDER BY created_at, id").fetchall()
        return [self._row_to_casino_record(row, include_meta=True) for row in rows]

    def replace_casino_records(self, records: Iterable[dict[str, Any]]) -> None:
        with self.conn:
            self.conn.execute("DELETE FROM casino_records")
            for record in records:
                payload = self._normalize_casino_payload(record)
                payload["created_at"] = _as_text(record.get("created_at")) or _now_text()
                payload["updated_at"] = _as_text(record.get("updated_at")) or _now_text()
                cols = ", ".join(CASINO_DB_COLUMNS)
                holders = ", ".join(["?"] * len(CASINO_DB_COLUMNS))
                values = [payload[column] for column in CASINO_DB_COLUMNS]
                self.conn.execute(f"INSERT INTO casino_records ({cols}) VALUES ({holders})", values)  # noqa: S608

    def save_casino_records(self, records: Iterable[dict[str, str]]) -> None:
        now = _now_text()
        with self.conn:
            self.conn.execute("DELETE FROM casino_records")
            for record in records:
                payload = {
                    "id": _as_text(record.get("id")),
                    "status": _as_text(record.get("status")) or "NotStarted",
                    "bookie": _as_text(record.get("bookie")),
                    "promo_start_date": _as_text(record.get("promo_start_date")),
                    "promo_name": _as_text(record.get("promo_name")),
                    "deposit_amount": _as_text(record.get("deposit_amount")),
                    "final_amount": _as_text(record.get("final_amount")),
                    "bank_status": _as_text(record.get("bank_status")) or "Unconfirmed",
                    "profit": _as_text(record.get("profit")),
                    "notes": _as_text(record.get("notes")),
                    "created_at": _as_text(record.get("created_at")) or now,
                    "updated_at": now,
                }
                cols = ", ".join(CASINO_DB_COLUMNS)
                holders = ", ".join(["?"] * len(CASINO_DB_COLUMNS))
                values = [payload[column] for column in CASINO_DB_COLUMNS]
                self.conn.execute(f"INSERT INTO casino_records ({cols}) VALUES ({holders})", values)  # noqa: S608

    def fetch_reload_offer_templates(self) -> list[dict[str, str]]:
        rows = self.conn.execute(
            "SELECT * FROM reload_offer_templates ORDER BY LOWER(bookie), LOWER(promo_name), created_at"
        ).fetchall()
        return [self._row_to_reload_offer_template(row, include_meta=True) for row in rows]

    def replace_reload_offer_templates(self, templates: Iterable[dict[str, Any]]) -> None:
        normalized = [self._normalize_reload_offer_template_payload(template) for template in templates]
        now = _now_text()
        with self.conn:
            self.conn.execute("DELETE FROM reload_offer_templates")
            for template in normalized:
                template["created_at"] = _as_text(template.get("created_at")) or now
                template["updated_at"] = _as_text(template.get("updated_at")) or now
                cols = ", ".join(RELOAD_TEMPLATE_COLUMNS)
                holders = ", ".join(["?"] * len(RELOAD_TEMPLATE_COLUMNS))
                values = [template[column] for column in RELOAD_TEMPLATE_COLUMNS]
                self.conn.execute(f"INSERT INTO reload_offer_templates ({cols}) VALUES ({holders})", values)  # noqa: S608

    def refresh_reload_offer_instances(self, window_start: str, window_end: str) -> None:
        start_date = self._require_iso_date(window_start, "window_start")
        end_date = self._require_iso_date(window_end, "window_end")
        if end_date < start_date:
            raise ValueError("window_end must be on or after window_start")

        templates = self.fetch_reload_offer_templates()
        with self.conn:
            self.conn.execute(
                "DELETE FROM reload_offer_instances WHERE scheduled_date < ? OR scheduled_date > ?",
                (window_start, window_end),
            )

            valid_template_ids = {template["id"] for template in templates}
            if valid_template_ids:
                holders = ", ".join(["?"] * len(valid_template_ids))
                self.conn.execute(
                    f"DELETE FROM reload_offer_instances WHERE template_id NOT IN ({holders})",  # noqa: S608
                    list(valid_template_ids),
                )
            else:
                self.conn.execute("DELETE FROM reload_offer_instances")
                return

            for template in templates:
                template_id = template["id"]
                scheduled_dates = set(self._generate_template_dates(template, start_date, end_date))
                if not scheduled_dates:
                    self.conn.execute(
                        "DELETE FROM reload_offer_instances WHERE template_id = ? AND scheduled_date BETWEEN ? AND ? AND TRIM(betting_record_id) = ''",
                        (template_id, window_start, window_end),
                    )
                    continue

                existing_rows = self.conn.execute(
                    "SELECT id, scheduled_date, betting_record_id FROM reload_offer_instances WHERE template_id = ? AND scheduled_date BETWEEN ? AND ?",
                    (template_id, window_start, window_end),
                ).fetchall()
                existing_by_date = {str(row["scheduled_date"]): row for row in existing_rows}

                for scheduled_date in sorted(scheduled_dates):
                    existing = existing_by_date.get(scheduled_date)
                    payload = self._build_reload_offer_instance_payload(template, scheduled_date)
                    if existing is None:
                        cols = ", ".join(RELOAD_INSTANCE_COLUMNS)
                        holders = ", ".join(["?"] * len(RELOAD_INSTANCE_COLUMNS))
                        values = [payload[column] for column in RELOAD_INSTANCE_COLUMNS]
                        self.conn.execute(
                            f"INSERT INTO reload_offer_instances ({cols}) VALUES ({holders})",  # noqa: S608
                            values,
                        )
                        continue

                    if _as_text(existing["betting_record_id"]):
                        continue

                    assignments = [
                        "start_at = ?",
                        "bookie = ?",
                        "promo_name = ?",
                        "deposit_amount = ?",
                        "bet_amount = ?",
                        "bet_type = ?",
                        "bonus_amount = ?",
                        "bonus_type = ?",
                        "notes = ?",
                        "updated_at = ?",
                    ]
                    values = [
                        payload["start_at"],
                        payload["bookie"],
                        payload["promo_name"],
                        payload["deposit_amount"],
                        payload["bet_amount"],
                        payload["bet_type"],
                        payload["bonus_amount"],
                        payload["bonus_type"],
                        payload["notes"],
                        payload["updated_at"],
                        str(existing["id"]),
                    ]
                    self.conn.execute(
                        f"UPDATE reload_offer_instances SET {', '.join(assignments)} WHERE id = ?",  # noqa: S608
                        values,
                    )

                removable_dates = [
                    str(row["scheduled_date"])
                    for row in existing_rows
                    if str(row["scheduled_date"]) not in scheduled_dates and not _as_text(row["betting_record_id"])
                ]
                if removable_dates:
                    holders = ", ".join(["?"] * len(removable_dates))
                    self.conn.execute(
                        f"DELETE FROM reload_offer_instances WHERE template_id = ? AND scheduled_date IN ({holders}) AND TRIM(betting_record_id) = ''",  # noqa: S608
                        [template_id, *removable_dates],
                    )

    def fetch_reload_offer_instances_for_date(self, scheduled_date: str) -> list[dict[str, str]]:
        self._require_iso_date(scheduled_date, "scheduled_date")
        rows = self.conn.execute(
            "SELECT * FROM reload_offer_instances WHERE scheduled_date = ? ORDER BY start_at, LOWER(bookie), LOWER(promo_name)",
            (scheduled_date,),
        ).fetchall()
        return [self._row_to_reload_offer_instance(row) for row in rows]

    def set_reload_offer_instance_betting_record(self, instance_id: str, betting_record_id: str) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE reload_offer_instances SET betting_record_id = ?, updated_at = ? WHERE id = ?",
                (_as_text(betting_record_id), _now_text(), _as_text(instance_id)),
            )

    def find_reload_offer_instance_by_betting_record(self, betting_record_id: str) -> dict[str, str] | None:
        row = self.conn.execute(
            "SELECT * FROM reload_offer_instances WHERE betting_record_id = ? LIMIT 1",
            (_as_text(betting_record_id),),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_reload_offer_instance(row)

    def _normalize_reload_offer_template_payload(self, template: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "id": _as_text(template.get("id")),
            "enabled": _as_bool(template.get("enabled", 1)),
            "start_at": _as_text(template.get("start_at")),
            "bookie": _as_text(template.get("bookie")),
            "promo_name": _as_text(template.get("promo_name")),
            "repeat_mode": _as_text(template.get("repeat_mode")) or "weekly",
            "repeat_weekday": int(_as_text(template.get("repeat_weekday")) or "0"),
            "repeat_monthday": int(_as_text(template.get("repeat_monthday")) or "1"),
            "deposit_amount": _as_float_or_none(template.get("deposit_amount")),
            "bet_amount": _as_float_or_none(template.get("bet_amount")),
            "bet_type": _as_text(template.get("bet_type")),
            "bonus_amount": _as_float_or_none(template.get("bonus_amount")),
            "bonus_type": _as_text(template.get("bonus_type")),
            "notes": _as_text(template.get("notes")),
            "created_at": _as_text(template.get("created_at")),
            "updated_at": _as_text(template.get("updated_at")),
        }

        if not payload["id"]:
            raise ValueError("Reload offer template id is required")
        if not payload["start_at"]:
            raise ValueError("Reload offer template start_at is required")
        try:
            datetime.strptime(payload["start_at"], "%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise ValueError("Reload offer template start_at must match yyyy-MM-dd HH:mm") from exc
        if payload["repeat_mode"] not in _RELOAD_REPEAT_MODES:
            payload["repeat_mode"] = "weekly"
        payload["repeat_weekday"] = max(0, min(6, int(payload["repeat_weekday"])))
        payload["repeat_monthday"] = max(1, min(31, int(payload["repeat_monthday"])))
        if payload["bet_type"] not in BETTING_Q_TYPES:
            payload["bet_type"] = ""
        if payload["bonus_type"] not in BETTING_B_TYPES:
            payload["bonus_type"] = ""
        return payload

    def _row_to_reload_offer_template(self, row: sqlite3.Row, include_meta: bool = False) -> dict[str, str]:
        record = {
            "id": _as_text(row["id"]),
            "enabled": "Yes" if int(row["enabled"] or 0) else "No",
            "start_at": _as_text(row["start_at"]),
            "bookie": _as_text(row["bookie"]),
            "promo_name": _as_text(row["promo_name"]),
            "repeat_mode": _as_text(row["repeat_mode"]),
            "repeat_weekday": _as_text(row["repeat_weekday"]),
            "repeat_monthday": _as_text(row["repeat_monthday"]),
            "deposit_amount": self._decimal_to_text(row["deposit_amount"]),
            "bet_amount": self._decimal_to_text(row["bet_amount"]),
            "bet_type": _as_text(row["bet_type"]),
            "bonus_amount": self._decimal_to_text(row["bonus_amount"]),
            "bonus_type": _as_text(row["bonus_type"]),
            "notes": _as_text(row["notes"]),
        }
        if include_meta:
            record["created_at"] = _as_text(row["created_at"])
            record["updated_at"] = _as_text(row["updated_at"])
        return record

    def _row_to_reload_offer_instance(self, row: sqlite3.Row) -> dict[str, str]:
        betting_record_id = _as_text(row["betting_record_id"])
        betting_record = self.get_betting_record(betting_record_id) if betting_record_id else None
        if betting_record_id and betting_record is None:
            status = "Not started"
            betting_record_id = ""
        else:
            betting_status = betting_record.get("status", "NotStarted") if betting_record is not None else "NotStarted"
            status = {
                "NotStarted": "Record created",
                "NeedQBet": "Ready for bet",
                "WaitQResult": "Waiting bet result",
                "NeedBBet": "Ready for bonus",
                "WaitBResult": "Waiting bonus result",
                "NeedBank": "Ready for bank",
                "Done": "Completed",
                "Error": "Error",
            }.get(betting_status, "Record created") if betting_record_id else "Not started"

        return {
            "id": _as_text(row["id"]),
            "template_id": _as_text(row["template_id"]),
            "scheduled_date": _as_text(row["scheduled_date"]),
            "start_at": _as_text(row["start_at"]),
            "bookie": _as_text(row["bookie"]),
            "promo_name": _as_text(row["promo_name"]),
            "deposit_amount": self._decimal_to_text(row["deposit_amount"]),
            "bet_amount": self._decimal_to_text(row["bet_amount"]),
            "bet_type": _as_text(row["bet_type"]),
            "bonus_amount": self._decimal_to_text(row["bonus_amount"]),
            "bonus_type": _as_text(row["bonus_type"]),
            "notes": _as_text(row["notes"]),
            "betting_record_id": betting_record_id,
            "status": status,
        }

    def _require_iso_date(self, value: str, field_name: str) -> date:
        try:
            return datetime.strptime(_as_text(value), "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(f"{field_name} must match YYYY-MM-DD") from exc

    def _generate_template_dates(self, template: dict[str, str], start_date: date, end_date: date) -> list[str]:
        if template.get("enabled") != "Yes":
            return []
        start_at_text = template.get("start_at", "")
        anchor = datetime.strptime(start_at_text, "%Y-%m-%d %H:%M").date()
        effective_start = max(start_date, anchor)
        repeat_mode = template.get("repeat_mode", "weekly")

        if repeat_mode == "weekly":
            weekday = int(template.get("repeat_weekday", "0") or "0")
            delta = (weekday - effective_start.weekday()) % 7
            current = effective_start + timedelta(days=delta)
            if current < anchor:
                current += timedelta(days=7)
            dates: list[str] = []
            while current <= end_date:
                dates.append(current.strftime("%Y-%m-%d"))
                current += timedelta(days=7)
            return dates

        monthday = int(template.get("repeat_monthday", "1") or "1")
        current_year = effective_start.year
        current_month = effective_start.month
        dates = []
        while True:
            candidate_day = min(monthday, monthrange(current_year, current_month)[1])
            candidate = date(current_year, current_month, candidate_day)
            if candidate >= effective_start and candidate >= anchor:
                if candidate > end_date:
                    break
                dates.append(candidate.strftime("%Y-%m-%d"))
            if current_year > end_date.year or (current_year == end_date.year and current_month >= end_date.month):
                if candidate > end_date:
                    break
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1
        return dates

    def _build_reload_offer_instance_payload(self, template: dict[str, str], scheduled_date: str) -> dict[str, Any]:
        start_at = template.get("start_at", "")
        start_time = datetime.strptime(start_at, "%Y-%m-%d %H:%M").strftime("%H:%M")
        combined_start = f"{scheduled_date} {start_time}"
        now = _now_text()
        return {
            "id": new_id(),
            "template_id": template.get("id", ""),
            "scheduled_date": scheduled_date,
            "start_at": combined_start,
            "bookie": template.get("bookie", ""),
            "promo_name": template.get("promo_name", ""),
            "deposit_amount": _as_float_or_none(template.get("deposit_amount")),
            "bet_amount": _as_float_or_none(template.get("bet_amount")),
            "bet_type": template.get("bet_type", ""),
            "bonus_amount": _as_float_or_none(template.get("bonus_amount")),
            "bonus_type": template.get("bonus_type", ""),
            "notes": template.get("notes", ""),
            "betting_record_id": "",
            "created_at": now,
            "updated_at": now,
        }

    def create_betting_record_from_reload_offer(self, instance_id: str) -> str:
        row = self.conn.execute("SELECT * FROM reload_offer_instances WHERE id = ?", (_as_text(instance_id),)).fetchone()
        if row is None:
            raise ValueError("Reload offer instance not found")

        instance = self._row_to_reload_offer_instance(row)
        existing_id = instance.get("betting_record_id", "")
        if existing_id and self.get_betting_record(existing_id) is not None:
            return existing_id

        record_id = new_id()
        betting_record = {
            "id": record_id,
            "status": "NotStarted",
            "start_at": instance.get("start_at", ""),
            "bookie": instance.get("bookie", ""),
            "promo_name": instance.get("promo_name", ""),
            "deposit_amount": instance.get("deposit_amount", ""),
            "q_result_at": "",
            "q_event": "",
            "q_type": instance.get("bet_type", ""),
            "q_amount": instance.get("bet_amount", ""),
            "q_target": "",
            "q_exchange": "",
            "q_is_placed": "No",
            "q_is_completed": "No",
            "b_result_at": "",
            "b_event": "",
            "b_type": instance.get("bonus_type", ""),
            "b_amount": instance.get("bonus_amount", ""),
            "b_target": "",
            "b_exchange": "",
            "b_is_placed": "No",
            "b_is_completed": "No",
            "profit": "",
            "bank": "Uncon",
            "notes": instance.get("notes", ""),
        }
        self.insert_betting_record(betting_record)
        self.set_reload_offer_instance_betting_record(instance_id, record_id)
        return record_id

    def _normalize_casino_payload(self, record: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}

        for field in CASINO_TEXT_FIELDS:
            payload[field] = _as_text(record.get(field))

        if payload["status"] not in CASINO_STATUS_VALUES:
            payload["status"] = CASINO_STATUS_VALUES[0]
        if payload["bank_status"] not in CASINO_BANK_STATUS_VALUES:
            payload["bank_status"] = CASINO_BANK_STATUS_VALUES[0]

        payload["id"] = _as_text(record.get("id"))
        if not payload["id"]:
            raise ValueError("Casino record id is required")

        return payload

    def _row_to_casino_record(self, row: sqlite3.Row, include_meta: bool = False) -> dict[str, str]:
        record = {
            "id": _as_text(row["id"]),
            "status": _as_text(row["status"]),
            "bookie": _as_text(row["bookie"]),
            "promo_start_date": _as_text(row["promo_start_date"]),
            "promo_name": _as_text(row["promo_name"]),
            "deposit_amount": _as_text(row["deposit_amount"]),
            "final_amount": _as_text(row["final_amount"]),
            "bank_status": _as_text(row["bank_status"]),
            "profit": _as_text(row["profit"]),
            "notes": _as_text(row["notes"]),
        }
        if include_meta:
            record["created_at"] = _as_text(row["created_at"])
            record["updated_at"] = _as_text(row["updated_at"])
        return record

    def _casino_order_sql(self, sort_field: str, ascending: bool) -> str:
        direction = "ASC" if ascending else "DESC"
        allowed = {
            "bookie": "bookie",
            "promo_start_date": "promo_start_date",
            "promo_name": "promo_name",
            "deposit_amount": "CAST(deposit_amount AS REAL)",
            "final_amount": "CAST(final_amount AS REAL)",
            "bank_status": "bank_status",
            "profit": "CAST(profit AS REAL)",
            "notes": "notes",
        }

        if sort_field == "status":
            parts = [f"WHEN '{status}' THEN {index}" for status, index in CASINO_STATUS_ORDER.items()]
            status_case = "CASE status " + " ".join(parts) + " ELSE 999 END"
            return f"ORDER BY {status_case} {direction}, promo_start_date DESC, created_at DESC"

        if sort_field == "promo_start_date":
            return (
                "ORDER BY "
                "CASE WHEN TRIM(promo_start_date) = '' THEN 1 ELSE 0 END, "
                f"substr(promo_start_date, 7, 2) {direction}, "
                f"substr(promo_start_date, 4, 2) {direction}, "
                f"substr(promo_start_date, 1, 2) {direction}, "
                "created_at DESC"
            )

        column = allowed.get(sort_field, "promo_start_date")
        if sort_field in {"deposit_amount", "final_amount", "profit"}:
            raw_field = sort_field
            return (
                "ORDER BY "
                f"CASE WHEN TRIM({raw_field}) = '' THEN 1 ELSE 0 END, "
                f"{column} {direction}, created_at DESC"
            )

        if column in {"bookie", "promo_name", "bank_status", "notes"}:
            return f"ORDER BY LOWER({column}) {direction}, created_at DESC"

        return f"ORDER BY {column} {direction}, created_at DESC"

    def _normalize_betting_payload(self, record: dict[str, Any]) -> dict[str, Any]:
        payload: dict[str, Any] = {}

        for field in BETTING_TEXT_FIELDS:
            payload[field] = _as_text(record.get(field))

        for field in BETTING_NUMERIC_FIELDS:
            payload[field] = _as_float_or_none(record.get(field))

        for field in BETTING_BOOL_FIELDS:
            payload[field] = _as_bool(record.get(field))

        if payload["status"] not in BETTING_STATUS_VALUES:
            payload["status"] = BETTING_STATUS_VALUES[0]
        if payload["q_type"] not in BETTING_Q_TYPES:
            payload["q_type"] = ""
        if payload["b_type"] not in BETTING_B_TYPES:
            payload["b_type"] = ""
        if payload["q_exchange"] not in BETTING_Q_EXCHANGES:
            payload["q_exchange"] = ""
        if payload["b_exchange"] not in BETTING_B_EXCHANGES:
            payload["b_exchange"] = ""
        if payload["bank"] not in BETTING_BANK_VALUES:
            payload["bank"] = BETTING_BANK_VALUES[0]

        payload["id"] = _as_text(record.get("id"))
        if not payload["id"]:
            raise ValueError("Betting record id is required")

        return payload

    def _row_to_betting_record(self, row: sqlite3.Row, include_meta: bool = False) -> dict[str, str]:
        record = {
            "id": _as_text(row["id"]),
            "status": _as_text(row["status"]),
            "start_at": _as_text(row["start_at"]),
            "bookie": _as_text(row["bookie"]),
            "promo_name": _as_text(row["promo_name"]),
            "deposit_amount": self._decimal_to_text(row["deposit_amount"]),
            "q_result_at": _as_text(row["q_result_at"]),
            "q_event": _as_text(row["q_event"]),
            "q_type": _as_text(row["q_type"]),
            "q_amount": self._decimal_to_text(row["q_amount"]),
            "q_target": _as_text(row["q_target"]),
            "q_exchange": _as_text(row["q_exchange"]),
            "q_is_placed": "Yes" if int(row["q_is_placed"] or 0) else "No",
            "q_is_completed": "Yes" if int(row["q_is_completed"] or 0) else "No",
            "b_result_at": _as_text(row["b_result_at"]),
            "b_event": _as_text(row["b_event"]),
            "b_type": _as_text(row["b_type"]),
            "b_amount": self._decimal_to_text(row["b_amount"]),
            "b_target": _as_text(row["b_target"]),
            "b_exchange": _as_text(row["b_exchange"]),
            "b_is_placed": "Yes" if int(row["b_is_placed"] or 0) else "No",
            "b_is_completed": "Yes" if int(row["b_is_completed"] or 0) else "No",
            "profit": self._decimal_to_text(row["profit"]),
            "bank": _as_text(row["bank"]),
            "notes": _as_text(row["notes"]),
        }
        if include_meta:
            record["created_at"] = _as_text(row["created_at"])
            record["updated_at"] = _as_text(row["updated_at"])
        return record

    def _betting_order_sql(self, sort_field: str, ascending: bool) -> str:
        direction = "ASC" if ascending else "DESC"
        allowed = {
            "start_at": "start_at",
            "bookie": "bookie",
            "promo_name": "promo_name",
            "deposit_amount": "deposit_amount",
            "q_result_at": "q_result_at",
            "q_event": "q_event",
            "q_type": "q_type",
            "q_amount": "q_amount",
            "q_target": "q_target",
            "q_exchange": "q_exchange",
            "q_is_placed": "q_is_placed",
            "q_is_completed": "q_is_completed",
            "b_result_at": "b_result_at",
            "b_event": "b_event",
            "b_type": "b_type",
            "b_amount": "b_amount",
            "b_target": "b_target",
            "b_exchange": "b_exchange",
            "b_is_placed": "b_is_placed",
            "b_is_completed": "b_is_completed",
            "profit": "profit",
            "bank": "bank",
            "notes": "notes",
        }

        if sort_field == "status":
            parts = [f"WHEN '{status}' THEN {index}" for index, status in enumerate(BETTING_STATUS_VALUES)]
            status_case = "CASE status " + " ".join(parts) + " ELSE 999 END"
            return f"ORDER BY {status_case} {direction}, start_at DESC, created_at DESC"

        column = allowed.get(sort_field, "start_at")
        if column in {"deposit_amount", "q_amount", "b_amount", "profit"}:
            return (
                f"ORDER BY CASE WHEN {column} IS NULL THEN 1 ELSE 0 END, "
                f"{column} {direction}, created_at DESC"
            )
        return f"ORDER BY {column} {direction}, created_at DESC"

    def _decimal_to_text(self, value: Any) -> str:
        if value is None:
            return ""
        return fmt_decimal(Decimal(str(value)))


class CsvStore:
    """Compatibility layer used by Casino tab while data is stored in SQLite."""

    def __init__(self, path: Path, fieldnames: list[str]):
        self.path = path
        self.fieldnames = fieldnames
        self.db = AppDatabase(path.parent)

    def ensure_exists(self) -> None:
        # Table creation happens in AppDatabase initialization.
        return

    def load(self) -> list[dict[str, str]]:
        if self.path.stem == "casino":
            return self.db.load_casino_records()
        raise ValueError("CsvStore compatibility wrapper currently supports casino only")

    def save(self, records: Iterable[dict[str, str]]) -> None:
        if self.path.stem == "casino":
            self.db.save_casino_records(records)
            return
        raise ValueError("CsvStore compatibility wrapper currently supports casino only")
