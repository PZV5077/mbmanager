from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton, QTabBar, QTabWidget, QWidget

from betting_tab import BettingTab
from casino_tab import CasinoTab
from settings_about_tab import SettingsAboutTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Matched Betting Manager")
        self.resize(1440, 860)
        data_dir = Path(__file__).resolve().parent / "data"
        tabs = QTabWidget(self)
        self.tabs = tabs
        betting_tab = BettingTab(data_dir, self)
        self._add_data_tab(tabs, "Betting", betting_tab)
        # tabs.addTab(CasinoTab(data_dir, self), "Casino")
        self.settings_index = tabs.addTab(SettingsAboutTab(data_dir, self), "Settings and About")
        tabs.tabBar().setTabVisible(self.settings_index, False)

        self.settings_btn = QPushButton("Settings and About", tabs)
        self.settings_btn.setFlat(True)
        self.settings_btn.clicked.connect(self._open_settings)
        tabs.setCornerWidget(self.settings_btn, Qt.Corner.TopRightCorner)
        tabs.currentChanged.connect(self._sync_settings_button)
        self._sync_settings_button(tabs.currentIndex())
        self.setCentralWidget(tabs)

    def _open_settings(self) -> None:
        self.tabs.setCurrentIndex(self.settings_index)

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
