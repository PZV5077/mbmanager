from __future__ import annotations

from PySide6.QtCore import QDate, QDateTime, QEvent, Qt, QTime, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QCalendarWidget,
    QDialog,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableView,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .utils import parse_date, parse_datetime


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


def _current_minute_datetime() -> QDateTime:
    now = QDateTime.currentDateTime()
    return QDateTime(now.date(), QTime(now.time().hour(), now.time().minute()))


def _is_dark_theme_mode() -> bool:
    app = QApplication.instance()
    if app is None or not isinstance(app, QApplication):
        return False
    return str(app.property("theme_mode") or "light") == "dark"


def _apply_calendar_popup_palette(popup: QDialog, calendar: QCalendarWidget) -> None:
    dark = _is_dark_theme_mode()
    if dark:
        panel_bg = QColor("#0F172A")
        view_bg = QColor("#111827")
        header_bg = QColor("#1E293B")
        text = QColor("#E2E8F0")
        highlight = QColor("#0369A1")
        highlight_text = QColor("#F8FAFC")
        disabled_text = QColor("#64748B")
    else:
        panel_bg = QColor("#FFFFFF")
        view_bg = QColor("#FFFFFF")
        header_bg = QColor("#F8FBFF")
        text = QColor("#0F172A")
        highlight = QColor("#0EA5E9")
        highlight_text = QColor("#FFFFFF")
        disabled_text = QColor("#94A3B8")

    palette = popup.palette()
    palette.setColor(QPalette.ColorRole.Window, panel_bg)
    palette.setColor(QPalette.ColorRole.Base, view_bg)
    palette.setColor(QPalette.ColorRole.AlternateBase, header_bg)
    palette.setColor(QPalette.ColorRole.Text, text)
    palette.setColor(QPalette.ColorRole.WindowText, text)
    palette.setColor(QPalette.ColorRole.ButtonText, text)
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, highlight_text)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Window, panel_bg)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base, view_bg)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.AlternateBase, header_bg)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, disabled_text)
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, disabled_text)

    popup.setPalette(palette)
    calendar.setPalette(palette)

    view = calendar.findChild(QTableView, "qt_calendar_calendarview")
    if view is None:
        return

    view.setPalette(palette)
    view.setAutoFillBackground(True)

    viewport = view.viewport()
    viewport.setPalette(palette)
    viewport.setAutoFillBackground(True)

    for header in (view.horizontalHeader(), view.verticalHeader()):
        if header is None:
            continue
        header_palette = header.palette()
        header_palette.setColor(QPalette.ColorRole.Window, header_bg)
        header_palette.setColor(QPalette.ColorRole.Base, header_bg)
        header_palette.setColor(QPalette.ColorRole.Button, header_bg)
        header_palette.setColor(QPalette.ColorRole.Text, text)
        header_palette.setColor(QPalette.ColorRole.ButtonText, text)
        header_palette.setColor(QPalette.ColorRole.WindowText, text)
        header.setPalette(header_palette)
        header.setAutoFillBackground(True)


