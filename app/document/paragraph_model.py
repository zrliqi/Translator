from dataclasses import dataclass, field
from typing import List, Optional, Tuple

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
