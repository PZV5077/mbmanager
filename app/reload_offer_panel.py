from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEasingCurve, QDate, QPropertyAnimation, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QCalendarWidget,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .constants import BETTING_B_TYPES, BETTING_Q_TYPES
from .ledger_common import set_metric_chip
from .storage import AppDatabase
from .utils import fmt_decimal, new_id, parse_decimal
from .widgets import NullableDateTimeWidget

_TEMPLATE_DATETIME_FMT = "%Y-%m-%d %H:%M"
_STATUS_LABELS = {
    "NotStarted": "Not started",
    "NeedQBet": "Ready for bet",
    "WaitQResult": "Waiting bet result",
    "NeedBBet": "Ready for bonus",
    "WaitBResult": "Waiting bonus result",
    "NeedBank": "Ready for bank",
    "Done": "Completed",
    "Error": "Error",
}
_WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _today() -> date:
    return datetime.now().date()


def _iso_date(value: date) -> str:
    return value.strftime("%Y-%m-%d")


def _parse_iso_date(value: str) -> date | None:
    try:
        return datetime.strptime((value or "").strip(), "%Y-%m-%d").date()
    except ValueError:
        return None


def _parse_template_datetime(value: str) -> datetime | None:
    try:
        return datetime.strptime((value or "").strip(), _TEMPLATE_DATETIME_FMT)
    except ValueError:
        return None


def _weekday_from_date_text(value: str) -> int:
    parsed = _parse_template_datetime(value)
    if parsed is None:
        return datetime.now().weekday()
    return parsed.weekday()


def _monthday_from_date_text(value: str) -> int:
    parsed = _parse_template_datetime(value)
    if parsed is None:
        return datetime.now().day
    return parsed.day


def _normalize_amount(value: str) -> str:
    text = (value or "").strip()
    if not text:
        return ""
    dec = parse_decimal(text)
    if dec is None or dec < 0:
        raise ValueError(f"Invalid amount: {value}")
    return fmt_decimal(dec)


def _blank_template() -> dict[str, str]:
    now = datetime.now().replace(second=0, microsecond=0)
    return {
        "id": new_id(),
        "enabled": "Yes",
        "start_at": now.strftime(_TEMPLATE_DATETIME_FMT),
        "bookie": "",
        "promo_name": "",
        "repeat_mode": "weekly",
        "repeat_weekday": str(now.weekday()),
        "repeat_monthday": str(now.day),
        "deposit_amount": "",
        "bet_amount": "",
        "bet_type": "",
        "bonus_amount": "",
        "bonus_type": "",
        "notes": "",
    }


def _template_label(template: dict[str, str]) -> str:
    bookie = (template.get("bookie") or "").strip() or "Unnamed bookie"
    promo = (template.get("promo_name") or "").strip() or "Unnamed template"
    status = "" if template.get("enabled", "Yes") == "Yes" else " · Disabled"
    return f"{bookie} · {promo}{status}"


def _status_label(status: str) -> str:
    return _STATUS_LABELS.get(status, status or "Not started")


def _template_to_instance_status(betting_status: str, linked: bool) -> str:
    if not linked:
        return "Not started"
    return _STATUS_LABELS.get(betting_status, "Record created")


def _calendar_date_format(selected: QDate) -> str:
    return f"Date: {selected.toString('yyyy-MM-dd')} · {_WEEKDAY_LABELS[selected.dayOfWeek() - 1]}"


