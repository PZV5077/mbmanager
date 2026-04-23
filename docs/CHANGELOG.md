# Changelog

## 2.0.2 - 2026-04-24

### Reload Offers
- Split Reload Offers into Betting and Casino dedicated panels and template dialogs.
- Added a shared `ReloadOffersPanelBase` to centralize panel header, calendar/table layout, metrics, expand/collapse animation, and row activation flow.
- Wired panel refresh notifications from Casino record mutations to keep Reload views synchronized.

### Data and Fixtures
- Migrated reload storage schema into betting/casino specific template and instance tables.
- Added small-scale fixture generator at `test/generate_small_test_db.py` and generated `test/fixtures/sample_usage/mbmanager.db` for local testing.

## 2.0.1 - 2026-04-20

### Architecture
- Moved to a SQLite-first storage model for active workflows.
- Rebuilt Betting records around a schema-driven table with indexed queries.
- Kept Casino behavior and connected it to the same database layer.

### Product Scope
- Runtime Reload Offer entry removed from workspace tabs.
- Legacy Reload Offer behavior retained as documentation only: docs/reload_offer_legacy_spec.md.
- User-facing version/title aligned to 2.0.1.

### UI and Theme System
- Switched global theme engine to qt-material (dark default, light optional).
- Added a shared overlay stylesheet and semantic roles/variants for chips, buttons, labels, and table editors.
- Reworked Betting/Casino top areas into title + metrics + filters + actions for clearer hierarchy.
- Unified status semantics across tabs (action/progress/success/risk/neutral) with centralized colors/text contrast.

### Interaction and Stability
- Date/time popup upgraded with inline controls, minute precision (24h), and minimal fade-in motion.
- Wayland/Linux popup palette refresh path preserved to avoid post-show color fallback.
- Theme toggle and font/theme settings persistence validated in startup smoke checks.

### Data Rules and Utilities
- Added expression evaluation for Profit input (example: -3+5 => 2).
- Introduced/updated status helper functions used by both Betting and Casino renderers.
- Updated data-directory resolution to support project-root test database priority when test/mbmanager.db exists.
