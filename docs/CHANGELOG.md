# Changelog

## 2.0.1 - 2026-04-20

### Major Refactor
- Rebuilt the application around a SQLite-first architecture.
- Replaced the legacy betting data flow with schema-driven storage and indexed queries.
- Kept casino workflow behavior while migrating its persistence to the new database layer.

### Betting Module
- Rewrote the Betting tab with the new field model:
  - Status, Start Date, Bookie, Promo Name, Dep
  - Q block: result datetime, event, type, amount, target, exchange, placed, completed
  - B block: result datetime, event, type, amount, target, exchange, placed, completed
  - Profit, Bank, Notes
- Added minute-level datetime pickers with 24-hour format.
- Added expression evaluation for Profit input (e.g. -3+5 => 2 on edit finish).
- Preserved search/filter/sort/add/copy/delete/undo/redo workflows.

### Storage and Performance
- Added SQLite schema with constraints for key enumerations.
- Added indexes for high-frequency query dimensions (status/time/bookie/promo/q-date/b-date/bank).
- Added database APIs for betting CRUD, snapshots, replace operations, and casino compatibility handling.

### UI and Themes
- Added a top-right light/dark theme toggle button (left of Settings).
- Persisted selected theme mode in UI settings.
- Added refined dual theme palettes with dedicated styling for:
  - Combo popup option backgrounds and selected states
  - Radio/checkbox indicator backgrounds and interactions
- Updated input controls to square borders.
- Added table-cell integrated square styling for embedded editors.

### Product Scope Updates
- Removed runtime Reload Offer integration from the main workspace.
- Kept a legacy capability snapshot for future redesign:
  - docs/reload_offer_legacy_spec.md
- Removed obsolete Reload Offer runtime files no longer referenced by active flow.

### Version and Branding
- Updated visible product version and title to 2.0.1.
- Removed "SQLite Edition" style wording in user-facing labels.

### Maintenance
- Cleaned Python cache artifacts from the app folder.
- Verified with compile checks and offscreen startup/theme-toggle smoke runs.
