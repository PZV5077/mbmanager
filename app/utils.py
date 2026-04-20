from __future__ import annotations

import ast
import operator
import platform
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable
from uuid import uuid4

from .constants import DATE_TIME_FMT

DATE_FMT = "%d/%m/%y"


def get_data_dir() -> Path:
    """获取平台特定的数据目录。"""
    system = platform.system()

    if system == "Linux":
        home = Path.home()
        for docs_folder in ["文档", "Documents"]:
            docs_dir = home / docs_folder
            if docs_dir.exists():
                return docs_dir / "mbmanager_data"
        return home / ".mbmanager_data"

    if system == "Windows":
        return Path.cwd() / "mbmanager_data"

    return Path.home() / ".mbmanager_data"


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


def parse_datetime(text: str) -> datetime | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, DATE_TIME_FMT)
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
    out = format(value, "f")
    if "." in out:
        out = out.rstrip("0").rstrip(".")
    return out


def has_negative(*values: str) -> bool:
    for value in values:
        dec = parse_decimal(value)
        if dec is not None and dec < 0:
            return True
    return False


def evaluate_profit_expression(text: str) -> str:
    expr = (text or "").strip()
    if not expr:
        return ""

    direct = parse_decimal(expr)
    if direct is not None:
        return fmt_decimal(direct)

    if not re.fullmatch(r"[0-9+\-*/().\s]+", expr):
        raise ValueError("Profit expression contains invalid characters")

    node = ast.parse(expr, mode="eval")
    result = _eval_profit_ast(node.body)
    return fmt_decimal(result)


def _eval_profit_ast(node: ast.AST) -> Decimal:
    bin_ops: dict[type[ast.AST], Callable[[Decimal, Decimal], Decimal]] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }
    unary_ops: dict[type[ast.AST], Callable[[Decimal], Decimal]] = {
        ast.UAdd: lambda v: v,
        ast.USub: lambda v: -v,
    }

    if isinstance(node, ast.BinOp) and type(node.op) in bin_ops:
        left = _eval_profit_ast(node.left)
        right = _eval_profit_ast(node.right)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ValueError("Division by zero in profit expression")
        return Decimal(str(bin_ops[type(node.op)](left, right)))

    if isinstance(node, ast.UnaryOp) and type(node.op) in unary_ops:
        return Decimal(str(unary_ops[type(node.op)](_eval_profit_ast(node.operand))))

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return Decimal(str(node.value))

    raise ValueError("Unsupported profit expression")


CASINO_STATUS_ORDER = {
    "NotStarted": 0,
    "NeedDeposit": 1,
    "NeedFinal": 2,
    "WaitBank": 3,
    "Done": 4,
    "Error": 5,
}


def _is_yes(value: str) -> bool:
    return (value or "").strip().lower() in {"yes", "true", "1", "y"}


def compute_betting_status(rec: dict[str, str]) -> str:
    # New SQLite schema status flow.
    if {"q_is_placed", "q_is_completed", "b_is_placed", "b_is_completed", "bank"}.issubset(rec.keys()):
        if rec.get("bank") == "Issue":
            return "Error"
        if has_negative(rec.get("deposit_amount", ""), rec.get("q_amount", ""), rec.get("b_amount", "")):
            return "Error"

        has_identity = any((rec.get(field, "") or "").strip() for field in ("start_at", "bookie", "promo_name"))
        if not has_identity:
            return "NotStarted"

        if not _is_yes(rec.get("q_is_placed", "No")):
            return "NeedQBet"
        if not _is_yes(rec.get("q_is_completed", "No")):
            return "WaitQResult"
        if not _is_yes(rec.get("b_is_placed", "No")):
            return "NeedBBet"
        if not _is_yes(rec.get("b_is_completed", "No")):
            return "WaitBResult"
        if rec.get("bank") != "Rec":
            return "NeedBank"
        return "Done"

    # Legacy CSV schema fallback.
    if has_negative(
        rec.get("deposit_amount", ""),
        rec.get("qb1_amount", ""),
        rec.get("qb2_amount", ""),
        rec.get("bonus_amount", ""),
        rec.get("final_amount", ""),
    ):
        return "Error"
    if rec.get("bank_status") == "Issue":
        return "Error"

    has_qb2_payload = any((rec.get(field, "") or "").strip() for field in ("qb2_type", "qb2_amount", "qb2_date"))
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
    if status in {
        "NeedDeposit",
        "NeedQB1",
        "NeedQB2",
        "NeedBonus",
        "NeedWithdraw",
        "NeedFinal",
        "NeedQBet",
        "NeedBBet",
        "NeedBank",
    }:
        return "#F59E0B"
    if status in {"WaitQB1Settle", "WaitQB2Settle", "WaitBonusSettle", "WaitBank", "WaitQResult", "WaitBResult"}:
        return "#3B82F6"
    if status == "Done":
        return "#16A34A"
    if status == "Error":
        return "#DC2626"
    return "#9CA3AF"
