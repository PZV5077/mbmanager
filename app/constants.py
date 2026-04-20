from __future__ import annotations

DATE_TIME_FMT = "%Y-%m-%d %H:%M"

YES_NO = ["No", "Yes"]

BETTING_STATUS_VALUES = [
    "NotStarted",
    "NeedQBet",
    "WaitQResult",
    "NeedBBet",
    "WaitBResult",
    "NeedBank",
    "Done",
    "Error",
]

BETTING_STATUS_ORDER = {status: index for index, status in enumerate(BETTING_STATUS_VALUES)}

BETTING_Q_TYPES = ["", "NORM", "F-SNR", "F-SR", "2UP", "ACCA", "EP", "BOOST", "BB", "OTH"]
BETTING_B_TYPES = ["", "NORM", "F-SNR", "F-SR", "2UP", "ACCA", "EP", "BOOST", "BB", "OTH"]
BETTING_Q_EXCHANGES = ["", "SMK", "BTF", "MB", "OTH"]
BETTING_B_EXCHANGES = ["", "SMK", "MB", "OTH"]
BETTING_BANK_VALUES = ["Uncon", "Rec", "Issue"]

BETTING_FIELDS = [
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
]

BETTING_HEADERS = [
    "Status",
    "Start Date",
    "Bookie",
    "Promo Name",
    "Dep",
    "Q Date",
    "Q Event",
    "Q Type",
    "Q Amount",
    "Q Target",
    "Q Exchange",
    "Q Placed",
    "Q Done",
    "B Date",
    "B Event",
    "B Type",
    "B Amount",
    "B Target",
    "B Exchange",
    "B Placed",
    "B Done",
    "Profit",
    "Bank",
    "Notes",
]

BETTING_COL_WIDTHS = [
    120,
    160,
    140,
    160,
    88,
    160,
    120,
    96,
    88,
    160,
    96,
    88,
    88,
    160,
    120,
    96,
    88,
    160,
    96,
    88,
    88,
    92,
    88,
    220,
]

BETTING_SORT_COLUMNS = {
    0: "status",
    1: "start_at",
    2: "bookie",
    3: "promo_name",
    4: "deposit_amount",
    5: "q_result_at",
    6: "q_event",
    7: "q_type",
    8: "q_amount",
    9: "q_target",
    10: "q_exchange",
    11: "q_is_placed",
    12: "q_is_completed",
    13: "b_result_at",
    14: "b_event",
    15: "b_type",
    16: "b_amount",
    17: "b_target",
    18: "b_exchange",
    19: "b_is_placed",
    20: "b_is_completed",
    21: "profit",
    22: "bank",
    23: "notes",
}
