# Matched Betting Manager

PySide6 desktop app for betting/casino records plus a reload-offer planner.

## What it does

- Betting and Casino record tables with search, filters, sort, undo, and autosave.
- Reload-offer pull-up panel with calendar, daily table, and template settings.
- Template-driven offer generation, status tracking, and click-to-create/highlight on the betting table.
- Clearable date inputs, keyboard navigation, and atomic CSV/JSON persistence.

## Data

- Betting: `data/betting.csv`
- Casino: `data/casino.csv`
- UI settings: `data/ui_settings.json`
- Reload offers: `reload_offers.json` in the app data directory

## Run

```bash
python -m venv .venv
pip install -r requirements.txt
python main.py
```
