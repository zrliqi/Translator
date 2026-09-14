from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Any

@dataclass
class BlockModel:
    id: str
    bbox: Tuple[float, float, float, float]
    text: str
    block_type: str = "text"  # "text", "heading", "page_number", "image"
    font_size: float = 12.0
    font_name: str = ""
    lines: List[dict] = field(default_factory=list)
    image_bytes: Optional[bytes] = None
    image_ext: str = "png"
    image_info: Optional[dict] = None
