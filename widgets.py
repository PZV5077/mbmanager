from __future__ import annotations

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import QDateEdit, QHBoxLayout, QToolButton, QWidget

from utils import parse_date


class NullableDateWidget(QWidget):
    textChanged = Signal(str)

    def __init__(self, value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._min = QDate(2000, 1, 1)
        self._updating = False

        self.edit = QDateEdit(self)
        self.edit.setCalendarPopup(True)
        self.edit.setDisplayFormat("dd/MM/yy")
        self.edit.setSpecialValueText("")
        self.edit.setMinimumDate(self._min)
        self.edit.setDate(self._min)

        self.clear_btn = QToolButton(self)
        self.clear_btn.setText("x")
        self.clear_btn.setAutoRaise(True)
        self.clear_btn.setToolTip("Clear date")

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lay.addWidget(self.edit)
        lay.addWidget(self.clear_btn)

        self.setFocusProxy(self.edit)
        self.set_text(value)
        self.edit.dateChanged.connect(self._emit)
        self.clear_btn.clicked.connect(self.clear)

    def set_text(self, value: str) -> None:
        self._updating = True
        try:
            dt = parse_date(value)
            if dt is None:
                self.edit.setDate(self._min)
            else:
                self.edit.setDate(QDate(dt.year, dt.month, dt.day))
        finally:
            self._updating = False

    def text(self) -> str:
        if self.edit.date() == self._min:
            return ""
        return self.edit.date().toString("dd/MM/yy")

    def clear(self) -> None:
        self.set_text("")
        self.textChanged.emit("")

    def _emit(self) -> None:
        if not self._updating:
            self.textChanged.emit(self.text())
