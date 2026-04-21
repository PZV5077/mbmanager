from __future__ import annotations

from typing import Literal

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

ThemeMode = Literal["light", "dark"]

_MATERIAL_THEME_BY_MODE: dict[ThemeMode, str] = {
    "dark": "dark_blue.xml",
    "light": "light_blue.xml",
}


def normalize_theme_mode(mode: str | None) -> ThemeMode:
    return "dark" if mode == "dark" else "light"


def theme_toggle_label(mode: str) -> str:
    active = normalize_theme_mode(mode)
    return "Dark Mode" if active == "light" else "Light Mode"


def apply_galaxy_theme(app: QApplication, mode: str = "dark") -> ThemeMode:
    active_mode = normalize_theme_mode(mode)
    app.setFont(QFont("Noto Sans", 10))

    apply_stylesheet(
        app,
        theme=_MATERIAL_THEME_BY_MODE[active_mode],
        invert_secondary=(active_mode == "light"),
        extra=_theme_extra(),
    )

    app.setStyleSheet(app.styleSheet() + "\n" + _overlay_stylesheet(active_mode))
    app.setProperty("theme_mode", active_mode)
    return active_mode


def _theme_extra() -> dict[str, str]:
    return {
        "font_family": "Noto Sans",
        "font_size": "13px",
        "line_height": "13px",
        "density_scale": "-1",
        "danger": "#B4234D",
        "warning": "#D97706",
        "success": "#2563EB",
    }


