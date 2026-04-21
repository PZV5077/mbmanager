from __future__ import annotations

import json
import tempfile
from pathlib import Path


class UiSettingsStore:
    def __init__(self, data_dir: Path) -> None:
        self.path = data_dir / "ui_settings.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, object]:
        if not self.path.exists():
            return {}
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def save(self, data: dict[str, object]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            delete=False,
            dir=str(self.path.parent),
            prefix=".ui_settings_",
            suffix=".tmp",
        ) as tf:
            json.dump(data, tf, ensure_ascii=True, indent=2)
            temp = tf.name
        Path(temp).replace(self.path)

    def get_column_widths(self, tab_key: str, defaults: list[int], expected_len: int) -> list[int]:
        data = self.load()
        tabs = data.get("tabs")
        if not isinstance(tabs, dict):
            return list(defaults)
        tab_data = tabs.get(tab_key)
        if not isinstance(tab_data, dict):
            return list(defaults)
        widths = tab_data.get("column_widths")
        if not isinstance(widths, list):
            return list(defaults)
        if len(widths) != expected_len or not all(isinstance(w, int) and w > 0 for w in widths):
            return list(defaults)
        return list(widths)

    def set_column_widths(self, tab_key: str, widths: list[int]) -> None:
        data = self.load()
        tabs = data.get("tabs")
        if not isinstance(tabs, dict):
            tabs = {}
            data["tabs"] = tabs
        tab_data = tabs.get(tab_key)
        if not isinstance(tab_data, dict):
            tab_data = {}
            tabs[tab_key] = tab_data
        tab_data["column_widths"] = [int(w) for w in widths]
        self.save(data)

    def get_font_scale(self, default: int = 100) -> int:
        data = self.load()
        scale = data.get("font_scale")
        if isinstance(scale, int) and 50 <= scale <= 200:
            return scale
        return default

    def set_font_scale(self, scale: int) -> None:
        data = self.load()
        data["font_scale"] = max(50, min(200, scale))
        self.save(data)

    def get_theme_mode(self, default: str = "dark") -> str:
        data = self.load()
        mode = data.get("theme_mode")
        if mode in {"light", "dark"}:
            return str(mode)
        return default

    def set_theme_mode(self, mode: str) -> None:
        data = self.load()
        data["theme_mode"] = "dark" if mode == "dark" else "light"
        self.save(data)
