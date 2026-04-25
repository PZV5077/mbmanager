from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QPushButton, QStackedWidget, QTabWidget, QVBoxLayout, QWidget

from app.betting_tab import BettingTab
from app.casino_tab import CasinoTab
from app.reload_casino_offer_panel import ReloadCasinoOffersPanel
from app.reload_betting_offer_panel import ReloadBettingOffersPanel
from app.settings_about_tab import SettingsAboutTab
from app.theme import apply_galaxy_theme, theme_toggle_label
from app.ui_settings import UiSettingsStore
from app.utils import get_data_dir


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowSystemMenuHint
            | Qt.WindowType.WindowMinMaxButtonsHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowTitle("Matched Betting Manager 2.0.1")
        self.resize(1980, 900)
        self.data_dir = get_data_dir()
        self.ui_settings = UiSettingsStore(self.data_dir)
        self.theme_mode = self.ui_settings.get_theme_mode("dark")
        self._build_workspace()

    def _build_workspace(self) -> None:
        old_central = self.centralWidget()
        if old_central is not None:
            old_central.deleteLater()

        self._apply_font_scale()

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        tabs = QTabWidget(container)
        self.tabs = tabs

        self.betting_tab = BettingTab(self.data_dir, self, on_records_changed=self._on_betting_records_changed)
        tabs.addTab(self.betting_tab, "Betting")

        self.casino_tab = CasinoTab(self.data_dir, self, on_records_changed=self._on_casino_records_changed)
        tabs.addTab(self.casino_tab, "Casino")

        self.settings_index = tabs.addTab(SettingsAboutTab(self.data_dir, self), "Settings and About")
        tabs.tabBar().setTabVisible(self.settings_index, False)

        self.reload_panel_stack = QStackedWidget(container)
        self.reload_panel_placeholder = QWidget(self.reload_panel_stack)

        self.reload_betting_offers_panel = ReloadBettingOffersPanel(
            self.data_dir,
            self._activate_reload_betting_offer_instance,
            self.reload_panel_stack,
        )
        self.reload_casino_offers_panel = ReloadCasinoOffersPanel(
            self.data_dir,
            self._activate_reload_casino_offer_instance,
            self.reload_panel_stack,
        )
        self.reload_panel_stack.addWidget(self.reload_panel_placeholder)
        self.reload_panel_stack.addWidget(self.reload_betting_offers_panel)
        self.reload_panel_stack.addWidget(self.reload_casino_offers_panel)
        self.reload_panel_placeholder.setMinimumHeight(0)
        self.reload_panel_placeholder.setMaximumHeight(0)

        corner_widget = QWidget(tabs)
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 0, 0)
        corner_layout.setSpacing(8)

        self.theme_toggle_btn = QPushButton(corner_widget)
        self.theme_toggle_btn.setObjectName("themeToggleButton")
        self.theme_toggle_btn.clicked.connect(self._toggle_theme)

        self.settings_btn = QPushButton("Settings and About", corner_widget)
        self.settings_btn.setObjectName("settingsButton")
        self.settings_btn.clicked.connect(self._open_settings)

        corner_layout.addWidget(self.theme_toggle_btn)
        corner_layout.addWidget(self.settings_btn)
        tabs.setCornerWidget(corner_widget, Qt.Corner.TopRightCorner)
        tabs.currentChanged.connect(self._sync_settings_button)
        tabs.currentChanged.connect(self._sync_reload_panel_visibility)
        self._sync_theme_button()
        self._sync_settings_button(tabs.currentIndex())
        self._sync_reload_panel_visibility(tabs.currentIndex())

        layout.addWidget(tabs, 1)
        layout.addWidget(self.reload_panel_stack)
        self.setCentralWidget(container)

    def _apply_font_scale(self) -> None:
        font_scale = self.ui_settings.get_font_scale(100)

        app = QApplication.instance()
        if app is None or not isinstance(app, QApplication):
            return

        default_font = app.font()
        point_size = default_font.pointSize()
        if point_size <= 0:
            return

        scaled_size = int(point_size * font_scale / 100)
        default_font.setPointSize(max(8, scaled_size))
        app.setFont(default_font)

    def refresh_workspace(self) -> None:
        self.data_dir = get_data_dir()
        self.ui_settings = UiSettingsStore(self.data_dir)
        self.theme_mode = self.ui_settings.get_theme_mode(self.theme_mode)
        app = QApplication.instance()
        if app is not None and isinstance(app, QApplication):
            apply_galaxy_theme(app, self.theme_mode)
        self._build_workspace()

    def _open_settings(self) -> None:
        self.tabs.setCurrentIndex(self.settings_index)

    def _toggle_theme(self) -> None:
        self.theme_mode = "dark" if self.theme_mode == "light" else "light"
        self.ui_settings.set_theme_mode(self.theme_mode)

        app = QApplication.instance()
        if app is not None and isinstance(app, QApplication):
            apply_galaxy_theme(app, self.theme_mode)
            self._apply_font_scale()

        self._sync_theme_button()
        self._sync_settings_button(self.tabs.currentIndex())
        if hasattr(self, "reload_betting_offers_panel"):
            self.reload_betting_offers_panel.refresh_panel()
        if hasattr(self, "reload_casino_offers_panel"):
            self.reload_casino_offers_panel.refresh_panel()

    def _sync_theme_button(self) -> None:
        self.theme_toggle_btn.setText(theme_toggle_label(self.theme_mode))
        if self.theme_mode == "light":
            self.theme_toggle_btn.setToolTip("Switch to dark theme")
            return
        self.theme_toggle_btn.setToolTip("Switch to light theme")

    def _sync_settings_button(self, index: int) -> None:
        self.settings_btn.setProperty("active", index == self.settings_index)
        self.settings_btn.style().unpolish(self.settings_btn)
        self.settings_btn.style().polish(self.settings_btn)
        self.settings_btn.update()

    def _sync_reload_panel_visibility(self, index: int) -> None:
        current_tab = self.tabs.widget(index)
        if current_tab is self.betting_tab:
            self.reload_panel_stack.setVisible(True)
            self.reload_panel_stack.setCurrentWidget(self.reload_betting_offers_panel)
            self.reload_betting_offers_panel._sync_layout_height()
            return
        if current_tab is self.casino_tab:
            self.reload_panel_stack.setVisible(True)
            self.reload_panel_stack.setCurrentWidget(self.reload_casino_offers_panel)
            self.reload_casino_offers_panel._sync_layout_height()
            return

        self.reload_panel_stack.setCurrentWidget(self.reload_panel_placeholder)
        self.reload_panel_stack.setMinimumHeight(0)
        self.reload_panel_stack.setMaximumHeight(0)
        self.reload_panel_stack.setVisible(False)

    def _activate_reload_betting_offer_instance(self, instance: dict[str, str]) -> str | None:
        record_id = instance.get("betting_record_id", "")
        if record_id:
            record = self.betting_tab.db.get_betting_record(record_id)
            if record is not None:
                self.tabs.setCurrentWidget(self.betting_tab)
                self.betting_tab.active_record_id = record_id
                self.betting_tab.render_table()
                return record_id

        record_id = self.reload_betting_offers_panel.db.create_betting_record_from_reload_betting_offer(instance.get("id", ""))
        self.tabs.setCurrentWidget(self.betting_tab)
        self.betting_tab.active_record_id = record_id
        self.betting_tab.render_table()
        self.reload_betting_offers_panel.refresh_panel()
        return record_id

    def _activate_reload_casino_offer_instance(self, instance: dict[str, str]) -> str | None:
        record_id = instance.get("casino_record_id", "")
        if record_id:
            record = self.casino_tab.db.get_casino_record(record_id)
            if record is not None:
                self.tabs.setCurrentWidget(self.casino_tab)
                self.casino_tab.active_record_id = record_id
                self.casino_tab.render_table()
                return record_id

        record_id = self.reload_casino_offers_panel.db.create_casino_record_from_reload_casino_offer(instance.get("id", ""))
        self.tabs.setCurrentWidget(self.casino_tab)
        self.casino_tab.active_record_id = record_id
        self.casino_tab.render_table()
        self.reload_casino_offers_panel.refresh_panel()
        return record_id

    def _on_betting_records_changed(self) -> None:
        if hasattr(self, "reload_betting_offers_panel"):
            self.reload_betting_offers_panel.refresh_panel()

    def _on_casino_records_changed(self) -> None:
        if hasattr(self, "reload_casino_offers_panel"):
            self.reload_casino_offers_panel.refresh_panel()


def main() -> int:
    app = QApplication(sys.argv)
    settings_store = UiSettingsStore(get_data_dir())
    apply_galaxy_theme(app, settings_store.get_theme_mode("dark"))

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
