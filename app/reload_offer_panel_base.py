from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEasingCurve, QDate, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .ledger_common import set_metric_chip
from .storage import AppDatabase

_WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _today() -> date:
    return datetime.now().date()


def _iso_date(value: date) -> str:
    return value.strftime("%Y-%m-%d")


def _calendar_date_format(selected: QDate) -> str:
    return f"Date: {selected.toString('yyyy-MM-dd')} · {_WEEKDAY_LABELS[selected.dayOfWeek() - 1]}"


class ReloadOffersPanelBase(QWidget):
    def __init__(
        self,
        data_dir: Path,
        activate_instance: Callable[[dict[str, str]], str | None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.db = AppDatabase(data_dir)
        self.activate_instance = activate_instance
        self._expanded = True
        self._render_guard = False
        self._content_height_hint = 360
        self._records: list[dict[str, str]] = []

        self._build_ui()
        self.refresh_panel()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)
        self._root_layout = root

        header = QFrame(self)
        self._header = header
        header.setObjectName("workspaceHeader")
        header_layout = QHBoxLayout(header)
        self._header_layout = header_layout
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(8)

        header_left = QVBoxLayout()
        self._header_left_layout = header_left
        header_left.setContentsMargins(0, 0, 0, 0)
        header_left.setSpacing(2)

        title = QLabel(self._panel_title(), header)
        title.setProperty("role", "panelTitle")
        subtitle = QLabel("", header)
        subtitle.setProperty("role", "panelSubtitle")
        subtitle.setVisible(False)
        self.selected_date_label = QLabel("", header)
        self.selected_date_label.setProperty("role", "metaInfo")

        header_left.addWidget(title)
        header_left.addWidget(subtitle)
        header_left.addWidget(self.selected_date_label)

        chip_row = QHBoxLayout()
        self._chip_row_layout = chip_row
        chip_row.setContentsMargins(0, 0, 0, 0)
        chip_row.setSpacing(6)

        self.today_chip = QLabel(header)
        self.pending_chip = QLabel(header)
        self.done_chip = QLabel(header)
        self.error_chip = QLabel(header)
        for chip in (self.today_chip, self.pending_chip, self.done_chip, self.error_chip):
            chip.setProperty("role", "metricChip")
            chip.setProperty("state", "neutral")
            chip_row.addWidget(chip)

        self.template_btn = QPushButton("Templates", header)
        self.template_btn.setProperty("variant", "secondary")
        self.template_btn.setStyleSheet("padding: 1px 10px;")
        self.template_btn.clicked.connect(self._open_template_dialog)

        self.toggle_btn = QPushButton("Collapse", header)
        self.toggle_btn.setProperty("variant", "ghost")
        self.toggle_btn.setStyleSheet("padding: 1px 10px;")
        self.toggle_btn.clicked.connect(self._toggle_expanded)
        self._apply_header_button_widths()

        header_layout.addLayout(header_left, 1)
        header_layout.addLayout(chip_row)
        header_layout.addWidget(self.template_btn)
        header_layout.addWidget(self.toggle_btn)
        root.addWidget(header)

        self.content = QFrame(self)
        self.content.setObjectName("filterPanel")
        content_layout = QHBoxLayout(self.content)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)

        calendar_panel = QFrame(self.content)
        calendar_panel.setObjectName("actionBar")
        calendar_layout = QVBoxLayout(calendar_panel)
        calendar_layout.setContentsMargins(10, 10, 10, 10)
        calendar_layout.setSpacing(8)

        calendar_title = QLabel("Date", calendar_panel)
        calendar_title.setProperty("role", "sectionLabel")

        self.calendar = QCalendarWidget(calendar_panel)
        self.calendar.setGridVisible(False)
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.selectionChanged.connect(self._on_calendar_changed)

        calendar_layout.addWidget(calendar_title)
        calendar_layout.addWidget(self.calendar, 1)

        table_panel = QFrame(self.content)
        table_panel.setObjectName("actionBar")
        table_layout = QVBoxLayout(table_panel)
        table_layout.setContentsMargins(10, 10, 10, 10)
        table_layout.setSpacing(8)

        table_title = QLabel("Task table", table_panel)
        table_title.setProperty("role", "sectionLabel")
        self.empty_label = QLabel("", table_panel)
        self.empty_label.setProperty("role", "metaInfo")

        self.table = QTableWidget(table_panel)
        self.table.setObjectName("ledgerTable")
        headers = self._table_headers()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.cellClicked.connect(self._activate_selected_row)

        header_view = self.table.horizontalHeader()
        header_view.setStretchLastSection(True)
        for column, width in enumerate(self._table_column_widths()):
            header_view.resizeSection(column, width)

        table_layout.addWidget(table_title)
        table_layout.addWidget(self.empty_label)
        table_layout.addWidget(self.table, 1)

        content_layout.addWidget(calendar_panel, 0)
        content_layout.addWidget(table_panel, 1)
        root.addWidget(self.content)

        self.content_animation = QPropertyAnimation(self.content, b"maximumHeight", self)
        self.content_animation.setDuration(180)
        self.content_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        base_header_height = max(72, self._header.sizeHint().height())
        self._header_fixed_height = max(40, int(base_header_height * 0.5))
        self._header.setMinimumHeight(self._header_fixed_height)
        self._header.setMaximumHeight(self._header_fixed_height)
        self._apply_header_density(compact=False)
        self.content.setMaximumHeight(self._content_height_hint)

    def _apply_header_button_widths(self) -> None:
        template_metrics = self.template_btn.fontMetrics()
        toggle_metrics = self.toggle_btn.fontMetrics()
        template_width = template_metrics.horizontalAdvance("Templates") + 28
        toggle_width = max(
            toggle_metrics.horizontalAdvance("Collapse"),
            toggle_metrics.horizontalAdvance("Expand"),
        ) + 28
        self.template_btn.setFixedWidth(max(86, template_width))
        self.toggle_btn.setFixedWidth(max(84, toggle_width))

    def refresh_panel(self) -> None:
        self._ensure_date_loaded(self.calendar.selectedDate())
        self._refresh_selected_date_label()
        self._render_table()
        self._refresh_summary()

    def _refresh_selected_date_label(self) -> None:
        selected = self.calendar.selectedDate()
        self.selected_date_label.setText(_calendar_date_format(selected))

    def _toggle_expanded(self) -> None:
        self._expanded = not self._expanded
        target = self._content_target_height() if self._expanded else 0
        self.content_animation.stop()
        self.content.setMinimumHeight(0)
        self.content_animation.setStartValue(self.content.maximumHeight())
        self.content_animation.setEndValue(target)
        self.content_animation.start()
        self._apply_header_density(compact=not self._expanded)
        self.toggle_btn.setText("Collapse" if self._expanded else "Expand")

    def _apply_header_density(self, compact: bool) -> None:
        if compact:
            self._root_layout.setSpacing(6)
            self._header_layout.setContentsMargins(10, 4, 10, 4)
            self._header_layout.setSpacing(6)
            self._header_left_layout.setSpacing(0)
            self._chip_row_layout.setSpacing(4)
            self.selected_date_label.setVisible(False)
            self._header.setMinimumHeight(self._header_fixed_height)
            self._header.setMaximumHeight(self._header_fixed_height)
            control_height = 26
            for chip in (self.today_chip, self.pending_chip, self.done_chip, self.error_chip):
                chip.setMinimumHeight(control_height)
                chip.setMaximumHeight(control_height)
            for btn in (self.template_btn, self.toggle_btn):
                btn.setMinimumHeight(control_height)
                btn.setMaximumHeight(control_height)
            return

        self._root_layout.setSpacing(8)
        self._header_layout.setContentsMargins(10, 4, 10, 4)
        self._header_layout.setSpacing(8)
        self._header_left_layout.setSpacing(0)
        self._chip_row_layout.setSpacing(6)
        self.selected_date_label.setVisible(False)
        self._header.setMinimumHeight(self._header_fixed_height)
        self._header.setMaximumHeight(self._header_fixed_height)
        chip_height = 26
        button_height = 26
        for chip in (self.today_chip, self.pending_chip, self.done_chip, self.error_chip):
            chip.setMinimumHeight(chip_height)
            chip.setMaximumHeight(chip_height)
        for btn in (self.template_btn, self.toggle_btn):
            btn.setMinimumHeight(button_height)
            btn.setMaximumHeight(button_height)

    def _content_target_height(self) -> int:
        return self._content_height_hint

    def _on_calendar_changed(self) -> None:
        self._ensure_date_loaded(self.calendar.selectedDate())
        self._refresh_selected_date_label()
        self._render_table()

    def _open_template_dialog(self) -> None:
        dialog = self._create_template_dialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.refresh_panel()

    def _ensure_date_loaded(self, selected: QDate) -> None:
        chosen = date(selected.year(), selected.month(), selected.day())
        window_start = _iso_date(chosen - timedelta(days=60))
        window_end = _iso_date(chosen + timedelta(days=120))
        self._refresh_instances_window(window_start, window_end)

    def _selected_date_iso(self) -> str:
        selected = self.calendar.selectedDate()
        return _iso_date(date(selected.year(), selected.month(), selected.day()))

    def _render_table(self) -> None:
        self._render_guard = True
        try:
            records = self._fetch_instances_for_date(self._selected_date_iso())
            self.table.clearContents()
            self.table.setRowCount(len(records))
            self._records = records
            amount_columns = self._amount_columns()
            column_count = self.table.columnCount()

            for row, record in enumerate(records):
                values = self._record_values(record)
                for column in range(column_count):
                    value = values[column] if column < len(values) else ""
                    item = QTableWidgetItem(value)
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    if column in amount_columns:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(row, column, item)

            self.empty_label.setText("" if records else self._empty_state_text())
        finally:
            self._render_guard = False

    def _refresh_summary(self) -> None:
        today_records = self._fetch_instances_for_date(_iso_date(_today()))
        total = len(today_records)
        done = sum(1 for record in today_records if self._is_done_status(record.get("status", "")))
        error = sum(1 for record in today_records if self._is_error_status(record.get("status", "")))
        pending = total - done - error

        set_metric_chip(self.today_chip, "Today", total, "neutral")
        set_metric_chip(self.pending_chip, "Pending", pending, "warning" if pending else "neutral")
        set_metric_chip(self.done_chip, "Done", done, "success" if done else "neutral")
        set_metric_chip(self.error_chip, "Error", error, "error" if error else "neutral")

    def _activate_selected_row(self, row: int, _column: int) -> None:
        if self._render_guard or not 0 <= row < len(getattr(self, "_records", [])):
            return
        instance = self._records[row]
        record_id = self.activate_instance(instance)
        if not record_id:
            return
        self._link_instance_record(instance.get("id", ""), record_id)
        self.refresh_panel()

    def _panel_title(self) -> str:
        raise NotImplementedError

    def _table_headers(self) -> list[str]:
        raise NotImplementedError

    def _table_column_widths(self) -> tuple[int, ...]:
        raise NotImplementedError

    def _amount_columns(self) -> set[int]:
        return set()

    def _empty_state_text(self) -> str:
        raise NotImplementedError

    def _record_values(self, record: dict[str, str]) -> list[str]:
        raise NotImplementedError

    def _create_template_dialog(self, parent: QWidget) -> QDialog:
        raise NotImplementedError

    def _refresh_instances_window(self, window_start: str, window_end: str) -> None:
        raise NotImplementedError

    def _fetch_instances_for_date(self, date_iso: str) -> list[dict[str, str]]:
        raise NotImplementedError

    def _link_instance_record(self, instance_id: str, record_id: str) -> None:
        raise NotImplementedError

    def _is_done_status(self, status: str) -> bool:
        raise NotImplementedError

    def _is_error_status(self, status: str) -> bool:
        raise NotImplementedError
