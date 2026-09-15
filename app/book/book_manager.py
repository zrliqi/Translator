import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from app.book.book_model import BookModel, BookStatus, CoverStatus
from app.utils.paths import BASE_DIR
from app.utils.logging import get_logger

logger = get_logger(__name__)

def get_books_db_path() -> Path:
    cache_dir = BASE_DIR / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "books.db"

class BookManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_books_db_path()
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    book_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    author TEXT NOT NULL,
                    source_pdf_path TEXT NOT NULL,
                    translator TEXT,
                    source_lang TEXT NOT NULL,
                    target_lang TEXT NOT NULL,
                    translation_status TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    cover_status TEXT NOT NULL,
                    overall_status TEXT NOT NULL,
                    cover_image_path TEXT,
                    published_pdf_path TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def save_book(self, book: BookModel) -> BookModel:
        book.update_timestamp()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO books (
                    book_id, title, author, source_pdf_path, translator,
                    source_lang, target_lang, translation_status, review_status,
                    cover_status, overall_status, cover_image_path, published_pdf_path,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                book.book_id, book.title, book.author, book.source_pdf_path,
                book.translator, book.source_lang, book.target_lang,
                book.translation_status, book.review_status, book.cover_status,
                book.overall_status, book.cover_image_path, book.published_pdf_path,
                book.created_at, book.updated_at
            ))
            conn.commit()
        return book

    def get_book(self, book_id: str) -> Optional[BookModel]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT book_id, title, author, source_pdf_path, translator,
                       source_lang, target_lang, translation_status, review_status,
                       cover_status, overall_status, cover_image_path, published_pdf_path,
                       created_at, updated_at
                FROM books WHERE book_id = ?
            """, (book_id,))
            row = cursor.fetchone()
            if row:
                return BookModel(
                    book_id=row[0],
                    title=row[1],
                    author=row[2],
                    source_pdf_path=row[3],
                    translator=row[4] or "",
                    source_lang=row[5],
                    target_lang=row[6],
                    translation_status=row[7],
                    review_status=row[8],
                    cover_status=row[9],
                    overall_status=row[10],
                    cover_image_path=row[11],
                    published_pdf_path=row[12],
                    created_at=row[13],
                    updated_at=row[14]
                )
        return None

    def list_books(self) -> List[BookModel]:
        books = []
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT book_id, title, author, source_pdf_path, translator,
                       source_lang, target_lang, translation_status, review_status,
                       cover_status, overall_status, cover_image_path, published_pdf_path,
                       created_at, updated_at
                FROM books ORDER BY updated_at DESC
            """)
            rows = cursor.fetchall()
            for row in rows:
                books.append(BookModel(
                    book_id=row[0],
                    title=row[1],
                    author=row[2],
                    source_pdf_path=row[3],
                    translator=row[4] or "",
                    source_lang=row[5],
                    target_lang=row[6],
                    translation_status=row[7],
                    review_status=row[8],
                    cover_status=row[9],
                    overall_status=row[10],
                    cover_image_path=row[11],
                    published_pdf_path=row[12],
                    created_at=row[13],
                    updated_at=row[14]
                ))
        return books

    def delete_book(self, book_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM books WHERE book_id = ?", (book_id,))
            conn.commit()
            return cursor.rowcount > 0

    def update_translator(self, book_id: str, translator: str) -> Optional[BookModel]:
        book = self.get_book(book_id)
        if book:
            book.translator = translator
            return self.save_book(book)
        return None
