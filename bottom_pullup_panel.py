from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QDate, Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCalendarWidget,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from reload_offer_store import ReloadOfferStore
from utils import status_color

RELOAD_QB_TYPES = ["", "Single", "Acca", "Bet Builder", "Other"]
RELOAD_BONUS_TYPES = ["", "Free Bet (SNR)", "Free Bet (SR)", "Bonus Cash", "Refund", "Profit Boost", "Other"]


class ReloadOfferSettingsDialog(QDialog):
    fixed_field_keys = [
        "bookie",
        "promo_name",
        "deposit_amount",
        "qb1_type",
        "qb1_amount",
        "has_qb2",
        "qb2_type",
        "qb2_amount",
        "bonus_type",
        "bonus_amount",
    ]

    def __init__(self, store: ReloadOfferStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.store = store
        self.db = self.store.load()
        self.templates: list[dict[str, Any]] = [deepcopy(template) for template in self.db.get("templates", [])]
        self._extra_fixed_fields: dict[str, str] = {}
        self._loading = False
        self._build_ui()
        self._refresh_template_list()

    def _build_ui(self) -> None:
        self.setWindowTitle("Reload Offer Settings")
        self.resize(940, 640)

        self.template_list = QListWidget(self)
        self.template_list.currentItemChanged.connect(self._on_template_item_changed)

        add_btn = QPushButton("Add", self)
        add_btn.clicked.connect(self._add_template)
        duplicate_btn = QPushButton("Duplicate", self)
        duplicate_btn.clicked.connect(self._duplicate_template)
        delete_btn = QPushButton("Delete", self)
        delete_btn.clicked.connect(self._delete_template)

        list_btn_row = QHBoxLayout()
        list_btn_row.addWidget(add_btn)
        list_btn_row.addWidget(duplicate_btn)
        list_btn_row.addWidget(delete_btn)

        left_panel = QVBoxLayout()
        left_panel.addWidget(QLabel("Templates", self))
        left_panel.addWidget(self.template_list, 1)
        left_panel.addLayout(list_btn_row)

        self.name_edit = QLineEdit(self)
        self.enabled_check = QCheckBox("Enabled", self)
        self.anchor_date_edit = QDateEdit(self)
        self.anchor_date_edit.setCalendarPopup(True)
        self.anchor_date_edit.setDisplayFormat("dd/MM/yy")
        self.repeat_combo = QComboBox(self)
        self.repeat_combo.addItem("Weekly", "weekly")
        self.repeat_combo.addItem("Every 2 weeks", "biweekly")
        self.repeat_combo.addItem("Monthly", "monthly")
        self.repeat_combo.currentIndexChanged.connect(self._update_repeat_visibility)

        self.weekday_combo = QComboBox(self)
        for index, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            self.weekday_combo.addItem(name, index)

        self.month_day_spin = QSpinBox(self)
        self.month_day_spin.setRange(1, 31)

        self.bookie_edit = QLineEdit(self)
        self.promo_name_edit = QLineEdit(self)
        self.deposit_amt_edit = QLineEdit(self)
        self.qb1_type_combo = QComboBox(self)
        self.qb1_type_combo.addItems(RELOAD_QB_TYPES)
        self.qb1_amt_edit = QLineEdit(self)
        self.has_qb2_combo = QComboBox(self)
        self.has_qb2_combo.addItems(["No", "Yes"])
        self.has_qb2_combo.currentTextChanged.connect(self._update_qb2_state)
        self.qb2_type_combo = QComboBox(self)
        self.qb2_type_combo.addItems(RELOAD_QB_TYPES)
        self.qb2_amt_edit = QLineEdit(self)
        self.bonus_type_combo = QComboBox(self)
        self.bonus_type_combo.addItems(RELOAD_BONUS_TYPES)
        self.bonus_amt_edit = QLineEdit(self)

        form = QFormLayout()
        form.addRow("Name", self.name_edit)
        form.addRow("Enabled", self.enabled_check)
        form.addRow("Start date", self.anchor_date_edit)
        form.addRow("Repeat", self.repeat_combo)
        form.addRow("Weekday", self.weekday_combo)
        form.addRow("Month day", self.month_day_spin)
        form.addRow("Bookie", self.bookie_edit)
        form.addRow("Promo name", self.promo_name_edit)
        form.addRow("Deposit amt", self.deposit_amt_edit)
        form.addRow("QB1 type", self.qb1_type_combo)
        form.addRow("QB1 amt", self.qb1_amt_edit)
        form.addRow("Has QB2", self.has_qb2_combo)
        form.addRow("QB2 type", self.qb2_type_combo)
        form.addRow("QB2 amt", self.qb2_amt_edit)
        form.addRow("Bonus type", self.bonus_type_combo)
        form.addRow("Bonus amt", self.bonus_amt_edit)

        self.repeat_help = QLabel(
            "Use Start date as the first usable date. Weekly/Biweekly follow a weekday; Monthly follows a month day.",
            self,
        )
        self.repeat_help.setWordWrap(True)
        self.repeat_help.setStyleSheet("color: #6B7280;")

        self.storage_path_label = QLabel(f"Storage: {self.store.path}", self)
        self.storage_path_label.setWordWrap(True)
        self.storage_path_label.setStyleSheet("color: #6B7280;")

        self.save_btn = QPushButton("Save", self)
        self.save_btn.clicked.connect(self._save_and_close)
        self.close_btn = QPushButton("Close", self)
        self.close_btn.clicked.connect(self.reject)

        right_buttons = QHBoxLayout()
        right_buttons.addStretch(1)
        right_buttons.addWidget(self.save_btn)
        right_buttons.addWidget(self.close_btn)

        right_panel = QVBoxLayout()
        right_panel.addWidget(QLabel("Template editor", self))
        right_panel.addLayout(form)
        right_panel.addWidget(self.repeat_help)
        right_panel.addWidget(self.storage_path_label)
        right_panel.addStretch(1)
        right_panel.addLayout(right_buttons)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        left_widget = QWidget(self)
        left_widget.setLayout(left_panel)
        right_widget = QWidget(self)
        right_widget.setLayout(right_panel)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        root = QVBoxLayout(self)
        root.addWidget(splitter)

        self._update_repeat_visibility()
        self._update_qb2_state()

    def _current_template(self) -> dict[str, Any] | None:
        current_row = self.template_list.currentRow()
        if current_row < 0 or current_row >= len(self.templates):
            return None
        return self.templates[current_row]

    def _template_by_id(self, template_id: str) -> dict[str, Any] | None:
        return next((template for template in self.templates if template.get("id") == template_id), None)

    def _on_template_item_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if self._loading:
            return
        if previous is not None:
            previous_id = str(previous.data(Qt.ItemDataRole.UserRole) or "")
            previous_template = self._template_by_id(previous_id)
            if previous_template is not None and not self._commit_editor_to_template(previous_template):
                self._loading = True
                try:
                    for index, template in enumerate(self.templates):
                        if template.get("id") == previous_id:
                            self.template_list.setCurrentRow(index)
                            break
                finally:
                    self._loading = False
                return
        if current is not None:
            current_id = str(current.data(Qt.ItemDataRole.UserRole) or "")
            template = self._template_by_id(current_id)
            if template is not None:
                self._load_template(template)
                return
        self._clear_editor()

    def _load_template(self, template: dict[str, Any]) -> None:
        self._loading = True
        try:
            self.name_edit.setText(template.get("name", ""))
            self.enabled_check.setChecked(bool(template.get("enabled", True)))
            anchor = self._to_qdate(template.get("anchor_date"))
            self.anchor_date_edit.setDate(anchor)
            repeat_type = template.get("repeat_type", "weekly")
            repeat_index = self.repeat_combo.findData(repeat_type)
            self.repeat_combo.setCurrentIndex(max(0, repeat_index))
            weekday_index = self.weekday_combo.findData(int(template.get("weekday", date.today().weekday())))
            self.weekday_combo.setCurrentIndex(max(0, weekday_index))
            self.month_day_spin.setValue(int(template.get("month_day", date.today().day)))
            fixed_fields = template.get("fixed_fields", {}) if isinstance(template.get("fixed_fields", {}), dict) else {}
            self._load_fixed_fields(fixed_fields)
        finally:
            self._loading = False
        self._update_repeat_visibility()
        self._update_qb2_state()

    def _clear_editor(self) -> None:
        self._loading = True
        try:
            self.name_edit.clear()
            self.enabled_check.setChecked(True)
            self.anchor_date_edit.setDate(QDate.currentDate())
            self.repeat_combo.setCurrentIndex(0)
            self.weekday_combo.setCurrentIndex(QDate.currentDate().dayOfWeek() - 1)
            self.month_day_spin.setValue(QDate.currentDate().day())
            self._load_fixed_fields({})
        finally:
            self._loading = False
        self._update_repeat_visibility()
        self._update_qb2_state()

    def _update_repeat_visibility(self) -> None:
        repeat_type = self.repeat_combo.currentData()
        weekly_visible = repeat_type in {"weekly", "biweekly"}
        monthly_visible = repeat_type == "monthly"
        self.weekday_combo.setVisible(weekly_visible)
        self.month_day_spin.setVisible(monthly_visible)

    def _update_qb2_state(self) -> None:
        has_qb2 = self.has_qb2_combo.currentText() == "Yes"
        self.qb2_type_combo.setEnabled(has_qb2)
        self.qb2_amt_edit.setEnabled(has_qb2)
        if not has_qb2:
            self.qb2_type_combo.setCurrentIndex(0)
            self.qb2_amt_edit.clear()

    def _commit_editor_to_template(self, template: dict[str, Any]) -> bool:
        template["name"] = self.name_edit.text().strip() or "New Template"
        template["enabled"] = self.enabled_check.isChecked()
        template["anchor_date"] = self.anchor_date_edit.date().toString("dd/MM/yy")
        template["repeat_type"] = str(self.repeat_combo.currentData())
        template["weekday"] = int(self.weekday_combo.currentData())
        template["month_day"] = int(self.month_day_spin.value())
        fixed_fields = self._collect_fixed_fields()
        template["fixed_fields"] = fixed_fields
        return True

    def _save_and_close(self) -> None:
        template = self._current_template()
        if template is not None and not self._commit_editor_to_template(template):
            return
        self.db = self.store.replace_templates(self.templates)
        QMessageBox.information(self, "Saved", f"Templates saved to:\n{self.store.path}")
        self.accept()

    def _refresh_template_list(self, select_template_id: str | None = None) -> None:
        self.template_list.blockSignals(True)
        try:
            self.template_list.clear()
            for template in self.templates:
                item = QListWidgetItem(self._template_item_text(template))
                item.setData(Qt.ItemDataRole.UserRole, template["id"])
                self.template_list.addItem(item)
            if self.templates:
                target_row = 0
                if select_template_id is not None:
                    for index, template in enumerate(self.templates):
                        if template["id"] == select_template_id:
                            target_row = index
                            break
                self.template_list.setCurrentRow(target_row)
            else:
                self._clear_editor()
        finally:
            self.template_list.blockSignals(False)
        if self.templates:
            current = self._current_template()
            if current is not None:
                self._load_template(current)

    def _template_item_text(self, template: dict[str, Any]) -> str:
        status = "On" if template.get("enabled", True) else "Off"
        return f"{template.get('name', 'New Template')}\n{self.store.template_summary(template)} • {status}"

    def _load_fixed_fields(self, fixed_fields: dict[str, Any]) -> None:
        self._extra_fixed_fields = {
            str(key): str(value)
            for key, value in fixed_fields.items()
            if str(key) not in self.fixed_field_keys
        }
        self.bookie_edit.setText(str(fixed_fields.get("bookie", "")))
        self.promo_name_edit.setText(str(fixed_fields.get("promo_name", "")))
        self.deposit_amt_edit.setText(str(fixed_fields.get("deposit_amount", "")))
        self.qb1_type_combo.setCurrentText(str(fixed_fields.get("qb1_type", "")))
        self.qb1_amt_edit.setText(str(fixed_fields.get("qb1_amount", "")))
        has_qb2 = str(fixed_fields.get("has_qb2", "No"))
        self.has_qb2_combo.setCurrentText("Yes" if has_qb2 == "Yes" else "No")
        self.qb2_type_combo.setCurrentText(str(fixed_fields.get("qb2_type", "")))
        self.qb2_amt_edit.setText(str(fixed_fields.get("qb2_amount", "")))
        self.bonus_type_combo.setCurrentText(str(fixed_fields.get("bonus_type", "")))
        self.bonus_amt_edit.setText(str(fixed_fields.get("bonus_amount", "")))

    def _collect_fixed_fields(self) -> dict[str, str]:
        fixed_fields = dict(self._extra_fixed_fields)

        values = {
            "bookie": self.bookie_edit.text().strip(),
            "promo_name": self.promo_name_edit.text().strip(),
            "deposit_amount": self.deposit_amt_edit.text().strip(),
            "qb1_type": self.qb1_type_combo.currentText().strip(),
            "qb1_amount": self.qb1_amt_edit.text().strip(),
            "has_qb2": self.has_qb2_combo.currentText().strip(),
            "qb2_type": self.qb2_type_combo.currentText().strip(),
            "qb2_amount": self.qb2_amt_edit.text().strip(),
            "bonus_type": self.bonus_type_combo.currentText().strip(),
            "bonus_amount": self.bonus_amt_edit.text().strip(),
        }

        for key, value in values.items():
            if key == "has_qb2":
                fixed_fields[key] = value or "No"
            elif value:
                fixed_fields[key] = value
            else:
                fixed_fields.pop(key, None)

        return fixed_fields

    def _add_template(self) -> None:
        current = self._current_template()
        if current is not None and not self._commit_editor_to_template(current):
            return
        new_template = {
            "id": str(len(self.templates) + 1),
            "name": "New Template",
            "enabled": True,
            "anchor_date": QDate.currentDate().toString("dd/MM/yy"),
            "repeat_type": "weekly",
            "weekday": QDate.currentDate().dayOfWeek() - 1,
            "month_day": QDate.currentDate().day(),
            "fixed_fields": {},
        }
        new_template["id"] = str(new_template.get("id")) + "-" + QDate.currentDate().toString("yyyyMMddhhmmss")
        self.templates.append(new_template)
        self._refresh_template_list(new_template["id"])

    def _duplicate_template(self) -> None:
        current = self._current_template()
        if current is None:
            return
        if not self._commit_editor_to_template(current):
            return
        duplicate = deepcopy(current)
        duplicate["id"] = duplicate.get("id", "") + "-copy"
        duplicate["name"] = f"{duplicate.get('name', 'New Template')} Copy"
        self.templates.append(duplicate)
        self._refresh_template_list(duplicate["id"])

    def _delete_template(self) -> None:
        current = self._current_template()
        if current is None:
            return
        if not self._commit_editor_to_template(current):
            return
        if QMessageBox.question(
            self,
            "Delete Template",
            f"Delete template '{current.get('name', '')}'?",
        ) != QMessageBox.StandardButton.Yes:
            return
        self.templates = [template for template in self.templates if template["id"] != current["id"]]
        self._refresh_template_list()

    def _to_qdate(self, text: str | None) -> QDate:
        if not text:
            return QDate.currentDate()
        try:
            parts = text.split("/")
            if len(parts) != 3:
                return QDate.currentDate()
            day, month, year = (int(part) for part in parts)
            return QDate(2000 + year if year < 100 else year, month, day)
        except ValueError:
            return QDate.currentDate()


class BottomPullUpPanel(QWidget):
    def __init__(
        self,
        data_dir: Path,
        parent: QWidget | None = None,
        on_offer_activated: Callable[[dict[str, Any]], None] | None = None,
        get_offer_status: Callable[[str], str | None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.store = ReloadOfferStore(data_dir)
        self._expanded = False
        self.db = self.store.ensure_schedule()
        self._on_offer_activated = on_offer_activated
        self._get_offer_status = get_offer_status
        self._visible_instances: list[dict[str, Any]] = []

        self.toggle_btn = QToolButton(self)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(False)
        self.toggle_btn.setText("▼ Reload Offers")
        self.toggle_btn.clicked.connect(self._on_toggle)

        self.settings_btn = QToolButton(self)
        self.settings_btn.setText("⚙")
        self.settings_btn.setToolTip("Reload offer settings")
        self.settings_btn.clicked.connect(self._open_settings)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.addWidget(self.toggle_btn)
        header_layout.addStretch(1)
        header_layout.addWidget(self.settings_btn)

        self.content = QFrame(self)
        self.content.setFrameShape(QFrame.Shape.StyledPanel)
        self.content.setVisible(False)
        self.content.setMinimumHeight(260)
        self.content.setMaximumHeight(340)
        self.content.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.calendar = QCalendarWidget(self.content)
        self.calendar.setGridVisible(True)
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.selectionChanged.connect(self._update_preview)

        calendar_frame = QFrame(self.content)
        calendar_frame.setFrameShape(QFrame.Shape.StyledPanel)
        calendar_layout = QVBoxLayout(calendar_frame)
        calendar_layout.setContentsMargins(8, 8, 8, 8)
        calendar_layout.addWidget(QLabel("Date", calendar_frame))
        calendar_layout.addWidget(self.calendar)

        self.preview_title = QLabel("Offers for today", self.content)
        self.preview_table = QTableWidget(self.content)
        self.preview_table.setColumnCount(8)
        self.preview_table.setHorizontalHeaderLabels(
            ["Template", "Status", "Bookie", "Promo", "Deposit", "QB1", "QB2", "Bonus"]
        )
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.preview_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.preview_table.cellClicked.connect(self._on_preview_row_clicked)
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setStretchLastSection(True)

        preview_frame = QFrame(self.content)
        preview_frame.setFrameShape(QFrame.Shape.StyledPanel)
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.addWidget(self.preview_title)
        preview_layout.addWidget(self.preview_table, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal, self.content)
        splitter.addWidget(calendar_frame)
        splitter.addWidget(preview_frame)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        calendar_margins = calendar_layout.contentsMargins()
        calendar_min_width = (
            self.calendar.minimumSizeHint().width()
            + calendar_margins.left()
            + calendar_margins.right()
        )
        calendar_frame.setMinimumWidth(calendar_min_width)
        splitter.setSizes([calendar_min_width, max(360, calendar_min_width * 2)])

        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(8, 8, 8, 8)
        content_layout.addWidget(splitter)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addLayout(header_layout)
        root_layout.addWidget(self.content)

        self.refresh_schedule()

    def _on_toggle(self, checked: bool) -> None:
        self.set_expanded(checked)

    def set_expanded(self, expanded: bool) -> None:
        self._expanded = expanded
        self.content.setVisible(expanded)
        self.toggle_btn.setText("▲ Reload Offers" if expanded else "▼ Reload Offers")

    def refresh_schedule(self) -> None:
        # Always reload from disk to avoid stale in-memory data overwriting recent settings changes.
        self.db = self.store.ensure_schedule()
        self._update_preview()

    def refresh_status_view(self) -> None:
        self._update_preview()

    def _open_settings(self) -> None:
        dialog = ReloadOfferSettingsDialog(self.store, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_schedule()

    def _update_preview(self) -> None:
        selected_date = self.calendar.selectedDate()
        self.preview_title.setText(f"Offers for {selected_date.toString('dd/MM/yy')}")
        self.preview_table.clearContents()
        self.preview_table.setRowCount(0)
        self._visible_instances = []

        instances = [
            instance
            for instance in self.db.get("instances", [])
            if instance.get("scheduled_date") == selected_date.toString("dd/MM/yy")
        ]
        if not instances:
            self.preview_title.setText(f"Offers for {selected_date.toString('dd/MM/yy')} (none)")
            return

        self._visible_instances = instances
        self.preview_table.setRowCount(len(instances))
        for row, instance in enumerate(instances):
            values = instance.get("values") if isinstance(instance.get("values"), dict) else {}
            instance_id = str(instance.get("id", "") or "")
            live_status = self._get_offer_status(instance_id) if callable(self._get_offer_status) else None
            status_display = live_status or str(instance.get("status", "pending") or "pending")
            has_qb2 = str(values.get("has_qb2", "No") or "No")
            qb2_amt = str(values.get("qb2_amount", "") or "")
            qb2_display = has_qb2 if not qb2_amt else f"{has_qb2} ({qb2_amt})"

            row_values = [
                str(instance.get("template_name", "Offer") or "Offer"),
                status_display,
                str(values.get("bookie", "") or ""),
                str(values.get("promo_name", "") or ""),
                str(values.get("deposit_amount", "") or ""),
                str(values.get("qb1_amount", "") or ""),
                qb2_display,
                str(values.get("bonus_amount", "") or ""),
            ]
            for col, value in enumerate(row_values):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                if col == 1:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setBackground(QBrush(QColor(status_color(status_display))))
                    item.setForeground(QBrush(QColor("white")))
                self.preview_table.setItem(row, col, item)

    def _on_preview_row_clicked(self, row: int, _column: int) -> None:
        if not (0 <= row < len(self._visible_instances)):
            return
        if callable(self._on_offer_activated):
            self._on_offer_activated(self._visible_instances[row])
            self._update_preview()
