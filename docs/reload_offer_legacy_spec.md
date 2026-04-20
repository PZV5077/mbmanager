# Reload Offer Legacy Feature Snapshot

Status: On hold for refactor (intentionally excluded from current rewrite)

## Existing Legacy Capabilities (v1)

- Bottom pull-up panel attached under the main tabs.
- Toggle expand/collapse to show a calendar and a day-based offer table.
- Offer templates can be created, duplicated, edited, enabled/disabled, and deleted.
- Template repeat modes: weekly, biweekly, monthly.
- Template fixed fields support:
  - bookie, promo_name, deposit_amount
  - qb1_type, qb1_amount
  - has_qb2, qb2_type, qb2_amount
  - bonus_type, bonus_amount
- Auto schedule generation window:
  - Keeps history and future horizon instances.
  - Rebuilds missing instances for active templates.
  - Prunes outdated future instances when template changes.
- Daily preview table shows template, status, and key amounts.
- Clicking an instance can jump/create corresponding betting record.
- Instance status can sync from betting progress state.
- Data file: reload_offers.json in the app data directory.

## Current Rewrite Decision

- Reload Offer UI and behavior are intentionally not included in the new version.
- This document preserves the functional baseline for a future dedicated refactor.
- Any future redesign should reuse this list as acceptance criteria before adding new features.
