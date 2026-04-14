from __future__ import annotations

from PySide6.QtCore import QDate, QEvent, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDateEdit, QHBoxLayout, QLineEdit, QToolButton, QWidget

from .utils import parse_date


def normalize_web_url(value: str) -> str | None:
    text = (value or "").strip()
    if not text or any(ch.isspace() for ch in text):
        return None
    if text.startswith(("http://", "https://")):
        return text
    host = text.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
    labels = host.removeprefix("www.").split(".")
    if len(labels) >= 2 and len(labels[-1]) >= 2 and any(ch.isalpha() for ch in host):
        return f"https://{text}"
    return None


class NullableDateWidget(QWidget):
    textChanged = Signal(str)

    def __init__(self, value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._min = QDate(2000, 1, 1)
        self._updating = False

        self.edit = QDateEdit(self)
        self.edit.setCalendarPopup(True)
        self.edit.setDisplayFormat("dd/MM/yy")
        # Qt may render minimum date when special text is truly empty.
        # Use a single space so empty values stay visually blank.
        self.edit.setSpecialValueText(" ")
        self.edit.setMinimumDate(self._min)
        self.edit.setDate(self._min)
        self._calendar = self.edit.calendarWidget()
        self._calendar.installEventFilter(self)

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

    def eventFilter(self, obj: object, event: QEvent) -> bool:
        if obj is self._calendar and event.type() == QEvent.Type.Show and self.edit.date() == self._min:
            today = QDate.currentDate()
            self._calendar.setCurrentPage(today.year(), today.month())
            self._calendar.setSelectedDate(today)
        return super().eventFilter(obj, event)


class LinkLineWidget(QWidget):
    textChanged = Signal(str)

    def __init__(self, value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.edit = QLineEdit(self)
        self.edit.setPlaceholderText("Text or URL")

        self.open_btn = QToolButton(self)
        self.open_btn.setText("↗")
        self.open_btn.setAutoRaise(True)
        self.open_btn.setToolTip("Open link in browser")
        self.open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_btn.clicked.connect(self._open_url)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lay.addWidget(self.edit, 1)
        lay.addWidget(self.open_btn)

        self.setFocusProxy(self.edit)
        self.edit.textChanged.connect(self._update_link_state)
        self.edit.editingFinished.connect(self._emit)
        self.set_text(value)

    def set_text(self, value: str) -> None:
        self.edit.setText(value)
        self._update_link_state(value)

    def text(self) -> str:
        return self.edit.text()

    def normalized_url(self) -> str | None:
        return normalize_web_url(self.edit.text())

    def _emit(self) -> None:
        self.textChanged.emit(self.text())

    def _update_link_state(self, value: str) -> None:
        url = normalize_web_url(value)
        self.open_btn.setVisible(url is not None)
        self.open_btn.setEnabled(url is not None)
        if url is not None:
            self.edit.setStyleSheet("QLineEdit { color: #1D4ED8; text-decoration: underline; }")
        else:
            self.edit.setStyleSheet("")

    def _open_url(self) -> None:
        url = normalize_web_url(self.edit.text())
        if url is None:
            return
        QDesktopServices.openUrl(QUrl(url))
