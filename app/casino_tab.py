from __future__ import annotations

from copy import deepcopy
from functools import partial
from pathlib import Path

from PySide6.QtCore import QEvent, QTimer, Qt
from PySide6.QtGui import QBrush, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .storage import CsvStore
from .ui_settings import UiSettingsStore
from .utils import (
    CASINO_STATUS_ORDER,
    compute_casino_profit,
    compute_casino_status,
    new_id,
    parse_date,
    parse_decimal,
    status_color,
    status_feedback_group,
    status_text_color,
)
from .widgets import LinkLineWidget, NullableDateWidget, normalize_web_url

FIELDS = ["id", "status", "bookie", "promo_start_date", "promo_name", "deposit_amount", "final_amount", "bank_status", "profit", "notes"]
HEADERS = ["Status", "Bookie", "P.Start", "Promo", "Dep", "Final", "Bank", "P/L", "Notes"]
COL_WIDTHS = [105, 105, 132, 125, 72, 78, 95, 72, 145]
BANK = ["Unconfirmed", "Received", "Issue"]
STATUS_FILTERS = ["NotStarted", "NeedDeposit", "NeedFinal", "WaitBank", "Done", "Error"]
NAV_FIELDS = ["bookie", "promo_start_date", "promo_name", "deposit_amount", "final_amount", "bank_status", "notes"]


