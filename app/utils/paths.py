import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def get_asset_path(filename: str) -> Path:
    return BASE_DIR / "assets" / filename

def get_font_path(filename: str) -> Path:
    return BASE_DIR / "assets" / "fonts" / filename

def get_output_dir() -> Path:
    out_dir = BASE_DIR / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir

def get_cache_db_path() -> Path:
    cache_dir = BASE_DIR / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "translation_cache.db"
