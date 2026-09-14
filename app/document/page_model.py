from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from app.document.block_model import BlockModel
from app.document.paragraph_model import ParagraphModel

@dataclass
class PageModel:
    page_num: int  # 1-indexed
    width: float
    height: float
    is_scanned: bool = False
    needs_ocr: bool = False
    has_images: bool = False
    blocks: List[BlockModel] = field(default_factory=list)
    paragraphs: List[ParagraphModel] = field(default_factory=list)
    extracted_text: str = ""
    text_density: float = 0.0
