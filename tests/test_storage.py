from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.storage import AppDatabase


class AppDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tempdir.name)
        self.db = AppDatabase(self.data_dir)

    def tearDown(self) -> None:
        self.db.close()
        self.tempdir.cleanup()

    def test_betting_record_crud_round_trip(self) -> None:
        record = {
            "id": "bet-1",
            "status": "NeedQBet",
            "start_at": "2026-04-21 10:00",
            "bookie": "Bookie",
            "promo_name": "Promo",
            "deposit_amount": "10",
            "q_result_at": "",
            "q_event": "",
            "q_type": "NORM",
            "q_amount": "9.5",
            "q_target": "https://example.com/q",
            "q_exchange": "SMK",
            "q_is_placed": "Yes",
            "q_is_completed": "No",
            "b_result_at": "",
            "b_event": "",
            "b_type": "NORM",
            "b_amount": "9",
            "b_target": "https://example.com/b",
            "b_exchange": "MB",
            "b_is_placed": "No",
            "b_is_completed": "No",
            "profit": "1.5",
            "bank": "Uncon",
            "notes": "note",
        }
        self.db.insert_betting_record(record)

        stored = self.db.get_betting_record("bet-1")
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored["deposit_amount"], "10")
        self.assertEqual(stored["q_is_placed"], "Yes")

        stored["profit"] = "2"
        stored["bank"] = "Rec"
        self.db.update_betting_record("bet-1", stored)

        updated = self.db.get_betting_record("bet-1")
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated["profit"], "2")
        self.assertEqual(updated["bank"], "Rec")

        self.db.delete_betting_records(["bet-1"])
        self.assertIsNone(self.db.get_betting_record("bet-1"))

    def test_casino_record_crud_round_trip(self) -> None:
        record = {
            "id": "cas-1",
            "status": "NeedFinal",
            "bookie": "Casino",
            "promo_start_date": "21/04/26",
            "promo_name": "Offer",
            "deposit_amount": "20",
            "final_amount": "",
            "bank_status": "Unconfirmed",
            "profit": "",
            "notes": "memo",
        }
        self.db.insert_casino_record(record)

        stored = self.db.get_casino_record("cas-1")
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored["promo_name"], "Offer")
        self.assertEqual(stored["deposit_amount"], "20")

        stored["final_amount"] = "25"
        stored["bank_status"] = "Received"
        stored["profit"] = "5"
        stored["status"] = "Done"
        self.db.update_casino_record("cas-1", stored)

        updated = self.db.get_casino_record("cas-1")
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated["final_amount"], "25")
        self.assertEqual(updated["status"], "Done")

        self.db.delete_casino_records(["cas-1"])
        self.assertIsNone(self.db.get_casino_record("cas-1"))

    def test_casino_fetch_filters_and_sorting(self) -> None:
        self.db.insert_casino_record(
            {
                "id": "cas-1",
                "status": "Done",
                "bookie": "Alpha",
                "promo_start_date": "20/04/26",
                "promo_name": "One",
                "deposit_amount": "10",
                "final_amount": "12",
                "bank_status": "Received",
                "profit": "2",
                "notes": "first",
            }
        )
        self.db.insert_casino_record(
            {
                "id": "cas-2",
                "status": "NeedFinal",
                "bookie": "Beta",
                "promo_start_date": "21/04/26",
                "promo_name": "Two",
                "deposit_amount": "15",
                "final_amount": "",
                "bank_status": "Unconfirmed",
                "profit": "",
                "notes": "second",
            }
        )

        filtered = self.db.fetch_casino_records(search="bet", status="Any", bank_status="Any")
        self.assertEqual([row["id"] for row in filtered], ["cas-2"])

        done_only = self.db.fetch_casino_records(search="", status="Done", bank_status="Received")
        self.assertEqual([row["id"] for row in done_only], ["cas-1"])

        by_amount = self.db.fetch_casino_records(search="", sort_field="deposit_amount", ascending=False)
        self.assertEqual([row["id"] for row in by_amount], ["cas-2", "cas-1"])

    def test_casino_snapshot_and_replace(self) -> None:
        self.db.insert_casino_record(
            {
                "id": "cas-1",
                "status": "NeedDeposit",
                "bookie": "A",
                "promo_start_date": "",
                "promo_name": "P1",
                "deposit_amount": "",
                "final_amount": "",
                "bank_status": "Unconfirmed",
                "profit": "",
                "notes": "",
            }
        )
        snapshot = self.db.snapshot_casino_records()
        self.db.replace_casino_records(
            [
                {
                    "id": "cas-2",
                    "status": "Done",
                    "bookie": "B",
                    "promo_start_date": "21/04/26",
                    "promo_name": "P2",
                    "deposit_amount": "10",
                    "final_amount": "14",
                    "bank_status": "Received",
                    "profit": "4",
                    "notes": "done",
                }
            ]
        )
        self.assertEqual([row["id"] for row in self.db.fetch_casino_records()], ["cas-2"])

        self.db.replace_casino_records(snapshot)
        self.assertEqual([row["id"] for row in self.db.fetch_casino_records()], ["cas-1"])


if __name__ == "__main__":
    unittest.main()
