from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget

from betting_tab import BettingTab
from casino_tab import CasinoTab


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Matched Betting Manager")
        self.resize(1440, 860)
        data_dir = Path(__file__).resolve().parent / "data"
        tabs = QTabWidget(self)
        tabs.addTab(BettingTab(data_dir, self), "Betting")
        # tabs.addTab(CasinoTab(data_dir, self), "Casino")
        self.setCentralWidget(tabs)


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
