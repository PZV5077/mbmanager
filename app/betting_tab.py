from __future__ import annotations

from copy import deepcopy
from functools import partial
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .constants import (
    BETTING_BANK_VALUES,
    BETTING_B_EXCHANGES,
    BETTING_B_TYPES,
    BETTING_COL_WIDTHS,
    BETTING_HEADERS,
    BETTING_Q_EXCHANGES,
    BETTING_Q_TYPES,
    BETTING_SORT_COLUMNS,
    BETTING_STATUS_ORDER,
    BETTING_STATUS_VALUES,
)
from .ledger_common import selected_record_ids, set_metric_chip, status_group_counts, view_hint_text
from .storage import AppDatabase
from .ui_settings import UiSettingsStore
from .utils import (
    compute_betting_status,
    evaluate_profit_expression,
    fmt_decimal,
    new_id,
    parse_decimal,
    status_color,
    status_text_color,
)
from .widgets import LinkLineWidget, NullableDateTimeWidget, normalize_web_url


class BettingTab(QWidget):
    def __init__(
        self,
        data_dir: Path,
        parent: QWidget | None = None,
        on_records_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.db = AppDatabase(data_dir)
        self.ui_settings = UiSettingsStore(data_dir)
        self.on_records_changed = on_records_changed

        self.sort_field = "start_at"
        self.sort_ascending = False
        self.active_record_id: str | None = None
        self.undo_stack: list[tuple[list[dict[str, str]], str | None]] = []
        self.redo_stack: list[tuple[list[dict[str, str]], str | None]] = []
        self.row_to_record_id: dict[int, str] = {}
        self.record_by_id: dict[str, dict[str, str]] = {}
        self._copy_snapshot_ids: list[str] = []
        self._delete_snapshot_ids: list[str] = []
        self._startup_focus_pending = True
        self._applying_col_widths = False
        self._last_visible_records: list[dict[str, str]] = []
        self.col_widths = self.ui_settings.get_column_widths("betting_v2", BETTING_COL_WIDTHS, len(BETTING_HEADERS))

        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.setInterval(250)
        self.save_timer.timeout.connect(self._notify_records_changed)

        self.settings_timer = QTimer(self)
        self.settings_timer.setSingleShot(True)
        self.settings_timer.setInterval(300)
        self.settings_timer.timeout.connect(self._save_column_widths)

        self._build_ui()
        self.render_table()

    def _build_ui(self) -> None:
        title = QLabel("Betting Ledger", self)
        title.setProperty("role", "panelTitle")

        subtitle = QLabel("Track qualifying and bonus legs with faster row-level editing.", self)
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
        self.search_edit.setPlaceholderText("Search Bookie / Promo / Notes / Bet Target")
        self.search_edit.setProperty("role", "toolbarSearch")
        self.search_edit.textChanged.connect(self.render_table)

        self.status_filter = QComboBox(self)
        self.status_filter.addItems(["Any", *BETTING_STATUS_VALUES])
        self.status_filter.setProperty("role", "toolbarSelect")
        self.status_filter.currentTextChanged.connect(self.render_table)

        self.bank_filter = QComboBox(self)
        self.bank_filter.addItems(["Any", *BETTING_BANK_VALUES])
        self.bank_filter.setProperty("role", "toolbarSelect")
        self.bank_filter.currentTextChanged.connect(self.render_table)

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

        self.copy_btn = QPushButton("Copy Selected", self)
        self.copy_btn.setProperty("variant", "secondary")
        self.copy_btn.clicked.connect(self.copy_selected)
        self.copy_btn.pressed.connect(self._capture_copy_selection)

        self.delete_btn = QPushButton("Delete Selected", self)
        self.delete_btn.setProperty("variant", "danger")
        self.delete_btn.clicked.connect(self.delete_selected)
        self.delete_btn.pressed.connect(self._capture_delete_selection)

        controls = QFrame(self)
        self.controls_bar = controls
        controls.setObjectName("controlBar")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(10, 8, 10, 8)
        controls_layout.setSpacing(8)

        filters_label = QLabel("Filters", controls)
        filters_label.setProperty("role", "sectionLabel")
        status_label = QLabel("Status", controls)
        status_label.setProperty("role", "fieldLabel")
        bank_label = QLabel("Bank", controls)
        bank_label.setProperty("role", "fieldLabel")

        controls_layout.addWidget(filters_label)
        controls_layout.addWidget(status_label)
        controls_layout.addWidget(self.status_filter)
        controls_layout.addWidget(bank_label)
        controls_layout.addWidget(self.bank_filter)
        controls_layout.addWidget(self.search_edit, 1)
        controls_layout.addWidget(self.clear_filters_btn)
        controls_layout.addWidget(self.undo_btn)
        controls_layout.addWidget(self.redo_btn)

        actions = QFrame(self)
        self.actions_bar = actions
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

        self.table = QTableWidget(self)
        self.table.setObjectName("ledgerTable")
        self.table.setColumnCount(len(BETTING_HEADERS))
        self.table.setHorizontalHeaderLabels(BETTING_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(44)
        self.table.verticalHeader().setMinimumSectionSize(32)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionsMovable(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().sectionClicked.connect(self.sort_by_column)
        self.table.horizontalHeader().sectionResized.connect(self._on_section_resized)
        self.table.itemSelectionChanged.connect(self._remember_active_selection)

        root = QVBoxLayout(self)
        root.addWidget(header)
        root.addWidget(controls)
        root.addWidget(actions)
        root.addWidget(self.table, 1)

        self._refresh_header_metrics([])
        self._apply_compact_top_bars()

        QShortcut(QKeySequence.StandardKey.Undo, self, activated=self.undo_last_change)
        QShortcut(QKeySequence.StandardKey.Redo, self, activated=self.redo_last_change)

    def _apply_compact_top_bars(self) -> None:
        bar_height = 38
        for bar in (self.controls_bar, self.actions_bar):
            bar.setMinimumHeight(bar_height)
            bar.setMaximumHeight(bar_height)

        for layout in (self.controls_bar.layout(), self.actions_bar.layout()):
            if isinstance(layout, QHBoxLayout):
                layout.setContentsMargins(8, 3, 8, 3)
                layout.setSpacing(6)

        field_height = 24
        button_height = 24
        compact_font = QFont(self.font())
        compact_font.setPointSize(11)
        compact_font.setBold(False)
        button_font = QFont(self.font())
        button_font.setPointSize(11)
        button_font.setBold(True)

        self.search_edit.setFont(compact_font)
        self.search_edit.setMinimumHeight(field_height)
        self.search_edit.setMaximumHeight(field_height)
        self.search_edit.setTextMargins(6, 0, 6, 0)
        self.search_edit.setStyleSheet("QLineEdit { padding: 0px 6px; }")

        for combo in (self.status_filter, self.bank_filter):
            combo.setFont(compact_font)
            combo.setMinimumHeight(field_height)
            combo.setMaximumHeight(field_height)
            combo.setMaxVisibleItems(20)
            combo.setStyleSheet("QComboBox { padding: 0px 6px; combobox-popup: 0; }")
            self._normalize_combo_popup(combo)

        for button in (
            self.clear_filters_btn,
            self.undo_btn,
            self.redo_btn,
            self.add_btn,
            self.copy_btn,
            self.delete_btn,
        ):
            button.setFont(button_font)
            button.setMinimumHeight(button_height)
            button.setMaximumHeight(button_height)
            button.setStyleSheet("QPushButton { padding: 0px 10px; }")

    def _normalize_combo_popup(self, combo: QComboBox) -> None:
        view = combo.view()
        if view is None:
            return
        view.setStyleSheet("")
        view_font = QFont(combo.font())
        view.setFont(view_font)
        model = combo.model()
        for row in range(combo.count()):
            index = model.index(row, 0)
            model.setData(index, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), Qt.ItemDataRole.TextAlignmentRole)

    def clear_filters(self) -> None:
        self.status_filter.setCurrentIndex(0)
        self.bank_filter.setCurrentIndex(0)
        self.search_edit.clear()
        self.render_table()

    def _push_undo(self) -> None:
        snapshot = self.db.snapshot_betting_records()
        self.undo_stack.append((deepcopy(snapshot), self.active_record_id))
        self.undo_stack = self.undo_stack[-30:]
        self.redo_stack.clear()
        self._update_history_buttons()

    def _update_history_buttons(self) -> None:
        self.undo_btn.setEnabled(bool(self.undo_stack))
        self.redo_btn.setEnabled(bool(self.redo_stack))

    def undo_last_change(self) -> None:
        if not self.undo_stack:
            return
        self.redo_stack.append((self.db.snapshot_betting_records(), self.active_record_id))
        self.redo_stack = self.redo_stack[-30:]
        records, active_id = self.undo_stack.pop()
        self.db.replace_betting_records(records)
        self.active_record_id = active_id
        self._update_history_buttons()
        self.render_table()
        self._notify_records_changed()

    def redo_last_change(self) -> None:
        if not self.redo_stack:
            return
        self.undo_stack.append((self.db.snapshot_betting_records(), self.active_record_id))
        self.undo_stack = self.undo_stack[-30:]
        records, active_id = self.redo_stack.pop()
        self.db.replace_betting_records(records)
        self.active_record_id = active_id
        self._update_history_buttons()
        self.render_table()
        self._notify_records_changed()

    def add_record(self) -> None:
        self._push_undo()
        record = self._empty_record()
        self.db.insert_betting_record(record)
        self.active_record_id = record["id"]
        self.render_table()
        self.save_timer.start()

    def delete_selected(self) -> None:
        selected_ids = self._selected_record_ids(preferred=self._delete_snapshot_ids)
        self._delete_snapshot_ids = []

        if not selected_ids:
            QMessageBox.information(self, "Delete", "Select at least one record.")
            return

        count = len(selected_ids)
        prompt = "Delete the selected record?" if count == 1 else f"Delete {count} selected records?"
        if QMessageBox.question(self, "Delete", prompt) != QMessageBox.StandardButton.Yes:
            return

        self._push_undo()
        self.db.delete_betting_records(selected_ids)
        self.active_record_id = None
        self.render_table()
        self.save_timer.start()

    def copy_selected(self) -> None:
        selected_ids = self._selected_record_ids(preferred=self._copy_snapshot_ids)
        self._copy_snapshot_ids = []

        if not selected_ids:
            QMessageBox.information(self, "Copy", "Select at least one record.")
            return

        self._push_undo()
        inserted_ids: list[str] = []
        for record_id in selected_ids:
            source = self.db.get_betting_record(record_id)
            if source is None:
                continue
            copy_item = deepcopy(source)
            copy_item["id"] = new_id()
            copy_item["status"] = compute_betting_status(copy_item)
            self.db.insert_betting_record(copy_item)
            inserted_ids.append(copy_item["id"])

        if not inserted_ids:
            self.undo_stack.pop()
            self._update_history_buttons()
            return

        self.active_record_id = inserted_ids[-1]
        self.render_table()
        self.save_timer.start()

    def _capture_delete_selection(self) -> None:
        self._delete_snapshot_ids = self._selected_record_ids()

    def _capture_copy_selection(self) -> None:
        self._copy_snapshot_ids = self._selected_record_ids()

    def _selected_record_ids(self, preferred: list[str] | None = None) -> list[str]:
        return selected_record_ids(self.table, self.row_to_record_id, preferred)

    def _notify_records_changed(self) -> None:
        if callable(self.on_records_changed):
            self.on_records_changed()

    def _empty_record(self) -> dict[str, str]:
        return {
            "id": new_id(),
            "status": "NotStarted",
            "start_at": "",
            "bookie": "",
            "promo_name": "",
            "deposit_amount": "",
            "q_result_at": "",
            "q_event": "",
            "q_type": "",
            "q_amount": "",
            "q_target": "",
            "q_exchange": "",
            "q_is_placed": "No",
            "q_is_completed": "No",
            "b_result_at": "",
            "b_event": "",
            "b_type": "",
            "b_amount": "",
            "b_target": "",
            "b_exchange": "",
            "b_is_placed": "No",
            "b_is_completed": "No",
            "profit": "",
            "bank": "Uncon",
            "notes": "",
        }

    def _visible_records(self) -> list[dict[str, str]]:
        records = self.db.fetch_betting_records(
            search=self.search_edit.text(),
            status=self.status_filter.currentText(),
            bank=self.bank_filter.currentText(),
            sort_field=self.sort_field,
            ascending=self.sort_ascending,
        )
        if self.sort_field == "status":
            records.sort(
                key=lambda rec: (
                    BETTING_STATUS_ORDER.get(rec.get("status", ""), 999),
                    rec.get("start_at", ""),
                ),
                reverse=not self.sort_ascending,
            )
        return records

    def sort_by_column(self, col: int) -> None:
        field = BETTING_SORT_COLUMNS.get(col)
        if field is None:
            return
        if self.sort_field == field:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_field = field
            self.sort_ascending = True
        self.render_table()

    def render_table(self) -> None:
        records = self._visible_records()
        self._last_visible_records = records
        h_scroll = self.table.horizontalScrollBar().value()
        v_scroll = self.table.verticalScrollBar().value()
        self.table.setUpdatesEnabled(False)
        self.table.clearContents()

        self.row_to_record_id.clear()
        self.record_by_id.clear()
        self.table.setRowCount(len(records))

        for row, record in enumerate(records):
            self.row_to_record_id[row] = record["id"]
            self.record_by_id[record["id"]] = record
            self._render_row(row, record)

        self._applying_col_widths = True
        try:
            for index, width in enumerate(self.col_widths):
                self.table.setColumnWidth(index, width)
        finally:
            self._applying_col_widths = False

        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setUpdatesEnabled(True)
        self._restore_selection(records)
        self._restore_scroll_position(h_scroll, v_scroll)
        self._refresh_header_metrics(records)

    def _restore_scroll_position(self, horizontal: int, vertical: int) -> None:
        hbar = self.table.horizontalScrollBar()
        vbar = self.table.verticalScrollBar()
        hbar.setValue(max(hbar.minimum(), min(horizontal, hbar.maximum())))
        vbar.setValue(max(vbar.minimum(), min(vertical, vbar.maximum())))

    def _render_row(self, row: int, record: dict[str, str]) -> None:
        status = record.get("status", "NotStarted")
        status_item = QTableWidgetItem(status)
        status_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
        status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        status_item.setBackground(QBrush(QColor(status_color(status))))
        status_item.setForeground(QBrush(QColor(status_text_color(status))))
        self.table.setItem(row, 0, status_item)

        self.table.setCellWidget(row, 1, self._datetime_widget(record, row, "start_at"))
        self.table.setCellWidget(row, 2, self._bookie_widget(record, row))
        self.table.setCellWidget(row, 3, self._line_widget(record, row, "promo_name"))
        self.table.setCellWidget(row, 4, self._line_widget(record, row, "deposit_amount", numeric=True))
        self.table.setCellWidget(row, 5, self._datetime_widget(record, row, "q_result_at"))
        self.table.setCellWidget(row, 6, self._line_widget(record, row, "q_event"))
        self.table.setCellWidget(row, 7, self._combo_widget(record, row, "q_type", BETTING_Q_TYPES))
        self.table.setCellWidget(row, 8, self._line_widget(record, row, "q_amount", numeric=True))
        self.table.setCellWidget(row, 9, self._line_widget(record, row, "q_target", is_link=True))
        self.table.setCellWidget(row, 10, self._combo_widget(record, row, "q_exchange", BETTING_Q_EXCHANGES))
        self.table.setCellWidget(row, 11, self._check_widget(record, row, "q_is_placed"))
        self.table.setCellWidget(row, 12, self._check_widget(record, row, "q_is_completed"))
        self.table.setCellWidget(row, 13, self._datetime_widget(record, row, "b_result_at"))
        self.table.setCellWidget(row, 14, self._line_widget(record, row, "b_event"))
        self.table.setCellWidget(row, 15, self._combo_widget(record, row, "b_type", BETTING_B_TYPES))
        self.table.setCellWidget(row, 16, self._line_widget(record, row, "b_amount", numeric=True))
        self.table.setCellWidget(row, 17, self._line_widget(record, row, "b_target", is_link=True))
        self.table.setCellWidget(row, 18, self._combo_widget(record, row, "b_exchange", BETTING_B_EXCHANGES))
        self.table.setCellWidget(row, 19, self._check_widget(record, row, "b_is_placed"))
        self.table.setCellWidget(row, 20, self._check_widget(record, row, "b_is_completed"))
        self.table.setCellWidget(row, 21, self._line_widget(record, row, "profit", profit=True))
        self.table.setCellWidget(row, 22, self._combo_widget(record, row, "bank", BETTING_BANK_VALUES))
        self.table.setCellWidget(row, 23, self._line_widget(record, row, "notes"))

    def _bookie_widget(self, record: dict[str, str], row: int) -> QWidget:
        combo = QComboBox(self.table)
        combo.setEditable(True)
        combo.setProperty("role", "cellEditor")
        options = self.db.list_betting_bookies()
        combo.addItems(options)
        combo.setCurrentText(record.get("bookie", ""))
        self._normalize_combo_popup(combo)
        if combo.lineEdit() is not None:
            combo.lineEdit().setProperty("role", "cellEditor")
        combo.lineEdit().editingFinished.connect(partial(self._bookie_changed, record["id"], row, combo))
        combo.activated.connect(partial(self._bookie_changed, record["id"], row, combo))
        return combo

    def _combo_widget(self, record: dict[str, str], row: int, field: str, values: list[str]) -> QWidget:
        combo = QComboBox(self.table)
        combo.setProperty("role", "cellEditor")
        combo.addItems(values)
        idx = combo.findText(record.get(field, ""))
        combo.setCurrentIndex(max(0, idx))
        self._normalize_combo_popup(combo)
        if combo.lineEdit() is not None:
            combo.lineEdit().setProperty("role", "cellEditor")
        combo.currentTextChanged.connect(partial(self._combo_changed, record["id"], row, field))
        return combo

    def _line_widget(
        self,
        record: dict[str, str],
        row: int,
        field: str,
        *,
        numeric: bool = False,
        is_link: bool = False,
        profit: bool = False,
    ) -> QWidget:
        if is_link:
            widget = LinkLineWidget(record.get(field, ""), self.table)
            widget.edit.setProperty("role", "cellEditor")
            widget.edit.editingFinished.connect(
                partial(self._line_changed, record["id"], row, field, widget.edit, numeric, True, profit)
            )
            return widget

        edit = QLineEdit(self.table)
        edit.setProperty("role", "cellEditor")
        edit.setText(record.get(field, ""))
        if numeric or profit:
            edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        edit.editingFinished.connect(partial(self._line_changed, record["id"], row, field, edit, numeric, False, profit))
        return edit

    def _datetime_widget(self, record: dict[str, str], row: int, field: str) -> QWidget:
        widget = NullableDateTimeWidget(record.get(field, ""), self.table)
        widget.edit.setProperty("role", "cellEditor")
        widget.textChanged.connect(partial(self._value_changed, record["id"], row, field))
        return widget

    def _check_widget(self, record: dict[str, str], row: int, field: str) -> QWidget:
        wrap = QWidget(self.table)
        layout = QHBoxLayout(wrap)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch(1)

        box = QCheckBox(wrap)
        box.setProperty("role", "cellToggle")
        box.setChecked(record.get(field, "No") == "Yes")
        box.stateChanged.connect(partial(self._check_changed, record["id"], row, field, box))

        layout.addWidget(box)
        layout.addStretch(1)
        return wrap

    def _bookie_changed(self, record_id: str, row: int, combo: QComboBox, *args) -> None:
        self.table.selectRow(row)
        self._set_record_value(record_id, "bookie", combo.currentText().strip())

    def _combo_changed(self, record_id: str, row: int, field: str, value: str) -> None:
        self.table.selectRow(row)
        self._set_record_value(record_id, field, value)

    def _line_changed(
        self,
        record_id: str,
        row: int,
        field: str,
        edit: QLineEdit,
        numeric: bool,
        is_link: bool,
        profit: bool,
    ) -> None:
        self.table.selectRow(row)
        value = edit.text().strip()

        if profit:
            if value:
                try:
                    value = evaluate_profit_expression(value)
                except ValueError as exc:
                    QMessageBox.warning(self, "Invalid value", f"Profit formula is invalid:\n{exc}")
                    self.render_table()
                    return
            self._set_record_value(record_id, field, value)
            return

        if numeric and value:
            dec = parse_decimal(value)
            if dec is None:
                QMessageBox.warning(self, "Invalid value", f"{field} must be a number.")
                self.render_table()
                return
            if dec < 0:
                QMessageBox.warning(self, "Invalid value", f"{field} cannot be negative.")
                self.render_table()
                return
            value = fmt_decimal(dec)

        if is_link and value:
            value = normalize_web_url(value) or value

        self._set_record_value(record_id, field, value)

    def _value_changed(self, record_id: str, row: int, field: str, value: str) -> None:
        self.table.selectRow(row)
        self._set_record_value(record_id, field, value)

    def _check_changed(self, record_id: str, row: int, field: str, box: QCheckBox, _state: int) -> None:
        self.table.selectRow(row)
        self._set_record_value(record_id, field, "Yes" if box.isChecked() else "No")

    def _set_record_value(self, record_id: str, field: str, value: str) -> None:
        record = self.db.get_betting_record(record_id)
        if record is None:
            return

        old_value = record.get(field, "")
        if old_value == value:
            return

        self._push_undo()
        record[field] = value
        record["status"] = compute_betting_status(record)

        try:
            self.db.update_betting_record(record_id, record)
        except ValueError as exc:
            self.undo_stack.pop()
            self._update_history_buttons()
            QMessageBox.warning(self, "Invalid value", str(exc))
            self.render_table()
            return

        self.active_record_id = record_id
        self.render_table()
        self.save_timer.start()

    def _restore_selection(self, records: list[dict[str, str]]) -> None:
        target_row: int | None = None
        if self._startup_focus_pending:
            self._startup_focus_pending = False
            for row, record in enumerate(records):
                if record.get("status") != "Done":
                    target_row = row
                    break

        if target_row is None and self.active_record_id:
            for row, rid in self.row_to_record_id.items():
                if rid == self.active_record_id:
                    target_row = row
                    break

        if target_row is None and records:
            target_row = 0

        if target_row is None:
            return

        self.table.setCurrentCell(target_row, 0)
        self.table.selectRow(target_row)

    def _remember_active_selection(self) -> None:
        current_row = self.table.currentRow()
        record_id = self.row_to_record_id.get(current_row)
        if record_id:
            self.active_record_id = record_id
        self._refresh_header_metrics()

    def _refresh_header_metrics(self, records: list[dict[str, str]] | None = None) -> None:
        visible_records = records if records is not None else self._last_visible_records
        total = len(visible_records)
        counts = status_group_counts(visible_records)

        selected = len(self._selected_record_ids())

        set_metric_chip(self.total_chip, "Total", total, "neutral")
        set_metric_chip(self.action_chip, "Need Action", counts["action"], "warning" if counts["action"] else "neutral")
        set_metric_chip(self.progress_chip, "Waiting", counts["progress"], "info" if counts["progress"] else "neutral")
        set_metric_chip(self.done_chip, "Done", counts["success"], "success" if counts["success"] else "neutral")
        set_metric_chip(self.risk_chip, "Error", counts["risk"], "error" if counts["risk"] else "neutral")
        self.view_hint_label.setText(view_hint_text(self.sort_field, self.sort_ascending, total, counts["neutral"], selected))

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
        self.ui_settings.set_column_widths("betting_v2", self.col_widths)
