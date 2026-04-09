from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from reload_offer_store import ReloadOfferStore
from ui_settings import UiSettingsStore


class SettingsAboutTab(QWidget):
    def __init__(self, data_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.data_dir = data_dir
        self.settings = UiSettingsStore(data_dir)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        title = QLabel("Matched Betting Manager v1.0", self)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")

        intro = QLabel("A matched betting manager designed as a supportment of Oddsmonkey or Outplayed.", self)
        intro.setWordWrap(True)

        # Font Size Setting
        font_scale_label = QLabel("Font Size:", self)
        self.font_scale_spinbox = QSpinBox(self)
        self.font_scale_spinbox.setMinimum(50)
        self.font_scale_spinbox.setMaximum(200)
        self.font_scale_spinbox.setValue(self.settings.get_font_scale())
        self.font_scale_spinbox.setSuffix("%")
        self.font_scale_spinbox.setMaximumWidth(100)
        self.font_scale_spinbox.valueChanged.connect(self._on_font_scale_changed)

        font_scale_layout = QHBoxLayout()
        font_scale_layout.setContentsMargins(0, 0, 0, 0)
        font_scale_layout.setSpacing(10)
        font_scale_layout.addWidget(font_scale_label)
        font_scale_layout.addWidget(self.font_scale_spinbox)
        font_scale_layout.addStretch(1)

        danger_style = (
            "QPushButton {"
            "border: 2px solid #7F1D1D;"
            "color: #FFFFFF;"
            "background: transparent;"
            "padding: 6px 12px;"
            "border-radius: 6px;"
            "font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "background: #FEE2E2;"
            "}"
        )

        delete_db_btn = QPushButton("Delete Database", self)
        delete_db_btn.setStyleSheet(danger_style)
        delete_db_btn.clicked.connect(self._delete_database)

        delete_templates_btn = QPushButton("Delete All Offer Templates", self)
        delete_templates_btn.setStyleSheet(danger_style)
        delete_templates_btn.clicked.connect(self._delete_all_offer_templates)

        delete_all_btn = QPushButton("Delete Database + Settings", self)
        delete_all_btn.setStyleSheet(danger_style)
        delete_all_btn.clicked.connect(self._delete_database_and_settings)

        for btn in (delete_db_btn, delete_templates_btn, delete_all_btn):
            char_width = btn.fontMetrics().horizontalAdvance('M')
            btn.setFixedWidth(btn.fontMetrics().horizontalAdvance(btn.text()) + char_width * 4)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(10)
        actions.addWidget(delete_db_btn)
        actions.addWidget(delete_templates_btn)
        actions.addWidget(delete_all_btn)
        actions.addStretch(1)

        author = QLabel("Author：Parzival5077", self)

        github = QLabel('GitHub：<a href="https://github.com/PZV5077">https://github.com/PZV5077</a>', self)
        github.setTextFormat(Qt.TextFormat.RichText)
        github.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        github.setOpenExternalLinks(True)

        lay.addWidget(title)
        lay.addWidget(intro)
        lay.addLayout(font_scale_layout)
        lay.addLayout(actions)
        lay.addWidget(author)
        lay.addWidget(github)
        lay.addStretch(1)

    def _delete_database(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Dangerous Action",
            "This will delete all CSV data files under data/.\nThis action cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        deleted = 0
        failed: list[str] = []

        for csv_file in self.data_dir.glob("*.csv"):
            try:
                csv_file.unlink(missing_ok=True)
                deleted += 1
            except OSError:
                failed.append(csv_file.name)

        if failed:
            QMessageBox.warning(
                self,
                "Delete Completed (with failures)",
                f"Deleted {deleted} file(s).\nFailed: {', '.join(failed)}",
            )
            self._request_workspace_refresh()
            return

        QMessageBox.information(self, "Delete Completed", f"Deleted {deleted} file(s).")
        self._request_workspace_refresh()

    def _delete_database_and_settings(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Dangerous Action",
            "This will delete all CSV data files, ui_settings.json, and offer template config under data/.\nThis action cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        deleted = 0
        failed: list[str] = []

        for csv_file in self.data_dir.glob("*.csv"):
            try:
                csv_file.unlink(missing_ok=True)
                deleted += 1
            except OSError:
                failed.append(csv_file.name)

        settings_file = self.data_dir / "ui_settings.json"
        try:
            settings_file.unlink(missing_ok=True)
            deleted += 1
        except OSError:
            failed.append(settings_file.name)

        offer_templates_file = ReloadOfferStore(self.data_dir).path
        try:
            offer_templates_file.unlink(missing_ok=True)
            deleted += 1
        except OSError:
            failed.append(offer_templates_file.name)

        if failed:
            QMessageBox.warning(
                self,
                "Delete Completed (with failures)",
                f"Deleted {deleted} file(s).\nFailed: {', '.join(failed)}",
            )
            self._request_workspace_refresh()
            return

        QMessageBox.information(self, "Delete Completed", f"Deleted {deleted} file(s).")
        self._request_workspace_refresh()

    def _delete_all_offer_templates(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Dangerous Action",
            "This will delete all offer template config (reload_offers.json).\nThis action cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        templates_file = ReloadOfferStore(self.data_dir).path
        try:
            templates_file.unlink(missing_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "Delete Failed", f"Failed to delete {templates_file.name}:\n{exc}")
            self._request_workspace_refresh()
            return

        QMessageBox.information(self, "Delete Completed", "Offer template config deleted.")
        self._request_workspace_refresh()

    def _on_font_scale_changed(self, value: int) -> None:
        self.settings.set_font_scale(value)
        
        # Apply font scaling to the application immediately
        app = QApplication.instance()
        if app is not None and isinstance(app, QApplication):
            default_font = app.font()
            base_size = default_font.pointSize()
            if base_size > 0:
                scaled_size = int(base_size * value / 100)
                default_font.setPointSize(scaled_size)
                app.setFont(default_font)

    def _request_workspace_refresh(self) -> None:
        window = self.window()
        refresh = getattr(window, "refresh_workspace", None)
        if callable(refresh):
            refresh()