class CasinoTab(QWidget):
    def __init__(self, data_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = CsvStore(data_dir / "casino.csv", FIELDS)
        self.ui_settings = UiSettingsStore(data_dir)
        self.records = self.store.load()
        self.active_record_id: str | None = None
        self.sort_field = "promo_start_date"
        self.sort_ascending = True
        self.undo_stack: list[tuple[list[dict[str, str]], str | None]] = []
        self.redo_stack: list[tuple[list[dict[str, str]], str | None]] = []
        self.row_to_record_id: dict[int, str] = {}
        self.visible_record_ids: list[str] = []
        self.widget_map: dict[tuple[str, str], QWidget] = {}
        self._copy_snapshot_ids: list[str] = []
        self._delete_snapshot_ids: list[str] = []
        self._startup_focus_pending = True
        self._applying_col_widths = False
        self._last_visible_records: list[dict[str, str]] = []
        self.col_widths = self.ui_settings.get_column_widths("casino", COL_WIDTHS, len(HEADERS))

        self._normalize_records()

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(700)
        self.save_timer.timeout.connect(self._save_records)

        self.settings_timer = QTimer(self)
        self.settings_timer.setSingleShot(True)
        self.settings_timer.setInterval(300)
        self.settings_timer.timeout.connect(self._save_column_widths)

        title = QLabel("Casino Ledger", self)
        title.setProperty("role", "panelTitle")

        subtitle = QLabel("Manage promo lifecycle from deposit to bank confirmation.", self)
        subtitle.setProperty("role", "panelSubtitle")

        self.total_chip = QLabel(self)
        self.action_chip = QLabel(self)
        self.progress_chip = QLabel(self)
        self.done_chip = QLabel(self)
        self.risk_chip = QLabel(self)
        for chip in (self.total_chip, self.action_chip, self.progress_chip, self.done_chip, self.risk_chip):
            chip.setProperty("role", "metricChip")
            chip.setProperty("state", "neutral")

        header = QFrame(self)
        header.setObjectName("workspaceHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(8)

        header_left = QVBoxLayout()
        header_left.setContentsMargins(0, 0, 0, 0)
        header_left.setSpacing(2)
        header_left.addWidget(title)
        header_left.addWidget(subtitle)

        chip_row = QHBoxLayout()
        chip_row.setContentsMargins(0, 0, 0, 0)
        chip_row.setSpacing(6)
        chip_row.addWidget(self.total_chip)
        chip_row.addWidget(self.action_chip)
        chip_row.addWidget(self.progress_chip)
        chip_row.addWidget(self.done_chip)
        chip_row.addWidget(self.risk_chip)

        header_layout.addLayout(header_left, 1)
        header_layout.addLayout(chip_row)

        self.search_edit = QLineEdit(self)
        self.search_edit.setPlaceholderText("Search Bookie or Promo")
        self.search_edit.setProperty("role", "toolbarSearch")
        self.search_edit.textChanged.connect(self.render_table)

        self.filter_toggle = QToolButton(self)
        self.filter_toggle.setText("Advanced Filters")
        self.filter_toggle.setCheckable(True)
        self.filter_toggle.setProperty("variant", "secondary")
        self.filter_toggle.toggled.connect(self._toggle_filters)

        self.clear_filters_btn = QPushButton("Clear Filters", self)
        self.clear_filters_btn.setProperty("variant", "ghost")
        self.clear_filters_btn.clicked.connect(self.clear_filters)

        self.undo_btn = QPushButton("Undo", self)
        self.undo_btn.setProperty("variant", "ghost")
        self.undo_btn.clicked.connect(self.undo_last_change)
        self.undo_btn.setEnabled(False)

        self.redo_btn = QPushButton("Redo", self)
        self.redo_btn.setProperty("variant", "ghost")
        self.redo_btn.clicked.connect(self.redo_last_change)
        self.redo_btn.setEnabled(False)

        self.add_btn = QPushButton("Add Record", self)
        self.add_btn.setProperty("variant", "primary")
        self.add_btn.clicked.connect(self.add_record)
        self.add_btn.setFocusPolicy(Qt.NoFocus)

        self.copy_btn = QPushButton("Copy Selected", self)
        self.copy_btn.setProperty("variant", "secondary")
        self.copy_btn.clicked.connect(self.copy_selected)
        self.copy_btn.setFocusPolicy(Qt.NoFocus)
        self.copy_btn.pressed.connect(self._capture_copy_selection)

        self.delete_btn = QPushButton("Delete Selected", self)
        self.delete_btn.setProperty("variant", "danger")
        self.delete_btn.setFocusPolicy(Qt.NoFocus)
        self.delete_btn.pressed.connect(self._capture_delete_selection)
        self.delete_btn.clicked.connect(self.delete_selected)

        controls = QFrame(self)
        controls.setObjectName("controlBar")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(10, 8, 10, 8)
        controls_layout.setSpacing(8)

        filter_label = QLabel("Filters", controls)
        filter_label.setProperty("role", "sectionLabel")
        search_label = QLabel("Search", controls)
        search_label.setProperty("role", "fieldLabel")

        controls_layout.addWidget(filter_label)
        controls_layout.addWidget(search_label)
        controls_layout.addWidget(self.search_edit, 1)
        controls_layout.addWidget(self.filter_toggle)
        controls_layout.addWidget(self.clear_filters_btn)
        controls_layout.addWidget(self.undo_btn)
        controls_layout.addWidget(self.redo_btn)

        actions = QFrame(self)
        actions.setObjectName("actionBar")
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(10, 8, 10, 8)
        actions_layout.setSpacing(8)

        actions_label = QLabel("Actions", actions)
        actions_label.setProperty("role", "sectionLabel")

        self.view_hint_label = QLabel("", actions)
        self.view_hint_label.setProperty("role", "metaInfo")

        actions_layout.addWidget(actions_label)
        actions_layout.addWidget(self.view_hint_label)
        actions_layout.addStretch(1)
        actions_layout.addWidget(self.add_btn)
        actions_layout.addWidget(self.copy_btn)
        actions_layout.addWidget(self.delete_btn)

        self.filter_panel = self._build_filter_panel()
        self.filter_panel.setVisible(False)

        self.table = QTableWidget(self)
        self.table.setObjectName("ledgerTable")
        self.table.setColumnCount(len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.verticalHeader().setMinimumSectionSize(32)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionsMovable(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().sectionClicked.connect(self.sort_by_column)
        self.table.horizontalHeader().sectionResized.connect(self._on_section_resized)
        self.table.itemSelectionChanged.connect(self._refresh_header_metrics)

        lay = QVBoxLayout(self)
        lay.addWidget(header)
        lay.addWidget(controls)
        lay.addWidget(actions)
        lay.addWidget(self.filter_panel)
        lay.addWidget(self.table, 1)

        QShortcut(QKeySequence.Undo, self, activated=self.undo_last_change)
        QShortcut(QKeySequence.Redo, self, activated=self.redo_last_change)
        self._refresh_header_metrics([])
        self.render_table()

    def _normalize_records(self) -> None:
        for rec in self.records:
            rec["profit"] = compute_casino_profit(rec)
            rec["status"] = compute_casino_status(rec)
        self._save_records()

    def _build_filter_panel(self) -> QWidget:
        panel = QFrame(self)
        panel.setObjectName("filterPanel")
        panel.setFrameShape(QFrame.StyledPanel)
        grid = QGridLayout(panel)
        grid.setContentsMargins(10, 8, 10, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        self.f_status = self._filter_combo(["Any", *STATUS_FILTERS])
        self.f_bank = self._filter_combo(["Any", *BANK])
        status_label = QLabel("Status", panel)
        status_label.setProperty("role", "fieldLabel")
        bank_label = QLabel("Bank", panel)
        bank_label.setProperty("role", "fieldLabel")
        grid.addWidget(status_label, 0, 0)
        grid.addWidget(self.f_status, 0, 1)
        grid.addWidget(bank_label, 0, 2)
        grid.addWidget(self.f_bank, 0, 3)
        return panel

    def _filter_combo(self, values: list[str]) -> QComboBox:
        combo = QComboBox(self)
        combo.setProperty("role", "toolbarSelect")
        combo.addItems(values)
        combo.currentTextChanged.connect(self.render_table)
        return combo

    def _toggle_filters(self, checked: bool) -> None:
        self.filter_panel.setVisible(checked)
        self.filter_toggle.setText("Hide Filters" if checked else "Advanced Filters")

    def clear_filters(self) -> None:
        self.f_status.setCurrentIndex(0)
        self.f_bank.setCurrentIndex(0)
        self.render_table()

    def _push_undo(self) -> None:
        self.undo_stack.append((deepcopy(self.records), self.active_record_id))
        self.undo_stack = self.undo_stack[-30:]
        self.redo_stack.clear()
        self._update_history_buttons()

    def _update_history_buttons(self) -> None:
        self.undo_btn.setEnabled(bool(self.undo_stack))
        self.redo_btn.setEnabled(bool(self.redo_stack))

    def undo_last_change(self) -> None:
        if not self.undo_stack:
            return
        self.redo_stack.append((deepcopy(self.records), self.active_record_id))
        self.redo_stack = self.redo_stack[-30:]
        self.records, self.active_record_id = self.undo_stack.pop()
        self._update_history_buttons()
        self.schedule_save()
        self.render_table()

    def redo_last_change(self) -> None:
        if not self.redo_stack:
            return
        self.undo_stack.append((deepcopy(self.records), self.active_record_id))
        self.undo_stack = self.undo_stack[-30:]
        self.records, self.active_record_id = self.redo_stack.pop()
        self._update_history_buttons()
        self.schedule_save()
        self.render_table()

    def schedule_save(self) -> None:
        self.save_timer.start()

    def _save_records(self) -> None:
        for rec in self.records:
            rec["profit"] = compute_casino_profit(rec)
            rec["status"] = compute_casino_status(rec)
        try:
            self.store.save(self.records)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Save failed", f"Auto-save failed:\n{exc}")

    def _bookie_options(self) -> list[str]:
        return sorted({(r.get("bookie", "") or "").strip() for r in self.records if (r.get("bookie", "") or "").strip()})

    def add_record(self) -> None:
        self._push_undo()
        rec = {
            "id": new_id(),
            "status": "NotStarted",
            "bookie": "",
            "promo_start_date": "",
            "promo_name": "",
            "deposit_amount": "",
            "final_amount": "",
            "bank_status": "Unconfirmed",
            "profit": "",
            "notes": "",
        }

        current_id = self._current_record_id()
        if current_id:
            insert_at = next((i for i, row in enumerate(self.records) if row.get("id") == current_id), None)
            if insert_at is None:
                self.records.append(rec)
            else:
                self.records.insert(insert_at + 1, rec)
        else:
            self.records.append(rec)

        self.active_record_id = rec["id"]
        self.schedule_save()
        self.render_table()

    def delete_selected(self) -> None:
        selected_ids = list(self._delete_snapshot_ids)
        self._delete_snapshot_ids.clear()

        selected_rows = set()
        selection_model = self.table.selectionModel()
        if selection_model is not None:
            selected_rows = {idx.row() for idx in selection_model.selectedRows()}

        if not selected_ids:
            selected_ids = [
                rid
                for row in sorted(selected_rows)
                if (rid := self.row_to_record_id.get(row)) is not None
            ]

        if not selected_ids:
            rid = self._current_record_id()
            if rid:
                selected_ids = [rid]

        if not selected_ids:
            QMessageBox.information(self, "Delete", "Select a record first.")
            return

        count = len(selected_ids)
        prompt = "Delete the selected record?" if count == 1 else f"Delete {count} selected records?"
        if QMessageBox.question(self, "Delete", prompt) != QMessageBox.Yes:
            return

        self._push_undo()
        to_delete = set(selected_ids)
        self.records = [r for r in self.records if r["id"] not in to_delete]
        self.active_record_id = None
        self.schedule_save()
        self.render_table()

    def copy_selected(self) -> None:
        selected_ids = list(self._copy_snapshot_ids)
        self._copy_snapshot_ids.clear()

        selected_rows = set()
        selection_model = self.table.selectionModel()
        if selection_model is not None:
            selected_rows = {idx.row() for idx in selection_model.selectedRows()}

        if not selected_ids:
            selected_ids = [
                rid
                for row in sorted(selected_rows)
                if (rid := self.row_to_record_id.get(row)) is not None
            ]

        if not selected_ids:
            rid = self._current_record_id()
            if rid:
                selected_ids = [rid]

        if not selected_ids:
            QMessageBox.information(self, "Copy", "Select a record first.")
            return

        self._push_undo()
        copied_items: list[tuple[str, dict[str, str]]] = []
        seen: set[str] = set()
        for rid in selected_ids:
            if rid in seen:
                continue
            seen.add(rid)
            original = next((r for r in self.records if r["id"] == rid), None)
            if original is None:
                continue
            copied = deepcopy(original)
            copied["id"] = new_id()
            copied["profit"] = compute_casino_profit(copied)
            copied["status"] = compute_casino_status(copied)
            copied_items.append((rid, copied))

        if not copied_items:
            self.undo_stack.pop()
            self._update_history_buttons()
            return

        inserted_ids: list[str] = []
        for source_id, copied in copied_items:
            insert_at = next((i for i, row in enumerate(self.records) if row.get("id") == source_id), None)
            if insert_at is None:
                self.records.append(copied)
            else:
                self.records.insert(insert_at + 1, copied)
            inserted_ids.append(copied["id"])

        self.active_record_id = inserted_ids[-1]
        self.schedule_save()
        self.render_table()

    def _capture_delete_selection(self) -> None:
        selected_rows = set()
        selection_model = self.table.selectionModel()
        if selection_model is not None:
            selected_rows = {idx.row() for idx in selection_model.selectedRows()}

        self._delete_snapshot_ids = [
            rid
            for row in sorted(selected_rows)
            if (rid := self.row_to_record_id.get(row)) is not None
        ]

    def _capture_copy_selection(self) -> None:
        selected_rows = set()
        selection_model = self.table.selectionModel()
        if selection_model is not None:
            selected_rows = {idx.row() for idx in selection_model.selectedRows()}

        self._copy_snapshot_ids = [
            rid
            for row in sorted(selected_rows)
            if (rid := self.row_to_record_id.get(row)) is not None
        ]

    def _current_record_id(self) -> str | None:
        row = self.table.currentRow()
        return self.row_to_record_id.get(row) or self.active_record_id

    def _visible_records(self) -> list[dict[str, str]]:
        term = self.search_edit.text().strip().lower()
        out: list[dict[str, str]] = []
        for rec in self.records:
            rec["profit"] = compute_casino_profit(rec)
            rec["status"] = compute_casino_status(rec)
            if term:
                hay = f"{rec.get('bookie','')} {rec.get('promo_name','')}".lower()
                if term not in hay:
                    continue
            if self.f_status.currentText() != "Any" and rec["status"] != self.f_status.currentText():
                continue
            if self.f_bank.currentText() != "Any" and rec.get("bank_status", "") != self.f_bank.currentText():
                continue
            out.append(rec)
        return sorted(out, key=self._sort_key, reverse=not self.sort_ascending)

    def _sort_key(self, rec: dict[str, str]):
        field = self.sort_field
        value = rec.get(field, "")
        if field in {"deposit_amount", "final_amount", "profit"}:
            d = parse_decimal(value)
            return (d is None, d or 0)
        if field == "promo_start_date":
            dt = parse_date(value)
            return (dt is None, dt)
        if field == "status":
            return CASINO_STATUS_ORDER.get(value, 999)
        return (value or "").lower()

    def sort_by_column(self, col: int) -> None:
        mapping = {0: "status", 1: "bookie", 2: "promo_start_date", 3: "promo_name", 4: "deposit_amount", 5: "final_amount", 6: "bank_status", 7: "profit", 8: "notes"}
        field = mapping.get(col)
        if not field:
            return
        if self.sort_field == field:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_field = field
            self.sort_ascending = True
        self.render_table()

    def render_table(self) -> None:
        visible = self._visible_records()
        self._last_visible_records = visible
        self.visible_record_ids = [r["id"] for r in visible]
        self.table.setUpdatesEnabled(False)
        self.table.clearContents()
        self.row_to_record_id.clear()
        self.widget_map.clear()
        self.table.setRowCount(len(visible))
        for row, rec in enumerate(visible):
            self.row_to_record_id[row] = rec["id"]
            self._render_row(row, rec)
        self._applying_col_widths = True
        try:
            for i, w in enumerate(self.col_widths):
                self.table.setColumnWidth(i, w)
        finally:
            self._applying_col_widths = False
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setUpdatesEnabled(True)
        self._restore_selection()
        self._refresh_header_metrics(visible)

    def _on_section_resized(self, index: int, _old_size: int, new_size: int) -> None:
        if self._applying_col_widths:
            return
        if not 0 <= index < len(self.col_widths):
            return
        if new_size <= 0:
            return
        self.col_widths[index] = new_size
        self.settings_timer.start()

    def _save_column_widths(self) -> None:
        self.ui_settings.set_column_widths("casino", self.col_widths)

    def _restore_selection(self) -> None:
        target_row: int | None = None
        if self._startup_focus_pending:
            self._startup_focus_pending = False
            for row, rid in self.row_to_record_id.items():
                rec = next((r for r in self.records if r["id"] == rid), None)
                if rec and rec.get("status") != "Done":
                    target_row = row
                    break
        if target_row is None and self.active_record_id:
            for row, rid in self.row_to_record_id.items():
                if rid == self.active_record_id:
                    target_row = row
                    break
        if target_row is None and self.table.rowCount() > 0:
            target_row = 0
        if target_row is None:
            return
        self.table.setCurrentCell(target_row, 0)
        self.table.selectRow(target_row)
        item = self.table.item(target_row, 0)
        if item is not None:
            self.table.scrollToItem(item)

    def _render_row(self, row: int, rec: dict[str, str]) -> None:
        status = rec["status"]
        item = QTableWidgetItem(status)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        item.setTextAlignment(Qt.AlignCenter)
        item.setBackground(QBrush(QColor(status_color(status))))
        item.setForeground(QBrush(QColor(status_text_color(status))))
        self.table.setItem(row, 0, item)
        widgets = [
            self._bookie_widget(rec, row),
            self._date_widget(rec, row, "promo_start_date"),
            self._line_widget(rec, row, "promo_name"),
            self._line_widget(rec, row, "deposit_amount"),
            self._line_widget(rec, row, "final_amount"),
            self._combo_widget(rec, row, "bank_status", BANK),
            self._readonly_widget(rec.get("profit", "")),
            self._line_widget(rec, row, "notes"),
        ]
        for col, widget in enumerate(widgets, start=1):
            self.table.setCellWidget(row, col, widget)

    def _readonly_widget(self, value: str) -> QWidget:
        edit = QLineEdit(self.table)
        edit.setReadOnly(True)
        edit.setProperty("role", "cellEditor")
        edit.setAlignment(Qt.AlignRight)
        edit.setText(value)
        return edit

    def _register_widget(self, widget: QWidget, record_id: str, row: int, field: str) -> QWidget:
        widget.setProperty("record_id", record_id)
        widget.setProperty("row", row)
        widget.setProperty("nav_field", field)
        widget.installEventFilter(self)
        self.widget_map[(record_id, field)] = widget
        if isinstance(widget, NullableDateWidget):
            widget.edit.setProperty("record_id", record_id)
            widget.edit.setProperty("row", row)
            widget.edit.setProperty("nav_field", field)
            widget.edit.installEventFilter(self)
        elif isinstance(widget, LinkLineWidget):
            widget.edit.setProperty("record_id", record_id)
            widget.edit.setProperty("row", row)
            widget.edit.setProperty("nav_field", field)
            widget.edit.installEventFilter(self)
            widget.open_btn.setProperty("record_id", record_id)
            widget.open_btn.setProperty("row", row)
            widget.open_btn.setProperty("nav_field", field)
            widget.open_btn.installEventFilter(self)
        return widget

    def _bookie_widget(self, rec: dict[str, str], row: int) -> QWidget:
        combo = QComboBox(self.table)
        combo.setEditable(True)
        combo.setProperty("role", "cellEditor")
        combo.addItems(self._bookie_options())
        combo.setCurrentText(rec.get("bookie", ""))
        if combo.lineEdit() is not None:
            combo.lineEdit().setProperty("role", "cellEditor")
        combo.lineEdit().editingFinished.connect(partial(self._bookie_changed, rec["id"], combo))
        combo.activated.connect(partial(self._bookie_changed, rec["id"], combo))
        return self._register_widget(combo, rec["id"], row, "bookie")

    def _combo_widget(self, rec: dict[str, str], row: int, field: str, values: list[str]) -> QWidget:
        combo = QComboBox(self.table)
        combo.setProperty("role", "cellEditor")
        combo.addItems(values)
        idx = combo.findText(rec.get(field, ""))
        combo.setCurrentIndex(max(0, idx))
        if combo.lineEdit() is not None:
            combo.lineEdit().setProperty("role", "cellEditor")
        combo.currentTextChanged.connect(partial(self._combo_changed, rec["id"], row, field))
        return self._register_widget(combo, rec["id"], row, field)

    def _line_widget(self, rec: dict[str, str], row: int, field: str) -> QWidget:
        widget = LinkLineWidget(rec.get(field, ""), self.table)
        widget.edit.setProperty("role", "cellEditor")
        widget.edit.editingFinished.connect(partial(self._line_changed, rec["id"], row, field, widget.edit))
        return self._register_widget(widget, rec["id"], row, field)

    def _date_widget(self, rec: dict[str, str], row: int, field: str) -> QWidget:
        w = NullableDateWidget(rec.get(field, ""), self.table)
        w.edit.setProperty("role", "cellEditor")
        w.textChanged.connect(partial(self._value_changed, rec["id"], row, field))
        return self._register_widget(w, rec["id"], row, field)

    def _set_metric_chip(self, chip: QLabel, label: str, value: int, state: str) -> None:
        chip.setText(f"{label}: {value}")
        chip.setProperty("state", state)
        chip.style().unpolish(chip)
        chip.style().polish(chip)
        chip.update()

    def _refresh_header_metrics(self, records: list[dict[str, str]] | None = None) -> None:
        visible_records = records if records is not None else self._last_visible_records
        total = len(visible_records)

        action = 0
        progress = 0
        done = 0
        risk = 0
        neutral = 0
        for record in visible_records:
            group = status_feedback_group(record.get("status", "NotStarted"))
            if group == "action":
                action += 1
            elif group == "progress":
                progress += 1
            elif group == "success":
                done += 1
            elif group == "risk":
                risk += 1
            else:
                neutral += 1

        selection_model = self.table.selectionModel()
        selected = len(selection_model.selectedRows()) if selection_model is not None else 0

        self._set_metric_chip(self.total_chip, "Total", total, "neutral")
        self._set_metric_chip(self.action_chip, "Need Action", action, "warning" if action else "neutral")
        self._set_metric_chip(self.progress_chip, "Waiting", progress, "info" if progress else "neutral")
        self._set_metric_chip(self.done_chip, "Done", done, "success" if done else "neutral")
        self._set_metric_chip(self.risk_chip, "Error", risk, "error" if risk else "neutral")

        sort_label = self.sort_field.replace("_", " ").title()
        sort_order = "ASC" if self.sort_ascending else "DESC"
        self.view_hint_label.setText(
            f"Sort: {sort_label} {sort_order} · Visible: {total} · Idle: {neutral} · Selected: {selected}"
        )

    def eventFilter(self, watched, event):  # noqa: ANN001
        if event.type() in {QEvent.MouseButtonPress, QEvent.FocusIn}:
            row = watched.property("row")
            rid = watched.property("record_id")
            if isinstance(row, int):
                self.table.selectRow(row)
            if isinstance(rid, str):
                self.active_record_id = rid
        if event.type() == QEvent.KeyPress and self._handle_nav_key(watched, event):
            return True
        return super().eventFilter(watched, event)

    def _handle_nav_key(self, watched, event) -> bool:  # noqa: ANN001
        rid = watched.property("record_id")
        field = watched.property("nav_field")
        if not isinstance(rid, str) or not isinstance(field, str):
            return False
        if isinstance(watched, QComboBox) and watched.view().isVisible():
            return False
        key = event.key()
        if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab):
            self._focus_relative(rid, field, 1)
            return True
        if key == Qt.Key_Backtab:
            self._focus_relative(rid, field, -1)
            return True
        if key == Qt.Key_Down:
            self._focus_vertical(rid, field, 1)
            return True
        if key == Qt.Key_Up:
            self._focus_vertical(rid, field, -1)
            return True
        return False

    def _nav_order(self) -> list[tuple[str, str]]:
        order: list[tuple[str, str]] = []
        for rid in self.visible_record_ids:
            for field in NAV_FIELDS:
                if (rid, field) in self.widget_map:
                    order.append((rid, field))
        return order

    def _focus_relative(self, rid: str, field: str, delta: int) -> None:
        order = self._nav_order()
        try:
            idx = order.index((rid, field))
        except ValueError:
            return
        idx += delta
        if 0 <= idx < len(order):
            self._focus_key(order[idx])

    def _focus_vertical(self, rid: str, field: str, delta: int) -> None:
        try:
            idx = self.visible_record_ids.index(rid)
        except ValueError:
            return
        idx += delta
        while 0 <= idx < len(self.visible_record_ids):
            key = (self.visible_record_ids[idx], field)
            if key in self.widget_map:
                self._focus_key(key)
                return
            idx += delta

    def _focus_key(self, key: tuple[str, str]) -> None:
        widget = self.widget_map.get(key)
        if widget is None:
            return
        row = widget.property("row")
        if isinstance(row, int):
            self.table.setCurrentCell(row, 0)
            self.table.selectRow(row)
        self.active_record_id = key[0]
        if isinstance(widget, NullableDateWidget):
            widget.edit.setFocus(); widget.edit.selectAll()
        elif isinstance(widget, QComboBox):
            widget.setFocus()
            if widget.isEditable() and widget.lineEdit():
                widget.lineEdit().selectAll()
        elif isinstance(widget, QLineEdit):
            widget.setFocus(); widget.selectAll()
        else:
            widget.setFocus()

    def _bookie_changed(self, record_id: str, combo: QComboBox, *args) -> None:
        self._set_record_value(record_id, "bookie", combo.currentText().strip())

    def _line_changed(self, record_id: str, row: int, field: str, edit: QLineEdit) -> None:
        self.table.selectRow(row)
        value = edit.text().strip()
        normalized = normalize_web_url(value)
        self._set_record_value(record_id, field, normalized or value)

    def _combo_changed(self, record_id: str, row: int, field: str, value: str) -> None:
        self.table.selectRow(row)
        self._set_record_value(record_id, field, value)

    def _value_changed(self, record_id: str, row: int, field: str, value: str) -> None:
        self.table.selectRow(row)
        self._set_record_value(record_id, field, value)

    def _set_record_value(self, record_id: str, field: str, value: str) -> None:
        rec = next((r for r in self.records if r["id"] == record_id), None)
        if rec is None or rec.get(field, "") == value:
            return
        if field == "deposit_amount":
            d = parse_decimal(value)
            if value and d is None:
                QMessageBox.warning(self, "Invalid value", "Dep must be a number.")
                self.render_table(); return
            if d is not None and d < 0:
                QMessageBox.warning(self, "Invalid value", "Dep cannot be negative.")
                self.render_table(); return
        if field == "final_amount" and value and parse_decimal(value) is None:
            QMessageBox.warning(self, "Invalid value", "Final must be a number.")
            self.render_table(); return
        self._push_undo()
        rec[field] = value
        rec["profit"] = compute_casino_profit(rec)
        rec["status"] = compute_casino_status(rec)
        self.active_record_id = record_id
        self.schedule_save()
        self.render_table()
