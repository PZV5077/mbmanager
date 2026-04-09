from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QTabBar, QTabWidget, QVBoxLayout, QWidget

from betting_tab import BettingTab
from bottom_pullup_panel import BottomPullUpPanel
from casino_tab import CasinoTab
from settings_about_tab import SettingsAboutTab
from ui_settings import UiSettingsStore
from utils import get_data_dir


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Matched Betting Manager")
        self.resize(1440, 860)
        self.data_dir = get_data_dir()
        self._build_workspace()

    def _build_workspace(self) -> None:
        old_central = self.centralWidget()
        if old_central is not None:
            old_central.deleteLater()

        self._apply_font_scale()

        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget(container)
        self.tabs = tabs
        self.betting_tab = BettingTab(self.data_dir, self, on_records_changed=self._on_betting_records_changed)
        self._add_data_tab(tabs, "Betting", self.betting_tab)
        # tabs.addTab(CasinoTab(self.data_dir, self), "Casino")
        self.settings_index = tabs.addTab(SettingsAboutTab(self.data_dir, self), "Settings and About")
        tabs.tabBar().setTabVisible(self.settings_index, False)

        self.settings_btn = QPushButton("Settings and About", tabs)
        self.settings_btn.clicked.connect(self._open_settings)
        tabs.setCornerWidget(self.settings_btn, Qt.Corner.TopRightCorner)
        tabs.currentChanged.connect(self._sync_settings_button)
        self._sync_settings_button(tabs.currentIndex())

        layout.addWidget(tabs, 1)
        self.reload_offer_panel = BottomPullUpPanel(
            self.data_dir,
            container,
            on_offer_activated=self._on_reload_offer_activated,
            get_offer_status=self._get_reload_offer_status,
        )
        layout.addWidget(self.reload_offer_panel, 0)
        self.setCentralWidget(container)

    def _apply_font_scale(self) -> None:
        settings_store = UiSettingsStore(self.data_dir)
        font_scale = settings_store.get_font_scale(100)

        app = QApplication.instance()
        if app is None or not isinstance(app, QApplication):
            return
        default_font = app.font()
        scaled_size = int(default_font.pointSize() * font_scale / 100) if font_scale != 100 else default_font.pointSize()
        default_font.setPointSize(scaled_size)
        app.setFont(default_font)

    def refresh_workspace(self) -> None:
        self.data_dir = get_data_dir()
        self._build_workspace()

    def _open_settings(self) -> None:
        self.tabs.setCurrentIndex(self.settings_index)

    def _on_reload_offer_activated(self, instance: dict[str, object]) -> None:
        # Always switch to betting tab when creating/highlighting from reload offers.
        self.tabs.setCurrentIndex(0)
        self.betting_tab.ensure_record_for_reload_instance(instance)

    def _get_reload_offer_status(self, instance_id: str) -> str | None:
        return self.betting_tab.get_reload_instance_status(instance_id)

    def _on_betting_records_changed(self) -> None:
        if hasattr(self, "reload_offer_panel"):
            self.reload_offer_panel.refresh_status_view()

    def _sync_settings_button(self, index: int) -> None:
        if index == self.settings_index:
            self.settings_btn.setStyleSheet("font-weight: 700;")
            return
        self.settings_btn.setStyleSheet("")

    def _add_data_tab(self, tabs: QTabWidget, title: str, tab: QWidget) -> None:
        idx = tabs.addTab(tab, title)
        store = getattr(tab, "store", None)
        path = getattr(store, "path", None)
        if path is None:
            return
        name = path.name
        if not name.startswith("test_"):
            return
        badge = QLabel(f"[{name}]", tabs)
        badge.setStyleSheet("color: #DC2626; font-weight: 600;")
        tabs.tabBar().setTabButton(idx, QTabBar.ButtonPosition.RightSide, badge)


def main() -> int:
    app = QApplication(sys.argv)

    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