class ReloadOfferTemplateDialog(QDialog):
    def __init__(self, data_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Reload Offer Templates")
        self.resize(980, 620)
        self.db = AppDatabase(data_dir)
        self.templates = self.db.fetch_reload_offer_templates()
        self._loading_form = False

        if not self.templates:
            self.templates = [_blank_template()]

        self._build_ui()
        self._populate_list()
        self.template_list.setCurrentRow(0)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("Reload Offer Templates", self)
        title.setProperty("role", "panelTitle")
        subtitle = QLabel("", self)
        subtitle.setProperty("role", "panelSubtitle")

        header = QFrame(self)
        header.setObjectName("workspaceHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(2)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        root.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)

        left_panel = QFrame(splitter)
        left_panel.setObjectName("filterPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        left_title = QLabel("Template list", left_panel)
        left_title.setProperty("role", "sectionLabel")

        self.template_list = QListWidget(left_panel)
        self.template_list.currentRowChanged.connect(self._on_row_changed)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(6)

        self.add_btn = QPushButton("Add", left_panel)
        self.add_btn.setProperty("variant", "primary")
        self.add_btn.clicked.connect(self._add_template)

        self.copy_btn = QPushButton("Duplicate", left_panel)
        self.copy_btn.setProperty("variant", "secondary")
        self.copy_btn.clicked.connect(self._copy_template)

        self.delete_btn = QPushButton("Delete", left_panel)
        self.delete_btn.setProperty("variant", "danger")
        self.delete_btn.clicked.connect(self._delete_template)

        button_row.addWidget(self.add_btn)
        button_row.addWidget(self.copy_btn)
        button_row.addWidget(self.delete_btn)

        left_layout.addWidget(left_title)
        left_layout.addWidget(self.template_list, 1)
        left_layout.addLayout(button_row)

        right_panel = QFrame(splitter)
        right_panel.setObjectName("filterPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(10)

        form_wrap = QWidget(right_panel)
        form = QFormLayout(form_wrap)
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.enabled_box = QCheckBox("Enabled", form_wrap)
        self.start_at_widget = NullableDateTimeWidget("", form_wrap)
        self.bookie_edit = QLineEdit(form_wrap)
        self.promo_name_edit = QLineEdit(form_wrap)
        self.repeat_mode_combo = QComboBox(form_wrap)
        self.repeat_mode_combo.addItems(["weekly", "monthly"])
        self.repeat_weekday_combo = QComboBox(form_wrap)
        self.repeat_weekday_combo.addItems(_WEEKDAY_LABELS)
        self.repeat_monthday_spin = QSpinBox(form_wrap)
        self.repeat_monthday_spin.setRange(1, 31)
        self.deposit_amount_edit = QLineEdit(form_wrap)
        self.bet_amount_edit = QLineEdit(form_wrap)
        self.bet_type_combo = QComboBox(form_wrap)
        self.bet_type_combo.setEditable(True)
        self.bet_type_combo.addItems(BETTING_Q_TYPES)
        self.bonus_amount_edit = QLineEdit(form_wrap)
        self.bonus_type_combo = QComboBox(form_wrap)
        self.bonus_type_combo.setEditable(True)
        self.bonus_type_combo.addItems(BETTING_B_TYPES)
        self.notes_edit = QLineEdit(form_wrap)

        form.addRow("Template status", self.enabled_box)
        form.addRow("Start at", self.start_at_widget)
        form.addRow("Bookie", self.bookie_edit)
        form.addRow("Promo name", self.promo_name_edit)
        form.addRow("Repeat mode", self.repeat_mode_combo)
        form.addRow("Weekly day", self.repeat_weekday_combo)
        form.addRow("Monthly day", self.repeat_monthday_spin)
        form.addRow("Deposit amount", self.deposit_amount_edit)
        form.addRow("Bet amount", self.bet_amount_edit)
        form.addRow("Bet type", self.bet_type_combo)
        form.addRow("Bonus amount", self.bonus_amount_edit)
        form.addRow("Bonus type", self.bonus_type_combo)
        form.addRow("Note", self.notes_edit)

        right_layout.addWidget(form_wrap)
        right_layout.addStretch(1)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 640])
        root.addWidget(splitter, 1)

        footer = QFrame(self)
        footer.setObjectName("actionBar")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(10, 8, 10, 8)
        footer_layout.setSpacing(8)

        footer_hint = QLabel("", footer)
        footer_hint.setProperty("role", "metaInfo")

        self.cancel_btn = QPushButton("Cancel", footer)
        self.cancel_btn.setProperty("variant", "ghost")
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Save templates", footer)
        self.save_btn.setProperty("variant", "primary")
        self.save_btn.clicked.connect(self.accept)

        footer_layout.addWidget(footer_hint)
        footer_layout.addStretch(1)
        footer_layout.addWidget(self.cancel_btn)
        footer_layout.addWidget(self.save_btn)
        root.addWidget(footer)

        for widget in (
            self.enabled_box,
            self.bookie_edit,
            self.promo_name_edit,
            self.repeat_mode_combo,
            self.repeat_weekday_combo,
            self.repeat_monthday_spin,
            self.deposit_amount_edit,
            self.bet_amount_edit,
            self.bet_type_combo,
            self.bonus_amount_edit,
            self.bonus_type_combo,
            self.notes_edit,
        ):
            if isinstance(widget, QCheckBox):
                widget.toggled.connect(self._form_changed)
            elif isinstance(widget, QLineEdit):
                widget.textChanged.connect(self._form_changed)
            elif isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(self._form_changed)
                if widget.isEditable() and widget.lineEdit() is not None:
                    widget.lineEdit().textChanged.connect(self._form_changed)
            elif isinstance(widget, QSpinBox):
                widget.valueChanged.connect(self._form_changed)

        self.start_at_widget.textChanged.connect(self._form_changed)
        self.repeat_mode_combo.currentTextChanged.connect(self._refresh_repeat_mode)
        for combo in (
            self.repeat_mode_combo,
            self.repeat_weekday_combo,
            self.bet_type_combo,
            self.bonus_type_combo,
        ):
            self._normalize_combo_popup(combo)
        self._refresh_repeat_mode(self.repeat_mode_combo.currentText())

    def _normalize_combo_popup(self, combo: QComboBox) -> None:
        view = combo.view()
        if view is None:
            return
        view.setStyleSheet("")
        model = combo.model()
        for row in range(combo.count()):
            index = model.index(row, 0)
            model.setData(index, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), Qt.ItemDataRole.TextAlignmentRole)

    def _populate_list(self) -> None:
        self.template_list.blockSignals(True)
        self.template_list.clear()
        for template in self.templates:
            self.template_list.addItem(QListWidgetItem(_template_label(template)))
        self.template_list.blockSignals(False)
        self._update_delete_state()

    def _update_delete_state(self) -> None:
        self.delete_btn.setEnabled(bool(self.templates))
        self.copy_btn.setEnabled(bool(self.templates))

    def _on_row_changed(self, row: int) -> None:
        self._load_template_to_form(row)
        self._update_delete_state()

    def _load_template_to_form(self, row: int) -> None:
        self._loading_form = True
        try:
            template = self.templates[row] if 0 <= row < len(self.templates) else _blank_template()
            self.enabled_box.setChecked(template.get("enabled", "Yes") == "Yes")
            self.start_at_widget.set_text(template.get("start_at", ""))
            self.bookie_edit.setText(template.get("bookie", ""))
            self.promo_name_edit.setText(template.get("promo_name", ""))
            self.repeat_mode_combo.setCurrentText(template.get("repeat_mode", "weekly") or "weekly")
            self.repeat_weekday_combo.setCurrentIndex(max(0, min(6, int(template.get("repeat_weekday", "0") or "0"))))
            self.repeat_monthday_spin.setValue(max(1, min(31, int(template.get("repeat_monthday", "1") or "1"))))
            self.deposit_amount_edit.setText(template.get("deposit_amount", ""))
            self.bet_amount_edit.setText(template.get("bet_amount", ""))
            self.bet_type_combo.setCurrentText(template.get("bet_type", ""))
            self.bonus_amount_edit.setText(template.get("bonus_amount", ""))
            self.bonus_type_combo.setCurrentText(template.get("bonus_type", ""))
            self.notes_edit.setText(template.get("notes", ""))
            self._refresh_repeat_mode(self.repeat_mode_combo.currentText())
        finally:
            self._loading_form = False

    def _save_current_form(self) -> None:
        row = self.template_list.currentRow()
        if not 0 <= row < len(self.templates):
            return
        start_at_text = self.start_at_widget.text().strip()
        self.templates[row] = {
            "id": self.templates[row].get("id") or new_id(),
            "enabled": "Yes" if self.enabled_box.isChecked() else "No",
            "start_at": start_at_text,
            "bookie": self.bookie_edit.text().strip(),
            "promo_name": self.promo_name_edit.text().strip(),
            "repeat_mode": self.repeat_mode_combo.currentText().strip() or "weekly",
            "repeat_weekday": str(self.repeat_weekday_combo.currentIndex()),
            "repeat_monthday": str(self.repeat_monthday_spin.value()),
            "deposit_amount": self.deposit_amount_edit.text().strip(),
            "bet_amount": self.bet_amount_edit.text().strip(),
            "bet_type": self.bet_type_combo.currentText().strip(),
            "bonus_amount": self.bonus_amount_edit.text().strip(),
            "bonus_type": self.bonus_type_combo.currentText().strip(),
            "notes": self.notes_edit.text().strip(),
        }
        if start_at_text:
            self.templates[row]["repeat_weekday"] = str(_weekday_from_date_text(start_at_text))
            self.templates[row]["repeat_monthday"] = str(_monthday_from_date_text(start_at_text))
            self.repeat_weekday_combo.setCurrentIndex(int(self.templates[row]["repeat_weekday"]))
            self.repeat_monthday_spin.setValue(int(self.templates[row]["repeat_monthday"]))
        item = self.template_list.item(row)
        if item is not None:
            item.setText(_template_label(self.templates[row]))

    def _form_changed(self, *args) -> None:
        if self._loading_form:
            return
        self._save_current_form()

    def _refresh_repeat_mode(self, mode: str) -> None:
        weekly = mode == "weekly"
        self.repeat_weekday_combo.setEnabled(weekly)
        self.repeat_monthday_spin.setEnabled(not weekly)

    def _add_template(self) -> None:
        self._save_current_form()
        self.templates.append(_blank_template())
        self._populate_list()
        self.template_list.setCurrentRow(len(self.templates) - 1)

    def _copy_template(self) -> None:
        row = self.template_list.currentRow()
        if not 0 <= row < len(self.templates):
            return
        self._save_current_form()
        source = dict(self.templates[row])
        source["id"] = new_id()
        source["promo_name"] = ((source.get("promo_name") or "").strip() + " Copy").strip()
        self.templates.insert(row + 1, source)
        self._populate_list()
        self.template_list.setCurrentRow(row + 1)

    def _delete_template(self) -> None:
        row = self.template_list.currentRow()
        if not 0 <= row < len(self.templates):
            return
        if QMessageBox.question(self, "Delete template", "Delete current template? Future unlinked tasks will be removed.") != QMessageBox.StandardButton.Yes:
            return
        self.templates.pop(row)
        if not self.templates:
            self.templates.append(_blank_template())
        self._populate_list()
        self.template_list.setCurrentRow(min(row, len(self.templates) - 1))

    def _validate_template(self, template: dict[str, str]) -> dict[str, str]:
        start_at = (template.get("start_at") or "").strip()
        if _parse_template_datetime(start_at) is None:
            raise ValueError("Start time is required and must match yyyy-MM-dd HH:mm.")

        bookie = (template.get("bookie") or "").strip()
        if not bookie:
            raise ValueError("Bookie name is required.")

        promo_name = (template.get("promo_name") or "").strip()
        if not promo_name:
            raise ValueError("Promo name is required.")

        repeat_mode = (template.get("repeat_mode") or "weekly").strip()
        if repeat_mode not in {"weekly", "monthly"}:
            raise ValueError("Repeat mode must be weekly or monthly.")

        bet_type = (template.get("bet_type") or "").strip()
        if bet_type and bet_type not in BETTING_Q_TYPES:
            raise ValueError("Bet type must use a supported value.")

        bonus_type = (template.get("bonus_type") or "").strip()
        if bonus_type and bonus_type not in BETTING_B_TYPES:
            raise ValueError("Bonus type must use a supported value.")

        weekday = int(template.get("repeat_weekday", "0") or "0")
        monthday = int(template.get("repeat_monthday", "1") or "1")

        return {
            "id": (template.get("id") or new_id()).strip(),
            "enabled": "Yes" if template.get("enabled", "Yes") == "Yes" else "No",
            "start_at": start_at,
            "bookie": bookie,
            "promo_name": promo_name,
            "repeat_mode": repeat_mode,
            "repeat_weekday": str(max(0, min(6, weekday))),
            "repeat_monthday": str(max(1, min(31, monthday))),
            "deposit_amount": _normalize_amount(template.get("deposit_amount", "")),
            "bet_amount": _normalize_amount(template.get("bet_amount", "")),
            "bet_type": bet_type,
            "bonus_amount": _normalize_amount(template.get("bonus_amount", "")),
            "bonus_type": bonus_type,
            "notes": (template.get("notes") or "").strip(),
        }

    def accept(self) -> None:
        self._save_current_form()
        normalized: list[dict[str, str]] = []
        try:
            for template in self.templates:
                normalized.append(self._validate_template(template))
        except ValueError as exc:
            QMessageBox.warning(self, "Template validation failed", str(exc))
            return

        horizon_start = _iso_date(_today() - timedelta(days=180))
        horizon_end = _iso_date(_today() + timedelta(days=365))
        self.db.replace_reload_offer_templates(normalized)
        self.db.refresh_reload_offer_instances(horizon_start, horizon_end)
        super().accept()


class ReloadOffersPanel(QWidget):
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

        title = QLabel("Reload Offers", header)
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
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(
            ["Status", "Bookie", "Promo", "Deposit", "Bet", "Bet type", "Bonus", "Bonus type", "Notes"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.cellClicked.connect(self._activate_selected_row)

        header_view = self.table.horizontalHeader()
        header_view.setStretchLastSection(True)
        for column, width in enumerate((120, 140, 180, 96, 96, 96, 96, 96)):
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
        hint = self.content.sizeHint().height()
        self._content_height_hint = max(self._content_height_hint, hint, 300)
        return self._content_height_hint

    def _on_calendar_changed(self) -> None:
        self._ensure_date_loaded(self.calendar.selectedDate())
        self._refresh_selected_date_label()
        self._render_table()

    def _open_template_dialog(self) -> None:
        dialog = ReloadOfferTemplateDialog(self.db.path.parent, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.refresh_panel()

    def _ensure_date_loaded(self, selected: QDate) -> None:
        chosen = date(selected.year(), selected.month(), selected.day())
        window_start = _iso_date(chosen - timedelta(days=60))
        window_end = _iso_date(chosen + timedelta(days=120))
        self.db.refresh_reload_offer_instances(window_start, window_end)

    def _selected_date_iso(self) -> str:
        selected = self.calendar.selectedDate()
        return _iso_date(date(selected.year(), selected.month(), selected.day()))

    def _render_table(self) -> None:
        self._render_guard = True
        try:
            records = self.db.fetch_reload_offer_instances_for_date(self._selected_date_iso())
            self.table.clearContents()
            self.table.setRowCount(len(records))
            self._records = records

            for row, record in enumerate(records):
                values = [
                    record.get("status", "Not started"),
                    record.get("bookie", ""),
                    record.get("promo_name", ""),
                    record.get("deposit_amount", ""),
                    record.get("bet_amount", ""),
                    record.get("bet_type", ""),
                    record.get("bonus_amount", ""),
                    record.get("bonus_type", ""),
                    record.get("notes", ""),
                ]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    if column in {3, 4, 6}:
                        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.table.setItem(row, column, item)

            if records:
                self.empty_label.setText("")
            else:
                self.empty_label.setText("No reload offers for this date.")
        finally:
            self._render_guard = False

    def _refresh_summary(self) -> None:
        today_records = self.db.fetch_reload_offer_instances_for_date(_iso_date(_today()))
        total = len(today_records)
        done = sum(1 for record in today_records if record.get("status") == _status_label("Done"))
        error = sum(1 for record in today_records if record.get("status") == _status_label("Error"))
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
        self.db.set_reload_offer_instance_betting_record(instance.get("id", ""), record_id)
        self.refresh_panel()


__all__ = ["ReloadOffersPanel", "ReloadOfferTemplateDialog"]
