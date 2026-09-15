import uuid
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any

class BookStatus:
    DRAFT = "Draft"
    AI_TRANSLATING = "AI Translating"
    AI_TRANSLATED = "AI Translated"
    NEEDS_HUMAN_REVIEW = "Needs Human Review"
    HUMAN_EDITING = "Human Editing"
    AI_RECHECKING = "AI Rechecking"
    HUMAN_APPROVED = "Human Approved"
    READY_FOR_PUBLISHING = "Ready for Publishing"
    PUBLISHED = "Published"

class CoverStatus:
    NOT_CREATED = "Not Created"
    DRAFT = "Draft"
    GENERATED = "Generated"
    HUMAN_SELECTED = "Human Selected"
    APPROVED = "Approved"

@dataclass
class BookModel:
    title: str
    author: str
    source_pdf_path: str
    translator: str = ""
    book_id: str = field(default_factory=lambda: f"book_{uuid.uuid4().hex[:10]}")
    source_lang: str = "English"
    target_lang: str = "Bangla"
    translation_status: str = BookStatus.DRAFT
    review_status: str = BookStatus.NEEDS_HUMAN_REVIEW
    cover_status: str = CoverStatus.NOT_CREATED
    overall_status: str = BookStatus.DRAFT
    cover_image_path: Optional[str] = None
    published_pdf_path: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def update_timestamp(self):
        self.updated_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BookModel":
        return cls(
            book_id=data.get("book_id", f"book_{uuid.uuid4().hex[:10]}"),
            title=data.get("title", "Untitled Book"),
            author=data.get("author", "Unknown Author"),
            source_pdf_path=data.get("source_pdf_path", ""),
            translator=data.get("translator", ""),
            source_lang=data.get("source_lang", "English"),
            target_lang=data.get("target_lang", "Bangla"),
            translation_status=data.get("translation_status", BookStatus.DRAFT),
            review_status=data.get("review_status", BookStatus.NEEDS_HUMAN_REVIEW),
            cover_status=data.get("cover_status", CoverStatus.NOT_CREATED),
            overall_status=data.get("overall_status", BookStatus.DRAFT),
            cover_image_path=data.get("cover_image_path"),
            published_pdf_path=data.get("published_pdf_path"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat())
        )
