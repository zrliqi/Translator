from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime

@dataclass
class ParagraphModel:
    id: str
    text: str
    translated_text: Optional[str] = None
    is_heading: bool = False
    is_page_number: bool = False
    bbox: Optional[Tuple[float, float, float, float]] = None
    font_size: float = 12.0
    status: str = "pending"  # "pending", "translated", "failed", "skipped"
    error_message: Optional[str] = None

    # Human Review & Version History Extension
    ai_translation: Optional[str] = None
    human_translation: Optional[str] = None
    review_status: str = "Needs Review"  # "AI Translated", "Needs Review", "Human Edited", "AI Rechecking", "Approved"
    edited_by: Optional[str] = None
    edited_at: Optional[str] = None
    ai_recheck_status: Optional[str] = None  # "PASS", "SUGGESTION", "POTENTIAL ISSUE"
    ai_recheck_feedback: Optional[str] = None
    revisions: List[Dict[str, Any]] = field(default_factory=list)
    comments: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def source_text(self) -> str:
        return self.text

    @property
    def current_translation(self) -> str:
        if self.human_translation is not None and self.human_translation.strip():
            return self.human_translation
        if self.translated_text is not None and self.translated_text.strip():
            return self.translated_text
        if self.ai_translation is not None and self.ai_translation.strip():
            return self.ai_translation
        return ""

    def has_human_edit(self) -> bool:
        return bool(self.human_translation and self.human_translation.strip()) or self.review_status in ("Human Edited", "Approved")

    def add_human_edit(self, new_text: str, editor: str = "Human Reviewer"):
        current = self.current_translation
        if current:
            self.revisions.append({
                "version": len(self.revisions) + 1,
                "text": current,
                "type": "AI" if not self.human_translation else "Human",
                "editor": self.edited_by or "AI System",
                "timestamp": datetime.now().isoformat()
            })

        self.human_translation = new_text
        self.translated_text = new_text
        self.review_status = "Human Edited"
        self.edited_by = editor
        self.edited_at = datetime.now().isoformat()

    def revert_to_version(self, version_index: int) -> bool:
        if 0 <= version_index < len(self.revisions):
            rev = self.revisions[version_index]
            # Save current as revision before reverting
            current = self.current_translation
            self.revisions.append({
                "version": len(self.revisions) + 1,
                "text": current,
                "type": "Human",
                "editor": self.edited_by or "User",
                "timestamp": datetime.now().isoformat()
            })

            reverted_text = rev["text"]
            if rev["type"] == "AI":
                self.human_translation = None
                self.translated_text = reverted_text
                self.ai_translation = reverted_text
                self.review_status = "AI Translated"
            else:
                self.human_translation = reverted_text
                self.translated_text = reverted_text
                self.review_status = "Human Edited"

            self.edited_at = datetime.now().isoformat()
            return True
        return False

    def add_comment(self, comment_text: str, author: str = "Reviewer"):
        if not comment_text.strip():
            return
        comment_entry = {
            "id": f"c_{len(self.comments) + 1}_{int(datetime.now().timestamp())}",
            "author": author,
            "text": comment_text.strip(),
            "timestamp": datetime.now().isoformat()
        }
        self.comments.append(comment_entry)

    def set_ai_translation(self, ai_text: str, force_overwrite_human: bool = False):
        """Sets AI translation without overwriting human edits unless explicitly forced."""
        if self.has_human_edit() and not force_overwrite_human:
            # Preserve human edit, store AI text as ai_translation only
            self.ai_translation = ai_text
            self.revisions.append({
                "version": len(self.revisions) + 1,
                "text": ai_text,
                "type": "AI (New Output)",
                "editor": "AI System",
                "timestamp": datetime.now().isoformat()
            })
            return False
        else:
            self.ai_translation = ai_text
            self.translated_text = ai_text
            self.review_status = "AI Translated"
            return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "translated_text": self.translated_text,
            "is_heading": self.is_heading,
            "is_page_number": self.is_page_number,
            "bbox": self.bbox,
            "font_size": self.font_size,
            "status": self.status,
            "error_message": self.error_message,
            "ai_translation": self.ai_translation,
            "human_translation": self.human_translation,
            "review_status": self.review_status,
            "edited_by": self.edited_by,
            "edited_at": self.edited_at,
            "ai_recheck_status": self.ai_recheck_status,
            "ai_recheck_feedback": self.ai_recheck_feedback,
            "revisions": self.revisions,
            "comments": self.comments
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParagraphModel":
        bbox = tuple(data["bbox"]) if data.get("bbox") else None
        para = cls(
            id=data["id"],
            text=data["text"],
            translated_text=data.get("translated_text"),
            is_heading=data.get("is_heading", False),
            is_page_number=data.get("is_page_number", False),
            bbox=bbox,
            font_size=data.get("font_size", 12.0),
            status=data.get("status", "pending"),
            error_message=data.get("error_message"),
            ai_translation=data.get("ai_translation"),
            human_translation=data.get("human_translation"),
            review_status=data.get("review_status", "Needs Review"),
            edited_by=data.get("edited_by"),
            edited_at=data.get("edited_at"),
            ai_recheck_status=data.get("ai_recheck_status"),
            ai_recheck_feedback=data.get("ai_recheck_feedback"),
            revisions=data.get("revisions", []),
            comments=data.get("comments", [])
        )
        return para
