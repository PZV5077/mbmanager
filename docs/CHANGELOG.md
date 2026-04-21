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
- Confirmed no runtime Python references to Reload Offer remain; only the legacy snapshot document is retained.

### Version and Branding
- Updated visible product version and title to 2.0.1.
- Removed "SQLite Edition" style wording in user-facing labels.

### Maintenance
- Cleaned Python cache artifacts from the app folder.
- Verified with compile checks and offscreen startup/theme-toggle smoke runs.

### UX Patch - Date/Time Popup Upgrade
- Removed secondary calendar expansion behavior in date editing popups.
- Replaced popup editor internals with an always-visible inline calendar layout.
- Added explicit hour/minute controls next to the calendar for faster precise input.
- Kept quick action buttons in popup flow:
  - Clear (reset value)
  - Now (set current local date/time)
- Kept click-to-open behavior directly on date/datetime cells.
- Added modern calendar styling for both light and dark themes inside popup dialogs.

### UI Patch - Theme Compatibility Hardening
- Replaced combo box pseudo-arrow drawing with explicit SVG chevrons for stable visibility in light/dark themes.
- Fixed combo popup and menu text colors that could inherit dark system palette values in light mode.
- Hardened date popup theming by styling the popup shell (`QDialog#dateTimePopup`) and calendar internals together.
- Added explicit palette synchronization for calendar view, viewport, and weekday/header rows to prevent Wayland post-show color fallback.
- Fixed weekday row background in month view by setting `QPalette.AlternateBase` (and disabled group equivalents) in light mode.

### UI Patch - Qt Material System Migration
- Switched the global theme engine from custom full-QSS to `qt-material` (`dark_blue.xml` / `light_blue.xml`).
- Added a concise project overlay stylesheet for consistent tabs, tables, danger actions, and panel metadata labels.
- Changed default first-launch theme to dark mode for a calm deep-blue workspace.
- Updated settings page styling from inline hardcoded colors to semantic properties (`role`, `variant`) to keep visuals cohesive.
- Synced date popup palette and color tokens with the new deep-blue visual language while preserving Wayland fallback protections.

### UI Patch - Phase 2 Workspace Hierarchy
- Reworked Betting and Casino tab headers into structured sections: title/subtitle, metric chips, filter bar, and action bar.
- Introduced reusable semantic styling roles for workspace controls (`panelSubtitle`, `sectionLabel`, `fieldLabel`, `metricChip`).
- Standardized button hierarchy with variants (`primary`, `secondary`, `ghost`, `danger`) for clearer action priority.
- Unified ledger table editor density by adding dedicated cell-editor styling hooks for line edits, combos, and toggles.
- Added live header metrics (visible, pending/waiting, done, selected) and sort-state hints to improve scanning speed.

### UI Patch - Phase 3 Status Semantics & Feedback
- Added a shared status-semantics layer (`action`, `progress`, `success`, `risk`, `neutral`) for both Betting and Casino workflows.
- Unified status-cell colors and text contrast through centralized helpers so both tabs render identical semantic feedback.
- Upgraded header chips to semantic counters (Action, In Progress, Done, Risk) with consistent visual states.
- Added visibility hints for idle/selected rows to improve operational awareness during batch edits.

### UI Patch - Phase 4 Micro Motion
- Added a minimal fade-in animation to the date/time popup so the interaction feels responsive without adding visual noise.
- Kept the motion scoped to the popup shell to avoid changing primary workspace behavior.

### UI Patch - Phase 5 Linux and Wayland Verification
- Re-checked visual regressions on Linux-focused startup paths and preserved the explicit Wayland popup refresh path.
- Kept the theme/popup smoke flow aligned with offscreen validation before packaging.
- Confirmed the release notes still keep the legacy Reload Offer snapshot documented while excluding the runtime entry.
