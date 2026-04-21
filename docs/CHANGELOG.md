# Changelog

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
