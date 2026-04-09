from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget


class SettingsAboutTab(QWidget):
    def __init__(self, data_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.data_dir = data_dir

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        title = QLabel("Matched Betting Manager v1.0", self)
        title.setStyleSheet("font-size: 18px; font-weight: 700;")

        intro = QLabel("A matched betting manager designed as a supportment of Oddsmonkey or Outplayed.", self)
        intro.setWordWrap(True)

        danger_style = (
            "QPushButton {"
            "border: 2px solid #7F1D1D;"
            "color: #00000;"
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

        delete_all_btn = QPushButton("Delete Database + Settings", self)
        delete_all_btn.setStyleSheet(danger_style)
        delete_all_btn.clicked.connect(self._delete_database_and_settings)

        for btn in (delete_db_btn, delete_all_btn):
            char_width = btn.fontMetrics().horizontalAdvance('M')
            btn.setFixedWidth(btn.fontMetrics().horizontalAdvance(btn.text()) + char_width * 4)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 0, 0, 0)
        actions.setSpacing(10)
        actions.addWidget(delete_db_btn)
        actions.addWidget(delete_all_btn)
        actions.addStretch(1)

        author = QLabel("Author：Parzival5077", self)

        github = QLabel('GitHub：<a href="https://github.com/PZV5077">https://github.com/PZV5077</a>', self)
        github.setTextFormat(Qt.TextFormat.RichText)
        github.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        github.setOpenExternalLinks(True)

        lay.addWidget(title)
        lay.addWidget(intro)
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
            return

        QMessageBox.information(self, "Delete Completed", f"Deleted {deleted} file(s).")

    def _delete_database_and_settings(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Dangerous Action",
            "This will delete all CSV data files and ui_settings.json under data/.\nThis action cannot be undone. Continue?",
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

        if failed:
            QMessageBox.warning(
                self,
                "Delete Completed (with failures)",
                f"Deleted {deleted} file(s).\nFailed: {', '.join(failed)}",
            )
            return

        QMessageBox.information(self, "Delete Completed", f"Deleted {deleted} file(s).")
