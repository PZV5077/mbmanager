# Matched Betting Manager v2.0.1

Modernized PySide6 interface with a refactored local database architecture.

## Scope

- Fully refactored Betting workflow with a new schema and minute-level datetime pickers.
- Casino tab behavior retained.
- Reload Offer UI is intentionally excluded in v2 (legacy behavior documented in docs/reload_offer_legacy_spec.md).
- No backward compatibility layer for old CSV/JSON data.
- Data directory location remains unchanged from previous versions.

## Data Storage

- Database file: mbmanager.db
- Path root: platform-specific data directory from app/utils.py

### Betting Table (SQLite)

Main table: betting_records

Columns:
- status
- start_at
- bookie
- promo_name
- deposit_amount
- q_result_at
- q_event
- q_type (NORM, F-SNR, F-SR, 2UP, ACCA, EP, BOOST, BB, OTH)
- q_amount
- q_target
- q_exchange (SMK, BTF, MB, OTH)
- q_is_placed
- q_is_completed
- b_result_at
- b_event
- b_type (NORM, F-SNR, F-SR, 2UP, ACCA, EP, BOOST, BB, OTH)
- b_amount
- b_target
- b_exchange (SMK, MB, OTH)
- b_is_placed
- b_is_completed
- profit
- bank (Uncon, Rec, Issue)
- notes

Indexes:
- status + start_at
- bookie
- promo_name
- q_result_at
- b_result_at
- bank

## UI Notes

- Start/Q/B datetime fields use popup picker with 24-hour time and minute precision.
- Profit supports inline arithmetic expressions (example: -3+5 -> 2 when editing ends).
- Betting list supports SQL-backed search/filter/sort.

## Run

```bash
python -m venv .venv
pip install -r requirements.txt
python main.py
```
