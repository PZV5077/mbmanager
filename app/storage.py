from __future__ import annotations

import sqlite3
from datetime import datetime
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
from .utils import CASINO_STATUS_ORDER, fmt_decimal, parse_date, parse_decimal

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

    def close(self) -> None:
        self.conn.close()

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