def _overlay_stylesheet(mode: ThemeMode) -> str:
    if mode == "dark":
        palette = {
            "window_bg": "#0D1526",
            "pane_bg": "rgba(14, 22, 36, 0.86)",
            "surface_bg": "rgba(17, 28, 51, 0.72)",
            "surface_alt_bg": "rgba(21, 40, 65, 0.56)",
            "border": "#314766",
            "tab_bg": "#132138",
            "tab_hover": "#1C2E4A",
            "tab_selected": "#1F3C67",
            "text_primary": "#E5ECF8",
            "text_secondary": "#9FB1CE",
            "chip_bg": "#1A2F52",
            "chip_border": "#2D4A74",
            "chip_text": "#DEE9FF",
            "chip_success_bg": "#1C4534",
            "chip_success_text": "#D9FBE8",
            "chip_warning_bg": "#584117",
            "chip_warning_text": "#FFEBC8",
            "chip_info_bg": "#173A63",
            "chip_info_text": "#DDEBFF",
            "chip_error_bg": "#5D1F2B",
            "chip_error_text": "#FFE1E8",
            "danger_bg": "#8F2341",
            "danger_hover": "#A62A4C",
            "danger_text": "#FFF1F2",
            "header_bg": "#152841",
            "header_border": "#273A57",
            "selection_bg": "#1E3A8A",
            "selection_text": "#EAF1FF",
            "button_hover": "#28456E",
        }
    else:
        palette = {
            "window_bg": "#F4F8FF",
            "pane_bg": "rgba(255, 255, 255, 0.9)",
            "surface_bg": "rgba(255, 255, 255, 0.88)",
            "surface_alt_bg": "rgba(242, 247, 255, 0.88)",
            "border": "#C8D8EE",
            "tab_bg": "#EAF1FF",
            "tab_hover": "#DDE9FF",
            "tab_selected": "#FFFFFF",
            "text_primary": "#172554",
            "text_secondary": "#486088",
            "chip_bg": "#E9F0FF",
            "chip_border": "#C7D8F1",
            "chip_text": "#1E3A8A",
            "chip_success_bg": "#DCFCE7",
            "chip_success_text": "#166534",
            "chip_warning_bg": "#FEF3C7",
            "chip_warning_text": "#92400E",
            "chip_info_bg": "#DBEAFE",
            "chip_info_text": "#1E3A8A",
            "chip_error_bg": "#FDE2E8",
            "chip_error_text": "#9F1239",
            "danger_bg": "#D1435B",
            "danger_hover": "#E1546D",
            "danger_text": "#FFF5F7",
            "header_bg": "#E8F0FF",
            "header_border": "#D2E0F4",
            "selection_bg": "#DBEAFE",
            "selection_text": "#1E3A8A",
            "button_hover": "#DCE8FF",
        }

    return f"""
        QMainWindow {{
            background: {palette['window_bg']};
        }}

        QWidget {{
            font-size: 13px;
        }}

        QTabWidget::pane {{
            border: 1px solid {palette['border']};
            border-radius: 14px;
            background: {palette['pane_bg']};
        }}

        QTabBar::tab {{
            background: {palette['tab_bg']};
            color: {palette['text_primary']};
            border: 1px solid {palette['border']};
            border-bottom: none;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            padding: 8px 16px;
            margin-right: 6px;
            font-weight: 700;
            text-transform: none;
        }}

        QTabBar::tab:hover {{
            background: {palette['tab_hover']};
        }}

        QTabBar::tab:selected {{
            background: {palette['tab_selected']};
        }}

        QLineEdit,
        QComboBox,
        QDateEdit,
        QDateTimeEdit,
        QSpinBox {{
            border-radius: 8px;
            padding: 6px 10px;
        }}

        QAbstractItemView {{
            outline: 0;
        }}

        QTableWidget {{
            border: 1px solid {palette['border']};
            border-radius: 12px;
            gridline-color: {palette['header_border']};
        }}

        QTableWidget::item:selected {{
            background: {palette['selection_bg']};
            color: {palette['selection_text']};
        }}

        QHeaderView::section {{
            background: {palette['header_bg']};
            border: none;
            border-right: 1px solid {palette['header_border']};
            border-bottom: 1px solid {palette['header_border']};
            padding: 8px;
            font-weight: 700;
        }}

        QPushButton#themeToggleButton,
        QPushButton#settingsButton {{
            border-radius: 8px;
            padding: 2px 3px;
            font-weight: 700;
            text-transform: none;
            
        }}

        QPushButton#themeToggleButton:hover,
        QPushButton#settingsButton:hover {{
            background: {palette['button_hover']};
        }}

        QPushButton#settingsButton[active="true"] {{
            background: {palette['button_hover']};
            border: 1px solid {palette['border']};
            font-weight: 800;
        }}

        QLabel[role="panelTitle"] {{
            font-size: 18px;
            font-weight: 800;
            color: {palette['text_primary']};
        }}

        QLabel[role="metaInfo"] {{
            color: {palette['text_secondary']};
        }}

        QLabel[role="panelSubtitle"] {{
            color: {palette['text_secondary']};
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.2px;
        }}

        QLabel[role="sectionLabel"] {{
            color: {palette['text_secondary']};
            font-size: 11px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.7px;
            padding-right: 2px;
        }}

        QLabel[role="fieldLabel"] {{
            color: {palette['text_secondary']};
            font-size: 12px;
            font-weight: 700;
            padding-right: 2px;
        }}

        QLabel[role="metricChip"] {{
            background: {palette['chip_bg']};
            color: {palette['chip_text']};
            border: 1px solid {palette['chip_border']};
            border-radius: 999px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 700;
        }}

        QLabel[role="metricChip"][state="success"],
        QLabel[role="metricChip"][state="done"] {{
            background: {palette['chip_success_bg']};
            color: {palette['chip_success_text']};
            border: none;
        }}

        QLabel[role="metricChip"][state="warning"],
        QLabel[role="metricChip"][state="pending"] {{
            background: {palette['chip_warning_bg']};
            color: {palette['chip_warning_text']};
            border: none;
        }}

        QLabel[role="metricChip"][state="info"] {{
            background: {palette['chip_info_bg']};
            color: {palette['chip_info_text']};
            border: none;
        }}

        QLabel[role="metricChip"][state="error"],
        QLabel[role="metricChip"][state="alert"] {{
            background: {palette['chip_error_bg']};
            color: {palette['chip_error_text']};
            border: none;
        }}

        QFrame#workspaceHeader,
        QFrame#controlBar,
        QFrame#actionBar,
        QFrame#filterPanel {{
            background: {palette['surface_bg']};
            border: 1px solid {palette['border']};
            border-radius: 12px;
        }}

        QFrame#controlBar,
        QFrame#actionBar,
        QFrame#filterPanel {{
            background: {palette['surface_alt_bg']};
        }}

        QLineEdit[role="toolbarSearch"],
        QComboBox[role="toolbarSelect"] {{
            min-height: 34px;
            font-weight: 600;
        }}

        QLineEdit[role="cellEditor"],
        QComboBox[role="cellEditor"] {{
            min-height: 24px;
            border-radius: 6px;
            padding: 3px 7px;
        }}

        QCheckBox[role="cellToggle"] {{
            padding: 0px 2px;
        }}

        QTableWidget#ledgerTable {{
            background: {palette['pane_bg']};
        }}

        QTableWidget#ledgerTable::item {{
            padding-left: 4px;
            padding-right: 4px;
        }}

        QToolButton[variant="secondary"] {{
            background: {palette['tab_bg']};
            color: {palette['text_primary']};
            border: 1px solid {palette['border']};
            border-radius: 8px;
            padding: 7px 11px;
            font-weight: 700;
        }}

        QToolButton[variant="secondary"]:hover {{
            background: {palette['tab_hover']};
        }}

        QPushButton[variant="ghost"] {{
            background: transparent;
            color: {palette['text_secondary']};
            border: 1px solid {palette['border']};
            border-radius: 8px;
            padding: 8px 12px;
            text-transform: none;
            font-weight: 700;
        }}

        QPushButton[variant="ghost"]:hover {{
            background: {palette['button_hover']};
            color: {palette['text_primary']};
        }}

        QPushButton[variant="primary"] {{
            border-radius: 8px;
            padding: 8px 12px;
            text-transform: none;
            font-weight: 800;
        }}

        QPushButton[variant="secondary"] {{
            background: {palette['tab_bg']};
            color: {palette['text_primary']};
            border: 1px solid {palette['border']};
            border-radius: 8px;
            padding: 8px 12px;
            text-transform: none;
            font-weight: 700;
        }}

        QPushButton[variant="secondary"]:hover {{
            background: {palette['tab_hover']};
        }}

        QPushButton[variant="danger"] {{
            background: {palette['danger_bg']};
            color: {palette['danger_text']};
            border: none;
            border-radius: 8px;
            padding: 8px 12px;
            text-transform: none;
            font-weight: 700;
        }}

        QPushButton[variant="danger"]:hover {{
            background: {palette['danger_hover']};
        }}

        QPushButton[variant="danger"]:pressed {{
            background: {palette['danger_hover']};
        }}
    """
