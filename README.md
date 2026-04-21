# Matched Betting Manager v2.0.1

PySide6 desktop app for matched betting records, now running on SQLite with a qt-material based theme system.

## Current Product Scope

- Betting: fully migrated to the SQLite schema with editable table workflow.
- Casino: retained and connected to the same SQLite storage layer.
- Reload Offer: removed from runtime UI; legacy behavior is documented in docs/reload_offer_legacy_spec.md.

## Data and Storage

- Database file name: mbmanager.db.
- Data directory is resolved by app/utils.py::get_data_dir().
- Priority rule: if project-root test/mbmanager.db exists, the app uses project-root test first.
- Otherwise fallback is platform specific (Linux Documents path if available, then home fallback; Windows cwd/mbmanager_data).

### Betting Table (SQLite)

Main table: betting_records.

Core columns:
- status, start_at, bookie, promo_name, deposit_amount
- q_result_at, q_event, q_type, q_amount, q_target, q_exchange, q_is_placed, q_is_completed
- b_result_at, b_event, b_type, b_amount, b_target, b_exchange, b_is_placed, b_is_completed
- profit, bank, notes

Indexes:
- status + start_at
- bookie
- promo_name
- q_result_at
- b_result_at
- bank

## UI and Behavior

- Material theme engine: dark by default, light optional.
- Shared semantic styling for chips, buttons, status feedback, and table editors.
- Date/time popup supports minute precision (24h) and uses a minimal fade-in animation.
- Profit field supports arithmetic expressions (example: -3+5 -> 2 after edit).

## Run

```bash
python -m venv .venv
pip install -r requirements.txt
python main.py
```
