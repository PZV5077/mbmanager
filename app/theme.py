from __future__ import annotations

from pathlib import Path
from typing import Literal

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

ThemeMode = Literal["light", "dark"]


def normalize_theme_mode(mode: str | None) -> ThemeMode:
    return "dark" if mode == "dark" else "light"


def theme_toggle_label(mode: str) -> str:
    active = normalize_theme_mode(mode)
    return "Dark Mode" if active == "light" else "Light Mode"


def apply_galaxy_theme(app: QApplication, mode: str = "light") -> ThemeMode:
    active_mode = normalize_theme_mode(mode)
    app.setFont(QFont("Noto Sans", 10))
    app.setStyleSheet(_light_stylesheet() if active_mode == "light" else _dark_stylesheet())
    app.setProperty("theme_mode", active_mode)
    return active_mode


def _icon_uri(file_name: str) -> str:
    icon_path = Path(__file__).resolve().parent / "icons" / file_name
    return icon_path.as_uri()


def _light_stylesheet() -> str:
    return """
        QMainWindow {
            background: qlineargradient(
                x1: 0,
                y1: 0,
                x2: 1,
                y2: 1,
                stop: 0 #F8FCFF,
                stop: 0.54 #EBF5FF,
                stop: 1 #DDEBFF
            );
        }

        QWidget {
            color: #0F172A;
            font-size: 13px;
        }

        QTabWidget::pane {
            border: 1px solid #C7D8EE;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.86);
        }

        QTabBar::tab {
            background: rgba(255, 255, 255, 0.72);
            color: #1E293B;
            border: 1px solid #C7D8EE;
            border-bottom: none;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            padding: 8px 15px;
            margin-right: 6px;
            font-weight: 600;
        }

        QTabBar::tab:hover {
            background: #F4FAFF;
            color: #0C4A6E;
        }

        QTabBar::tab:selected {
            background: #FFFFFF;
            color: #0F766E;
        }

        QLineEdit,
        QComboBox,
        QDateEdit,
        QDateTimeEdit,
        QSpinBox {
            background: #FFFFFF;
            color: #0F172A;
            border: 1px solid #B7CCE6;
            border-radius: 0px;
            padding: 6px 8px;
            selection-background-color: #0284C7;
            selection-color: #FFFFFF;
        }

        QAbstractItemView {
            background: #FFFFFF;
            color: #0F172A;
            selection-background-color: #0EA5E9;
            selection-color: #FFFFFF;
            outline: 0;
        }

        QAbstractItemView::item {
            color: #0F172A;
        }

        QLineEdit:focus,
        QComboBox:focus,
        QDateEdit:focus,
        QDateTimeEdit:focus,
        QSpinBox:focus {
            border: 1px solid #0EA5E9;
        }

        QTableWidget QLineEdit,
        QTableWidget QComboBox,
        QTableWidget QDateEdit,
        QTableWidget QDateTimeEdit,
        QTableWidget QSpinBox {
            border-radius: 0px;
            border: 1px solid #D3DFEE;
            background: transparent;
            color: #0F172A;
            padding: 2px 4px;
            margin: 0px;
        }

        QTableWidget QLineEdit:focus,
        QTableWidget QComboBox:focus,
        QTableWidget QDateEdit:focus,
        QTableWidget QDateTimeEdit:focus,
        QTableWidget QSpinBox:focus {
            border: 1px solid #0EA5E9;
            background: #FFFFFF;
        }

        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border: none;
            border-left: 1px solid #B7CCE6;
            background: #F3F8FF;
        }

        QComboBox::drop-down:hover {
            background: #E8F2FF;
        }

        QComboBox::down-arrow {
            image: url("__COMBO_ARROW_LIGHT__");
            width: 12px;
            height: 8px;
        }

        QComboBox QAbstractItemView {
            background: #FFFFFF;
            color: #0F172A;
            border: 1px solid #8FB3DA;
            selection-background-color: #0EA5E9;
            selection-color: #FFFFFF;
            outline: 0;
        }

        QComboBox QAbstractItemView::item {
            min-height: 26px;
            padding: 4px 8px;
            background: #FFFFFF;
            color: #0F172A;
        }

        QComboBox QAbstractItemView::item:hover {
            background: #E0F2FE;
            color: #0C4A6E;
        }

        QMenu {
            background: #FFFFFF;
            border: 1px solid #B7CCE6;
            color: #0F172A;
        }

        QMenu::item {
            color: #0F172A;
        }

        QMenu::item:selected {
            background: #E0F2FE;
            color: #0C4A6E;
        }

        QPushButton {
            background: qlineargradient(
                x1: 0,
                y1: 0,
                x2: 1,
                y2: 1,
                stop: 0 #0EA5E9,
                stop: 1 #0F766E
            );
            color: #FFFFFF;
            border: none;
            border-radius: 9px;
            padding: 8px 14px;
            font-weight: 700;
        }

        QPushButton:hover {
            background: qlineargradient(
                x1: 0,
                y1: 0,
                x2: 1,
                y2: 1,
                stop: 0 #0284C7,
                stop: 1 #0F766E
            );
        }

        QPushButton:pressed {
            background: #0F766E;
        }

        QPushButton:disabled {
            background: #94A3B8;
            color: #E2E8F0;
        }

        QPushButton#themeToggleButton {
            background: #FFFFFF;
            color: #0F172A;
            border: 1px solid #B7CCE6;
            padding: 8px 12px;
            font-weight: 700;
        }

        QPushButton#themeToggleButton:hover {
            background: #F0F9FF;
            border: 1px solid #0EA5E9;
            color: #0369A1;
        }

        QToolButton {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid #BFD1E7;
            border-radius: 8px;
            padding: 4px 8px;
            font-weight: 600;
        }

        QToolButton:hover {
            background: #FFFFFF;
            border: 1px solid #7FA7D8;
        }

        QRadioButton {
            spacing: 8px;
            background: transparent;
        }

        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 1px solid #7FA5CF;
            background: #FFFFFF;
        }

        QRadioButton::indicator:hover {
            border: 1px solid #0EA5E9;
            background: #F0F9FF;
        }

        QRadioButton::indicator:checked {
            border: 1px solid #0284C7;
            background: qradialgradient(
                cx: 0.5,
                cy: 0.5,
                radius: 0.6,
                fx: 0.5,
                fy: 0.5,
                stop: 0 #FFFFFF,
                stop: 0.35 #FFFFFF,
                stop: 0.36 #0EA5E9,
                stop: 1 #0EA5E9
            );
        }

        QRadioButton::indicator:disabled {
            background: #E2E8F0;
            border: 1px solid #94A3B8;
        }

        QCheckBox {
            spacing: 8px;
            background: transparent;
        }

        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid #7FA5CF;
            background: #FFFFFF;
        }

        QCheckBox::indicator:unchecked:hover {
            background: #F0F9FF;
            border: 1px solid #0EA5E9;
        }

        QCheckBox::indicator:checked {
            background: #0EA5E9;
            border: 1px solid #0284C7;
        }

        QTableWidget {
            background: rgba(255, 255, 255, 0.95);
            gridline-color: #E2E8F0;
            border: 1px solid #C9D9EE;
            border-radius: 12px;
            alternate-background-color: #F8FBFF;
            color: #0F172A;
        }

        QTableWidget::item:selected {
            background: #CFEFFF;
            color: #0C4A6E;
        }

        QHeaderView::section {
            background: #E4EFFB;
            color: #0F172A;
            border: none;
            border-right: 1px solid #CBDCF1;
            border-bottom: 1px solid #CBDCF1;
            padding: 8px;
            font-weight: 700;
        }

        QScrollBar:vertical,
        QScrollBar:horizontal {
            background: transparent;
            border: none;
        }

        QScrollBar:vertical {
            width: 12px;
        }

        QScrollBar:horizontal {
            height: 12px;
        }

        QScrollBar::handle:vertical,
        QScrollBar::handle:horizontal {
            background: #9CC2EA;
            border-radius: 6px;
            min-height: 26px;
            min-width: 26px;
        }

        QLabel[role="panelTitle"] {
            font-size: 16px;
            font-weight: 800;
            color: #0B3B4A;
        }
    """.replace("__COMBO_ARROW_LIGHT__", _icon_uri("chevron_down_dark.svg"))


