from __future__ import annotations

from pathlib import Path

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

from .ui_settings import UiSettingsStore


class SettingsAboutTab(QWidget):
    def __init__(self, data_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.data_dir = data_dir
        self.settings = UiSettingsStore(data_dir)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Matched Betting Manager v2.0.1", self)
        title.setProperty("role", "panelTitle")

        intro = QLabel(
            "This release provides a modernized workspace UI with faster local data operations.",
            self,
        )
        intro.setWordWrap(True)

        font_scale_label = QLabel("Font Size", self)
        self.font_scale_spin = QSpinBox(self)
        self.font_scale_spin.setRange(50, 200)
        self.font_scale_spin.setValue(self.settings.get_font_scale())
        self.font_scale_spin.setSuffix("%")
        self.font_scale_spin.valueChanged.connect(self._on_font_scale_changed)

        font_row = QHBoxLayout()
        font_row.addWidget(font_scale_label)
        font_row.addWidget(self.font_scale_spin)
        font_row.addStretch(1)

        db_path = self.data_dir / "mbmanager.db"
        db_label = QLabel(f"Database: {db_path}", self)
        db_label.setWordWrap(True)
        db_label.setProperty("role", "metaInfo")

        data_dir_label = QLabel(f"Data Directory: {self.data_dir}", self)
        data_dir_label.setWordWrap(True)
        data_dir_label.setProperty("role", "metaInfo")

        delete_db_btn = QPushButton("Delete Database", self)
        delete_db_btn.setProperty("variant", "danger")
        delete_db_btn.clicked.connect(self._delete_database)

        delete_all_btn = QPushButton("Delete Database + UI Settings", self)
        delete_all_btn.setProperty("variant", "danger")
        delete_all_btn.clicked.connect(self._delete_database_and_settings)

        actions = QHBoxLayout()
        actions.addWidget(delete_db_btn)
        actions.addWidget(delete_all_btn)
        actions.addStretch(1)

        author = QLabel("Author: Parzival5077", self)
        github = QLabel('GitHub: <a href="https://github.com/PZV5077">https://github.com/PZV5077</a>', self)
        github.setOpenExternalLinks(True)

        layout.addWidget(title)
        layout.addWidget(intro)
        layout.addLayout(font_row)
        layout.addWidget(data_dir_label)
        layout.addWidget(db_label)
        layout.addLayout(actions)
        layout.addWidget(author)
        layout.addWidget(github)
        layout.addStretch(1)

    def _on_font_scale_changed(self, value: int) -> None:
        self.settings.set_font_scale(value)

        app = QApplication.instance()
        if app is None or not isinstance(app, QApplication):
            return

        base_font = app.font()
        size = base_font.pointSize()
        if size <= 0:
            return
        scaled = int(size * value / 100)
        base_font.setPointSize(max(8, scaled))
        app.setFont(base_font)

    def _delete_database(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Dangerous Action",
            "Delete database file (mbmanager.db)? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        db_file = self.data_dir / "mbmanager.db"
        try:
            db_file.unlink(missing_ok=True)
        except OSError as exc:
            QMessageBox.warning(self, "Delete Failed", f"Failed to delete database:\n{exc}")
            self._request_workspace_refresh()
            return

        QMessageBox.information(self, "Delete Completed", "Database deleted.")
        self._request_workspace_refresh()

    def _delete_database_and_settings(self) -> None:
        reply = QMessageBox.warning(
            self,
            "Dangerous Action",
            "Delete database and UI settings? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        failures: list[str] = []

        db_file = self.data_dir / "mbmanager.db"
        settings_file = self.data_dir / "ui_settings.json"

        try:
            db_file.unlink(missing_ok=True)
        except OSError:
            failures.append(db_file.name)

        try:
            settings_file.unlink(missing_ok=True)
        except OSError:
            failures.append(settings_file.name)

        if failures:
            QMessageBox.warning(
                self,
                "Delete Completed (with failures)",
                f"Could not delete: {', '.join(failures)}",
            )
        else:
            QMessageBox.information(self, "Delete Completed", "Database and UI settings deleted.")

        self._request_workspace_refresh()

    def _request_workspace_refresh(self) -> None:
        window = self.window()
        refresh = getattr(window, "refresh_workspace", None)
        if callable(refresh):
            refresh()
