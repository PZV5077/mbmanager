from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
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
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .constants import BETTING_B_TYPES, BETTING_Q_TYPES
from .reload_offer_panel_base import ReloadOffersPanelBase
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


class ReloadBettingOfferTemplateDialog(QDialog):
    def __init__(self, data_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Reload Betting Offer Templates")
        self.resize(980, 620)
        self.db = AppDatabase(data_dir)
        self.templates = self.db.fetch_reload_betting_offer_templates()
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

        title = QLabel("Reload Betting Offer Templates", self)
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
        self.db.replace_reload_betting_offer_templates(normalized)
        self.db.refresh_reload_betting_offer_instances(horizon_start, horizon_end)
        super().accept()


class ReloadBettingOffersPanel(ReloadOffersPanelBase):
    def _panel_title(self) -> str:
        return "Reload Betting Offers"

    def _table_headers(self) -> list[str]:
        return ["Status", "Bookie", "Promo", "Deposit", "Bet", "Bet type", "Bonus", "Bonus type", "Notes"]

    def _table_column_widths(self) -> tuple[int, ...]:
        return (120, 140, 180, 96, 96, 96, 96, 96)

    def _amount_columns(self) -> set[int]:
        return {3, 4, 6}

    def _empty_state_text(self) -> str:
        return "No reload betting offers for this date."

    def _record_values(self, record: dict[str, str]) -> list[str]:
        return [
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

    def _create_template_dialog(self, parent: QWidget) -> QDialog:
        return ReloadBettingOfferTemplateDialog(self.db.path.parent, parent)

    def _refresh_instances_window(self, window_start: str, window_end: str) -> None:
        self.db.refresh_reload_betting_offer_instances(window_start, window_end)

    def _fetch_instances_for_date(self, date_iso: str) -> list[dict[str, str]]:
        return self.db.fetch_reload_betting_offer_instances_for_date(date_iso)

    def _link_instance_record(self, instance_id: str, record_id: str) -> None:
        self.db.set_reload_betting_offer_instance_betting_record(instance_id, record_id)

    def _is_done_status(self, status: str) -> bool:
        return status == _status_label("Done")

    def _is_error_status(self, status: str) -> bool:
        return status == _status_label("Error")

__all__ = [
    "ReloadBettingOffersPanel",
    "ReloadBettingOfferTemplateDialog",
]