def _dark_stylesheet() -> str:
    return """
        QMainWindow {
            background: qlineargradient(
                x1: 0,
                y1: 0,
                x2: 1,
                y2: 1,
                stop: 0 #0B1020,
                stop: 0.55 #131B32,
                stop: 1 #1C2746
            );
        }

        QWidget {
            color: #E2E8F0;
            font-size: 13px;
        }

        QTabWidget::pane {
            border: 1px solid #364761;
            border-radius: 12px;
            background: rgba(15, 23, 42, 0.9);
        }

        QTabBar::tab {
            background: rgba(30, 41, 59, 0.9);
            color: #CBD5E1;
            border: 1px solid #364761;
            border-bottom: none;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            padding: 8px 15px;
            margin-right: 6px;
            font-weight: 600;
        }

        QTabBar::tab:hover {
            background: #24324A;
            color: #E2E8F0;
        }

        QTabBar::tab:selected {
            background: #0F172A;
            color: #67E8F9;
        }

        QLineEdit,
        QComboBox,
        QDateEdit,
        QDateTimeEdit,
        QSpinBox {
            background: #0F172A;
            color: #E2E8F0;
            border: 1px solid #3A4B64;
            border-radius: 0px;
            padding: 6px 8px;
            selection-background-color: #0284C7;
            selection-color: #F8FAFC;
        }

        QAbstractItemView {
            background: #111827;
            color: #E5E7EB;
            selection-background-color: #0369A1;
            selection-color: #F8FAFC;
            outline: 0;
        }

        QAbstractItemView::item {
            color: #E5E7EB;
        }

        QLineEdit:focus,
        QComboBox:focus,
        QDateEdit:focus,
        QDateTimeEdit:focus,
        QSpinBox:focus {
            border: 1px solid #22D3EE;
        }

        QTableWidget QLineEdit,
        QTableWidget QComboBox,
        QTableWidget QDateEdit,
        QTableWidget QDateTimeEdit,
        QTableWidget QSpinBox {
            border-radius: 0px;
            border: 1px solid #2A3A54;
            background: transparent;
            color: #E2E8F0;
            padding: 2px 4px;
            margin: 0px;
        }

        QTableWidget QLineEdit:focus,
        QTableWidget QComboBox:focus,
        QTableWidget QDateEdit:focus,
        QTableWidget QDateTimeEdit:focus,
        QTableWidget QSpinBox:focus {
            border: 1px solid #22D3EE;
            background: #0F172A;
        }

        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border: none;
            border-left: 1px solid #3A4B64;
            background: #1D2A41;
        }

        QComboBox::drop-down:hover {
            background: #24324A;
        }

        QComboBox::down-arrow {
            image: url("__COMBO_ARROW_DARK__");
            width: 12px;
            height: 8px;
        }

        QComboBox QAbstractItemView {
            background: #111827;
            color: #E5E7EB;
            border: 1px solid #3A4B64;
            selection-background-color: #0369A1;
            selection-color: #F8FAFC;
            outline: 0;
        }

        QComboBox QAbstractItemView::item {
            min-height: 26px;
            padding: 4px 8px;
            background: #111827;
            color: #E5E7EB;
        }

        QComboBox QAbstractItemView::item:hover {
            background: #1E293B;
            color: #E2E8F0;
        }

        QMenu {
            background: #111827;
            border: 1px solid #3A4B64;
            color: #E5E7EB;
        }

        QMenu::item {
            color: #E5E7EB;
        }

        QMenu::item:selected {
            background: #1E293B;
            color: #67E8F9;
        }

        QPushButton {
            background: qlineargradient(
                x1: 0,
                y1: 0,
                x2: 1,
                y2: 1,
                stop: 0 #0EA5E9,
                stop: 1 #0369A1
            );
            color: #F8FAFC;
            border: none;
            border-radius: 9px;
            padding: 8px 14px;
            font-weight: 700;
        }

        QPushButton:hover {
            background: qlineargradient(
                x1: 0,
                y1: 0,
                x2: 1,
                y2: 1,
                stop: 0 #38BDF8,
                stop: 1 #0369A1
            );
        }

        QPushButton:pressed {
            background: #075985;
        }

        QPushButton:disabled {
            background: #334155;
            color: #94A3B8;
        }

        QPushButton#themeToggleButton {
            background: #1E293B;
            color: #E2E8F0;
            border: 1px solid #3A4B64;
            padding: 8px 12px;
            font-weight: 700;
        }

        QPushButton#themeToggleButton:hover {
            background: #24324A;
            border: 1px solid #22D3EE;
            color: #67E8F9;
        }

        QToolButton {
            background: rgba(30, 41, 59, 0.9);
            border: 1px solid #3A4B64;
            border-radius: 8px;
            padding: 4px 8px;
            font-weight: 600;
            color: #E2E8F0;
        }

        QToolButton:hover {
            background: #24324A;
            border: 1px solid #22D3EE;
        }

        QRadioButton {
            spacing: 8px;
            background: transparent;
        }

        QRadioButton::indicator {
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 1px solid #5B6B82;
            background: #0B1220;
        }

        QRadioButton::indicator:hover {
            border: 1px solid #22D3EE;
            background: #111E33;
        }

        QRadioButton::indicator:checked {
            border: 1px solid #0891B2;
            background: qradialgradient(
                cx: 0.5,
                cy: 0.5,
                radius: 0.6,
                fx: 0.5,
                fy: 0.5,
                stop: 0 #FFFFFF,
                stop: 0.35 #FFFFFF,
                stop: 0.36 #22D3EE,
                stop: 1 #22D3EE
            );
        }

        QRadioButton::indicator:disabled {
            background: #1E293B;
            border: 1px solid #475569;
        }

        QCheckBox {
            spacing: 8px;
            background: transparent;
        }

        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid #5B6B82;
            background: #0B1220;
        }

        QCheckBox::indicator:unchecked:hover {
            border: 1px solid #22D3EE;
            background: #111E33;
        }

        QCheckBox::indicator:checked {
            border: 1px solid #0891B2;
            background: #22D3EE;
        }

        QTableWidget {
            background: rgba(10, 17, 31, 0.95);
            gridline-color: #223149;
            border: 1px solid #364761;
            border-radius: 12px;
            alternate-background-color: #121D33;
            color: #E2E8F0;
        }

        QTableWidget::item:selected {
            background: #164E63;
            color: #ECFEFF;
        }

        QHeaderView::section {
            background: #1E293B;
            color: #E2E8F0;
            border: none;
            border-right: 1px solid #364761;
            border-bottom: 1px solid #364761;
            padding: 8px;
            font-weight: 700;
        }

        QScrollBar:vertical,
        QScrollBar:horizontal {
            background: transparent;
            border: none;
        }

        QScrollBar:vertical {
            width: 12px;
        }

        QScrollBar:horizontal {
            height: 12px;
        }

        QScrollBar::handle:vertical,
        QScrollBar::handle:horizontal {
            background: #334155;
            border-radius: 6px;
            min-height: 26px;
            min-width: 26px;
        }

        QScrollBar::handle:vertical:hover,
        QScrollBar::handle:horizontal:hover {
            background: #475569;
        }

        QLabel[role="panelTitle"] {
            font-size: 16px;
            font-weight: 800;
            color: #A5F3FC;
        }
    """.replace("__COMBO_ARROW_DARK__", _icon_uri("chevron_down_light.svg"))
