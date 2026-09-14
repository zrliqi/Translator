import os
from pathlib import Path
from typing import Dict, Optional
from app.utils.logging import get_logger
from app.utils.paths import get_font_path

logger = get_logger(__name__)

class FontManager:
    _instance = None

    def __init__(self):
        self.registered_fonts: Dict[str, Path] = {}
        self._discover_fonts()

    @classmethod
    def get_instance(cls) -> "FontManager":
        if cls._instance is None:
            cls._instance = FontManager()
        return cls._instance

    def _discover_fonts(self):
        sans_path = get_font_path("NotoSansBengali-Regular.ttf")
        serif_path = get_font_path("NotoSerifBengali-Regular.ttf")

        if sans_path.exists():
            self.registered_fonts["Noto Sans Bengali"] = sans_path
        if serif_path.exists():
            self.registered_fonts["Noto Serif Bengali"] = serif_path

    def get_font_path(self, font_name: str) -> Optional[Path]:
        return self.registered_fonts.get(font_name)

    def is_font_available(self, font_name: str) -> bool:
        path = self.get_font_path(font_name)
        return path is not None and path.exists()

    def list_available_fonts(self) -> list[str]:
        return list(self.registered_fonts.keys())
