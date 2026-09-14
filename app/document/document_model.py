from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
from app.document.page_model import PageModel
from app.document.paragraph_model import ParagraphModel

@dataclass
class DocumentModel:
    file_path: Path
    file_name: str
    file_size_bytes: int
    total_pages: int
    is_scanned_document: bool = False
    pages: List[PageModel] = field(default_factory=list)

    def get_all_paragraphs(self) -> List[ParagraphModel]:
        paragraphs = []
        for p in self.pages:
            paragraphs.extend(p.paragraphs)
        return paragraphs

    def get_translatable_paragraphs(self) -> List[ParagraphModel]:
        paragraphs = []
        for p in self.pages:
            for para in p.paragraphs:
                if not para.is_page_number and para.text.strip():
                    paragraphs.append(para)
        return paragraphs
