from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import uuid4

DATE_FMT = "%d/%m/%y"


def new_id() -> str:
    return uuid4().hex


def today_str() -> str:
    return datetime.now().strftime(DATE_FMT)


def parse_date(text: str) -> datetime | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, DATE_FMT)
    except ValueError:
        return None


def parse_decimal(text: str) -> Decimal | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def fmt_decimal(value: Decimal | None) -> str:
    if value is None:
        return ""
    value = value.quantize(Decimal("0.01"))
    s = format(value, "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def has_negative(*values: str) -> bool:
    for value in values:
        d = parse_decimal(value)
        if d is not None and d < 0:
            return True
    return False


BETTING_STATUS_ORDER = {
    "NotStarted": 0,
    "NeedDeposit": 1,
    "NeedQB1": 2,
    "WaitQB1Settle": 3,
    "NeedQB2": 4,
    "WaitQB2Settle": 5,
    "NeedBonus": 6,
    "WaitBonusSettle": 7,
    "NeedWithdraw": 8,
    "WaitBank": 9,
    "Done": 10,
    "Error": 11,
}

CASINO_STATUS_ORDER = {
    "NotStarted": 0,
    "NeedDeposit": 1,
    "NeedFinal": 2,
    "WaitBank": 3,
    "Done": 4,
    "Error": 5,
}


def compute_betting_status(rec: dict[str, str]) -> str:
    if has_negative(rec.get("deposit_amount", ""), rec.get("qb1_amount", ""), rec.get("qb2_amount", ""), rec.get("bonus_amount", ""), rec.get("final_amount", "")):
        return "Error"
    if rec.get("bank_status") == "Issue":
        return "Error"
    has_qb2_payload = any((rec.get(f, "") or "").strip() for f in ("qb2_type", "qb2_amount", "qb2_date"))
    if rec.get("has_qb2") == "No" and (has_qb2_payload or rec.get("qb2_settled") == "Yes"):
        return "Error"
    if not (rec.get("bookie", "") or "").strip():
        return "NotStarted"
    if not (rec.get("deposit_amount", "") or "").strip():
        return "NeedDeposit"
    qb1_settled = rec.get("qb1_settled", "No") == "Yes"
    if not qb1_settled:
        if not (rec.get("qb1_type", "") or "").strip() or not (rec.get("qb1_amount", "") or "").strip():
            return "NeedQB1"
        return "WaitQB1Settle"

    if rec.get("has_qb2") == "Yes":
        qb2_settled = rec.get("qb2_settled", "No") == "Yes"
        if not qb2_settled:
            if not (rec.get("qb2_type", "") or "").strip() or not (rec.get("qb2_amount", "") or "").strip():
                return "NeedQB2"
            return "WaitQB2Settle"

    bonus_settled = rec.get("bonus_settled", "No") == "Yes"
    if not bonus_settled:
        if not (rec.get("bonus_type", "") or "").strip() or not (rec.get("bonus_amount", "") or "").strip():
            return "NeedBonus"
        return "WaitBonusSettle"

    if not (rec.get("final_amount", "") or "").strip():
        return "NeedWithdraw"
    if rec.get("bank_status") != "Received":
        return "WaitBank"
    return "Done"


def compute_casino_profit(rec: dict[str, str]) -> str:
    dep = parse_decimal(rec.get("deposit_amount", ""))
    final = parse_decimal(rec.get("final_amount", ""))
    if dep is None or final is None:
        return ""
    return fmt_decimal(final - dep)


def compute_casino_status(rec: dict[str, str]) -> str:
    if has_negative(rec.get("deposit_amount", "")):
        return "Error"
    if rec.get("bank_status") == "Issue":
        return "Error"
    if not (rec.get("bookie", "") or "").strip():
        return "NotStarted"
    if not (rec.get("deposit_amount", "") or "").strip():
        if (rec.get("final_amount", "") or "").strip():
            return "Error"
        return "NeedDeposit"
    if not (rec.get("final_amount", "") or "").strip():
        return "NeedFinal"
    if rec.get("bank_status") != "Received":
        return "WaitBank"
    return "Done"


def status_color(status: str) -> str:
    if status == "NotStarted":
        return "#9CA3AF"
    if status in {"NeedDeposit", "NeedQB1", "NeedQB2", "NeedBonus", "NeedWithdraw", "NeedFinal"}:
        return "#F59E0B"
    if status in {"WaitQB1Settle", "WaitQB2Settle", "WaitBonusSettle", "WaitBank"}:
        return "#3B82F6"
    if status == "Done":
        return "#16A34A"
    if status == "Error":
        return "#DC2626"
    return "#9CA3AF"
