from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.constants import (
    BETTING_B_EXCHANGES,
    BETTING_B_TYPES,
    BETTING_BANK_VALUES,
    BETTING_Q_EXCHANGES,
    BETTING_Q_TYPES,
    BETTING_STATUS_VALUES,
)
from app.storage import AppDatabase, CASINO_BANK_STATUS_VALUES, CASINO_STATUS_VALUES


def _fmt_dt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M")


def _fmt_dmy(day: date) -> str:
    return day.strftime("%d/%m/%y")


def _pick(values: list[str], idx: int) -> str:
    return values[idx % len(values)]


def _build_betting_records(size: int = 100) -> list[dict[str, str]]:
    base = datetime(2025, 1, 1, 9, 0)
    out: list[dict[str, str]] = []
    for i in range(size):
        at = base + timedelta(hours=i * 6)
        out.append(
            {
                "id": f"bet-sample-{i:03d}",
                "status": _pick(BETTING_STATUS_VALUES, i),
                "start_at": _fmt_dt(at),
                "bookie": f"Bookie-{i % 12}",
                "promo_name": f"Bet Promo {i % 20}",
                "deposit_amount": "" if i % 11 == 0 else f"{20 + i * 1.2:.2f}",
                "q_result_at": "" if i % 3 else _fmt_dt(at + timedelta(hours=3)),
                "q_event": "" if i % 5 else f"Q-Event-{i}",
                "q_type": _pick(BETTING_Q_TYPES, i),
                "q_amount": "" if i % 4 == 0 else f"{10 + i * 0.9:.2f}",
                "q_target": "" if i % 6 else f"https://example.com/q/{i}",
                "q_exchange": _pick(BETTING_Q_EXCHANGES, i),
                "q_is_placed": "Yes" if i % 2 else "No",
                "q_is_completed": "Yes" if i % 3 == 0 else "No",
                "b_result_at": "" if i % 4 else _fmt_dt(at + timedelta(hours=18)),
                "b_event": "" if i % 7 else f"B-Event-{i}",
                "b_type": _pick(BETTING_B_TYPES, i + 3),
                "b_amount": "" if i % 5 == 0 else f"{9 + i * 0.8:.2f}",
                "b_target": "" if i % 8 else f"https://example.com/b/{i}",
                "b_exchange": _pick(BETTING_B_EXCHANGES, i + 2),
                "b_is_placed": "Yes" if i % 4 else "No",
                "b_is_completed": "Yes" if i % 5 == 0 else "No",
                "profit": "" if i % 9 == 0 else f"{-5 + i * 0.6:.2f}",
                "bank": _pick(BETTING_BANK_VALUES, i),
                "notes": f"sample betting note {i}",
            }
        )
    return out


def _build_casino_records(size: int = 100) -> list[dict[str, str]]:
    start = date(2025, 1, 1)
    out: list[dict[str, str]] = []
    for i in range(size):
        day = start + timedelta(days=i)
        deposit = "" if i % 10 == 0 else f"{15 + i * 1.1:.2f}"
        final = "" if i % 4 else f"{18 + i * 1.25:.2f}"
        out.append(
            {
                "id": f"cas-sample-{i:03d}",
                "status": _pick(CASINO_STATUS_VALUES, i),
                "bookie": f"Casino-{i % 10}",
                "promo_start_date": _fmt_dmy(day),
                "promo_name": f"Casino Promo {i % 18}",
                "deposit_amount": deposit,
                "final_amount": final,
                "bank_status": _pick(CASINO_BANK_STATUS_VALUES, i),
                "profit": "" if not deposit or not final else f"{float(final) - float(deposit):.2f}",
                "notes": f"sample casino note {i}",
            }
        )
    return out