class _DateTimePopup(QDialog):
    def __init__(self, initial_value: QDateTime, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cleared = False

        self.setWindowFlags(Qt.WindowType.Popup)
        self.setWindowTitle("DateTime")
        self.setObjectName("dateTimePopup")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAutoFillBackground(True)

        self.calendar = QCalendarWidget(self)
        self.calendar.setGridVisible(False)
        self.calendar.setSelectedDate(initial_value.date())
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        self._refresh_theme()

        time_wrap = QFrame(self)
        time_layout = QHBoxLayout(time_wrap)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(6)

        hour_label = QLabel("Hour", time_wrap)
        self.hour_spin = QSpinBox(time_wrap)
        self.hour_spin.setRange(0, 23)
        self.hour_spin.setValue(initial_value.time().hour())

        minute_label = QLabel("Minute", time_wrap)
        self.minute_spin = QSpinBox(time_wrap)
        self.minute_spin.setRange(0, 59)
        self.minute_spin.setValue(initial_value.time().minute())

        time_layout.addWidget(hour_label)
        time_layout.addWidget(self.hour_spin)
        time_layout.addSpacing(8)
        time_layout.addWidget(minute_label)
        time_layout.addWidget(self.minute_spin)
        time_layout.addStretch(1)

        self.clear_btn = QPushButton("Clear", self)
        self.clear_btn.clicked.connect(self._clear_and_accept)

        self.now_btn = QPushButton("Now", self)
        self.now_btn.clicked.connect(self._set_now)

        self.apply_btn = QPushButton("Apply", self)
        self.apply_btn.clicked.connect(self.accept)

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.clicked.connect(self.reject)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(6)
        btn_row.addWidget(self.clear_btn)
        btn_row.addWidget(self.now_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.cancel_btn)
        btn_row.addWidget(self.apply_btn)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(self.calendar)
        root.addWidget(time_wrap)
        root.addLayout(btn_row)

        self.resize(360, 340)

    def showEvent(self, event: QEvent) -> None:
        super().showEvent(event)
        # Wayland popup polish can override calendar view colors after show.
        self._refresh_theme()
        QTimer.singleShot(0, self._refresh_theme)

    def _refresh_theme(self) -> None:
        self.setStyleSheet(_calendar_popup_stylesheet())
        _apply_calendar_popup_palette(self, self.calendar)

    @property
    def cleared(self) -> bool:
        return self._cleared

    def selected_datetime(self) -> QDateTime:
        selected_date = self.calendar.selectedDate()
        selected_time = QTime(self.hour_spin.value(), self.minute_spin.value())
        return QDateTime(selected_date, selected_time)

    def _clear_and_accept(self) -> None:
        self._cleared = True
        self.accept()

    def _set_now(self) -> None:
        current = _current_minute_datetime()
        self.calendar.setSelectedDate(current.date())
        self.hour_spin.setValue(current.time().hour())
        self.minute_spin.setValue(current.time().minute())


def _calendar_popup_stylesheet() -> str:
    mode = "light"
    app = QApplication.instance()
    if app is not None and isinstance(app, QApplication):
        mode = str(app.property("theme_mode") or "light")

    if mode == "dark":
        return """
            QDialog#dateTimePopup {
                background: #0F172A;
                border: 1px solid #334155;
                border-radius: 10px;
            }

            QDialog#dateTimePopup QLabel {
                color: #E2E8F0;
            }

            QDialog#dateTimePopup QFrame {
                background: transparent;
            }

            QCalendarWidget {
                border: 1px solid #334155;
                background: #0F172A;
            }

            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background: #172338;
                border-bottom: 1px solid #334155;
            }

            QCalendarWidget QToolButton {
                color: #E2E8F0;
                background: transparent;
                border: none;
                padding: 6px;
                min-width: 28px;
                font-weight: 600;
            }

            QCalendarWidget QToolButton:hover {
                background: #24324A;
                border-radius: 4px;
            }

            QCalendarWidget QMenu {
                background: #111827;
                color: #E5E7EB;
                border: 1px solid #334155;
            }

            QCalendarWidget QSpinBox {
                color: #E2E8F0;
                background: #0F172A;
                border: 1px solid #334155;
                selection-background-color: #0369A1;
            }

            QCalendarWidget QAbstractItemView:enabled {
                background: #111827;
                color: #E2E8F0;
                selection-background-color: #0369A1;
                selection-color: #F8FAFC;
                alternate-background-color: #1E293B;
                outline: 0;
            }

            QCalendarWidget QTableView {
                background: #111827;
                color: #E2E8F0;
            }

            QCalendarWidget QTableView#qt_calendar_calendarview QWidget#qt_scrollarea_viewport {
                background: #111827;
                color: #E2E8F0;
            }

            QCalendarWidget QTableView#qt_calendar_calendarview QHeaderView::section {
                background: #1E293B;
                color: #E2E8F0;
                border: none;
                border-bottom: 1px solid #334155;
                padding: 6px 0px;
                font-weight: 700;
            }

            QCalendarWidget QAbstractItemView:disabled {
                color: #64748B;
            }
        """

    return """
        QDialog#dateTimePopup {
            background: #FFFFFF;
            border: 1px solid #C7D8EE;
            border-radius: 10px;
        }

        QDialog#dateTimePopup QLabel {
            color: #0F172A;
        }

        QDialog#dateTimePopup QFrame {
            background: transparent;
        }

        QCalendarWidget {
            border: 1px solid #C7D8EE;
            background: #FFFFFF;
        }

        QCalendarWidget QWidget#qt_calendar_navigationbar {
            background: #F0F7FF;
            border-bottom: 1px solid #C7D8EE;
        }

        QCalendarWidget QToolButton {
            color: #0F172A;
            background: transparent;
            border: none;
            padding: 6px;
            min-width: 28px;
            font-weight: 600;
        }

        QCalendarWidget QToolButton:hover {
            background: #E0F2FE;
            border-radius: 4px;
        }

        QCalendarWidget QMenu {
            background: #FFFFFF;
            color: #0F172A;
            border: 1px solid #B7CCE6;
        }

        QCalendarWidget QSpinBox {
            color: #0F172A;
            background: #FFFFFF;
            border: 1px solid #B7CCE6;
            selection-background-color: #0EA5E9;
        }

        QCalendarWidget QAbstractItemView:enabled {
            background: #FFFFFF;
            color: #0F172A;
            selection-background-color: #0EA5E9;
            selection-color: #FFFFFF;
            alternate-background-color: #F8FBFF;
            outline: 0;
        }

        QCalendarWidget QTableView {
            background: #FFFFFF;
            color: #0F172A;
        }

        QCalendarWidget QTableView#qt_calendar_calendarview QWidget#qt_scrollarea_viewport {
            background: #FFFFFF;
            color: #0F172A;
        }

        QCalendarWidget QTableView#qt_calendar_calendarview QHeaderView::section {
            background: #F8FBFF;
            color: #0F172A;
            border: none;
            border-bottom: 1px solid #C7D8EE;
            padding: 6px 0px;
            font-weight: 700;
        }

        QCalendarWidget QAbstractItemView:disabled {
            color: #94A3B8;
        }
    """


class NullableDateTimeWidget(QWidget):
    textChanged = Signal(str)

    def __init__(self, value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value: QDateTime | None = None

        self.edit = QLineEdit(self)
        self.edit.setReadOnly(True)
        self.edit.setPlaceholderText("yyyy-MM-dd HH:mm")
        self.edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit.installEventFilter(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.edit, 1)

        self.setFocusProxy(self.edit)
        self.set_text(value)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.edit and event.type() in {QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick}:
            self._open_popup()
            return True
        return super().eventFilter(watched, event)

    def set_text(self, value: str) -> None:
        parsed = parse_datetime(value)
        if parsed is None:
            self._value = None
            self.edit.clear()
            return
        self._value = QDateTime(QDate(parsed.year, parsed.month, parsed.day), QTime(parsed.hour, parsed.minute))
        self.edit.setText(self._value.toString("yyyy-MM-dd HH:mm"))

    def text(self) -> str:
        if self._value is None:
            return ""
        return self._value.toString("yyyy-MM-dd HH:mm")

    def clear(self) -> None:
        self._value = None
        self.edit.clear()
        self.textChanged.emit("")

    def _open_popup(self) -> None:
        initial = self._value or _current_minute_datetime()
        popup = _DateTimePopup(initial, self)
        popup.move(self.edit.mapToGlobal(self.edit.rect().bottomLeft()))
        if popup.exec() != QDialog.DialogCode.Accepted:
            return
        if popup.cleared:
            self.clear()
            return
        self._value = popup.selected_datetime()
        self.edit.setText(self._value.toString("yyyy-MM-dd HH:mm"))
        self.textChanged.emit(self.text())


class NullableDateWidget(QWidget):
    textChanged = Signal(str)

    def __init__(self, value: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value: QDate | None = None

        self.edit = QLineEdit(self)
        self.edit.setReadOnly(True)
        self.edit.setPlaceholderText("dd/MM/yy")
        self.edit.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit.installEventFilter(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.edit, 1)

        self.setFocusProxy(self.edit)
        self.set_text(value)

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is self.edit and event.type() in {QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick}:
            self._open_popup()
            return True
        return super().eventFilter(watched, event)

    def set_text(self, value: str) -> None:
        parsed = parse_date(value)
        if parsed is None:
            self._value = None
            self.edit.clear()
            return
        self._value = QDate(parsed.year, parsed.month, parsed.day)
        self.edit.setText(self._value.toString("dd/MM/yy"))

    def text(self) -> str:
        if self._value is None:
            return ""
        return self._value.toString("dd/MM/yy")

    def clear(self) -> None:
        self._value = None
        self.edit.clear()
        self.textChanged.emit("")

    def _open_popup(self) -> None:
        initial_date = self._value or QDate.currentDate()
        initial = QDateTime(initial_date, _current_minute_datetime().time())
        popup = _DateTimePopup(initial, self)
        popup.move(self.edit.mapToGlobal(self.edit.rect().bottomLeft()))
        if popup.exec() != QDialog.DialogCode.Accepted:
            return
        if popup.cleared:
            self.clear()
            return
        self._value = popup.selected_datetime().date()
        self.edit.setText(self._value.toString("dd/MM/yy"))
        self.textChanged.emit(self.text())


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
