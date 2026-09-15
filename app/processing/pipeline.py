import sqlite3
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, List, Any
from app.utils.paths import get_cache_db_path
from app.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class JobState:
    job_id: str
    source_pdf_path: str
    source_pdf_hash: str
    total_pages: int
    completed_pages: int = 0
    total_blocks: int = 0
    completed_blocks: int = 0
    failed_blocks: int = 0
    status: str = "CREATED"  # CREATED, ANALYZING, TRANSLATING, COMPLETED, PAUSED, FAILED, CANCELLED
    translated_map: Dict[str, str] = field(default_factory=dict)  # block_id -> translated_text
    units_map: Dict[str, Dict[str, Any]] = field(default_factory=dict) # block_id -> para dict data

    def __post_init__(self):
        if self.translated_map is None:
            self.translated_map = {}
        if self.units_map is None:
            self.units_map = {}

class JobManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or get_cache_db_path()
        self._init_db()

    def _init_db(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_state (
                    job_id TEXT PRIMARY KEY,
                    source_pdf_path TEXT NOT NULL,
                    source_pdf_hash TEXT NOT NULL,
                    total_pages INTEGER NOT NULL,
                    completed_pages INTEGER NOT NULL,
                    total_blocks INTEGER NOT NULL,
                    completed_blocks INTEGER NOT NULL,
                    failed_blocks INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    translated_map_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

            # Add units_map_json column if missing
            cursor.execute("PRAGMA table_info(job_state)")
            columns = [col[1] for col in cursor.fetchall()]
            if "units_map_json" not in columns:
                cursor.execute("ALTER TABLE job_state ADD COLUMN units_map_json TEXT DEFAULT '{}'")
                conn.commit()

    def save_job(self, job: JobState):
        map_json = json.dumps(job.translated_map, ensure_ascii=False)
        units_json = json.dumps(job.units_map, ensure_ascii=False)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO job_state
                (job_id, source_pdf_path, source_pdf_hash, total_pages, completed_pages,
                 total_blocks, completed_blocks, failed_blocks, status, translated_map_json, units_map_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job.job_id, job.source_pdf_path, job.source_pdf_hash,
                job.total_pages, job.completed_pages, job.total_blocks,
                job.completed_blocks, job.failed_blocks, job.status, map_json, units_json
            ))
            conn.commit()

    def load_job(self, job_id: str) -> Optional[JobState]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT job_id, source_pdf_path, source_pdf_hash, total_pages, completed_pages,
                       total_blocks, completed_blocks, failed_blocks, status, translated_map_json, units_map_json
                FROM job_state WHERE job_id = ?
            """, (job_id,))
            row = cursor.fetchone()
            if row:
                t_map = json.loads(row[9]) if row[9] else {}
                u_map = json.loads(row[10]) if len(row) > 10 and row[10] else {}
                return JobState(
                    job_id=row[0],
                    source_pdf_path=row[1],
                    source_pdf_hash=row[2],
                    total_pages=row[3],
                    completed_pages=row[4],
                    total_blocks=row[5],
                    completed_blocks=row[6],
                    failed_blocks=row[7],
                    status=row[8],
                    translated_map=t_map,
                    units_map=u_map
                )
        return None

    def find_job_by_path(self, source_pdf_path: str) -> Optional[JobState]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT job_id, source_pdf_path, source_pdf_hash, total_pages, completed_pages,
                       total_blocks, completed_blocks, failed_blocks, status, translated_map_json, units_map_json
                FROM job_state WHERE source_pdf_path = ? ORDER BY updated_at DESC LIMIT 1
            """, (str(source_pdf_path),))
            row = cursor.fetchone()
            if row:
                t_map = json.loads(row[9]) if row[9] else {}
                u_map = json.loads(row[10]) if len(row) > 10 and row[10] else {}
                return JobState(
                    job_id=row[0],
                    source_pdf_path=row[1],
                    source_pdf_hash=row[2],
                    total_pages=row[3],
                    completed_pages=row[4],
                    total_blocks=row[5],
                    completed_blocks=row[6],
                    failed_blocks=row[7],
                    status=row[8],
                    translated_map=t_map,
                    units_map=u_map
                )
        return None