def _build_reload_betting_templates(size: int = 12) -> list[dict[str, str]]:
    base = datetime(2025, 1, 1, 8, 30)
    out: list[dict[str, str]] = []
    for i in range(size):
        at = base + timedelta(days=i * 3)
        out.append(
            {
                "id": f"rbt-sample-{i:03d}",
                "enabled": "Yes" if i % 5 else "No",
                "start_at": _fmt_dt(at),
                "bookie": f"RBet-{i % 6}",
                "promo_name": f"Reload Bet Promo {i}",
                "repeat_mode": "weekly" if i % 2 == 0 else "monthly",
                "repeat_weekday": str(i % 7),
                "repeat_monthday": str((i % 28) + 1),
                "deposit_amount": "" if i % 4 == 0 else f"{25 + i * 3.0:.2f}",
                "bet_amount": "" if i % 3 == 0 else f"{12 + i * 1.7:.2f}",
                "bet_type": _pick(BETTING_Q_TYPES, i + 1),
                "bonus_amount": "" if i % 3 else f"{5 + i * 1.2:.2f}",
                "bonus_type": _pick(BETTING_B_TYPES, i + 2),
                "notes": f"reload betting template {i}",
            }
        )
    return out


def _build_reload_casino_templates(size: int = 10) -> list[dict[str, str]]:
    base = datetime(2025, 1, 2, 10, 0)
    out: list[dict[str, str]] = []
    for i in range(size):
        at = base + timedelta(days=i * 4)
        out.append(
            {
                "id": f"rct-sample-{i:03d}",
                "enabled": "Yes" if i % 4 else "No",
                "start_at": _fmt_dt(at),
                "bookie": f"RCas-{i % 5}",
                "promo_name": f"Reload Casino Promo {i}",
                "repeat_mode": "weekly" if i % 3 else "monthly",
                "repeat_weekday": str((i + 1) % 7),
                "repeat_monthday": str((i % 27) + 1),
                "deposit_amount": "" if i % 3 == 0 else f"{20 + i * 2.5:.2f}",
                "notes": f"reload casino template {i}",
            }
        )
    return out


def _link_instances(db: AppDatabase, max_links: int = 20) -> None:
    b_ids = [
        str(row[0])
        for row in db.conn.execute(
            "SELECT id FROM reload_betting_offer_instances WHERE TRIM(betting_record_id) = '' ORDER BY id LIMIT ?",
            (max_links,),
        ).fetchall()
    ]
    for instance_id in b_ids:
        db.create_betting_record_from_reload_betting_offer(instance_id)

    c_ids = [
        str(row[0])
        for row in db.conn.execute(
            "SELECT id FROM reload_casino_offer_instances WHERE TRIM(casino_record_id) = '' ORDER BY id LIMIT ?",
            (max_links,),
        ).fetchall()
    ]
    for instance_id in c_ids:
        db.create_casino_record_from_reload_casino_offer(instance_id)


def generate_small_db() -> Path:
    target_dir = Path(__file__).resolve().parent / "fixtures" / "sample_usage"
    target_dir.mkdir(parents=True, exist_ok=True)
    db_path = target_dir / "mbmanager.db"
    if db_path.exists():
        db_path.unlink()

    db = AppDatabase(target_dir)
    try:
        db.replace_betting_records(_build_betting_records(80))
        db.replace_casino_records(_build_casino_records(80))
        db.replace_reload_betting_offer_templates(_build_reload_betting_templates(12))
        db.replace_reload_casino_offer_templates(_build_reload_casino_templates(10))

        db.refresh_reload_betting_offer_instances("2025-01-01", "2026-12-31")
        db.refresh_reload_casino_offer_instances("2025-01-01", "2026-12-31")
        _link_instances(db, max_links=20)

        print("Small test database generated:")
        print(f"- path: {db_path}")
        print(f"- betting_records: {db.conn.execute('SELECT COUNT(*) FROM betting_records').fetchone()[0]}")
        print(f"- casino_records: {db.conn.execute('SELECT COUNT(*) FROM casino_records').fetchone()[0]}")
        print(f"- reload_betting_offer_templates: {db.conn.execute('SELECT COUNT(*) FROM reload_betting_offer_templates').fetchone()[0]}")
        print(f"- reload_casino_offer_templates: {db.conn.execute('SELECT COUNT(*) FROM reload_casino_offer_templates').fetchone()[0]}")
        print(f"- reload_betting_offer_instances: {db.conn.execute('SELECT COUNT(*) FROM reload_betting_offer_instances').fetchone()[0]}")
        print(f"- reload_casino_offer_instances: {db.conn.execute('SELECT COUNT(*) FROM reload_casino_offer_instances').fetchone()[0]}")
    finally:
        db.close()

    return db_path


if __name__ == "__main__":
    generate_small_db()
