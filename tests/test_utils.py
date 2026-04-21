from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from app import utils


class ProfitExpressionTests(unittest.TestCase):
    def test_evaluates_arithmetic_expression(self) -> None:
        self.assertEqual(utils.evaluate_profit_expression("-3+5"), "2")
        self.assertEqual(utils.evaluate_profit_expression("10/4"), "2.5")

    def test_rejects_invalid_expression(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid characters"):
            utils.evaluate_profit_expression("1+abc")

        with self.assertRaisesRegex(ValueError, "Division by zero"):
            utils.evaluate_profit_expression("5/0")


class StatusRuleTests(unittest.TestCase):
    def test_betting_status_flow(self) -> None:
        record = {
            "start_at": "2026-04-21 10:00",
            "bookie": "Bookie",
            "promo_name": "Promo",
            "deposit_amount": "10",
            "q_amount": "9.5",
            "b_amount": "9.2",
            "q_is_placed": "Yes",
            "q_is_completed": "Yes",
            "b_is_placed": "Yes",
            "b_is_completed": "No",
            "bank": "Uncon",
        }
        self.assertEqual(utils.compute_betting_status(record), "WaitBResult")

        record["b_is_completed"] = "Yes"
        self.assertEqual(utils.compute_betting_status(record), "NeedBank")

        record["bank"] = "Rec"
        self.assertEqual(utils.compute_betting_status(record), "Done")

    def test_casino_status_and_profit(self) -> None:
        record = {
            "bookie": "Casino",
            "deposit_amount": "20",
            "final_amount": "26.5",
            "bank_status": "Received",
        }
        self.assertEqual(utils.compute_casino_profit(record), "6.5")
        self.assertEqual(utils.compute_casino_status(record), "Done")

        record["final_amount"] = ""
        self.assertEqual(utils.compute_casino_status(record), "NeedFinal")


class DataDirTests(unittest.TestCase):
    def test_prefers_repo_test_database_when_present(self) -> None:
        data_dir = utils.get_data_dir()
        self.assertEqual(data_dir, Path(__file__).resolve().parents[1] / "test")

    def test_linux_fallback_prefers_documents_when_repo_db_missing(self) -> None:
        project_root = Path(utils.__file__).resolve().parents[1]
        repo_db = project_root / "test" / "mbmanager.db"
        home = Path("/tmp/fake-home")

        original_exists = Path.exists

        def fake_exists(path: Path) -> bool:
            if path == repo_db:
                return False
            if path == home / "Documents":
                return True
            return original_exists(path)

        with patch("app.utils.platform.system", return_value="Linux"):
            with patch("pathlib.Path.home", return_value=home):
                with patch("pathlib.Path.exists", new=fake_exists):
                    self.assertEqual(utils.get_data_dir(), home / "Documents" / "mbmanager_data")


if __name__ == "__main__":
    unittest.main()
