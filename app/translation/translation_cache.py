import sqlite3
import hashlib
from pathlib import Path
from typing import Optional
from app.utils.paths import get_cache_db_path
from app.utils.logging import get_logger

logger = get_logger(__name__)

class TranslationCache:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_cache_db_path()
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS translation_cache (
                    cache_key TEXT PRIMARY KEY,
                    source_text TEXT NOT NULL,
                    target_text TEXT NOT NULL,
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def _generate_key(self, source_text: str, source_lang: str, target_lang: str, model_name: str) -> str:
        raw = f"{source_text.strip()}|{source_lang}|{target_lang}|{model_name}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, source_text: str, source_lang: str = "en", target_lang: str = "bn", model_name: str = "default") -> Optional[str]:
        key = self._generate_key(source_text, source_lang, target_lang, model_name)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT target_text FROM translation_cache WHERE cache_key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row[0]
        return None

    def put(self, source_text: str, target_text: str, source_lang: str = "en", target_lang: str = "bn", model_name: str = "default"):
        if not source_text.strip() or not target_text.strip():
            return
        key = self._generate_key(source_text, source_lang, target_lang, model_name)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO translation_cache
                (cache_key, source_text, target_text, source_lang, target_lang, model_name)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (key, source_text.strip(), target_text.strip(), source_lang, target_lang, model_name))
            conn.commit()
