import re
from typing import List, Tuple
from app.document.block_model import BlockModel
from app.document.paragraph_model import ParagraphModel
from app.utils.logging import get_logger

logger = get_logger(__name__)

class LayoutAnalyzer:
    @staticmethod
    def is_page_number(text: str, bbox: Tuple[float, float, float, float], page_height: float) -> bool:
        clean = text.strip()
        if not clean:
            return False

        # Numbers like "1", "Page 12", "- 5 -", "12 / 104"
        is_num_pattern = bool(re.match(r"^(\-?\s*\d+\s*\-?|Page\s+\d+|\d+\s*/\s*\d+)$", clean, re.IGNORECASE))

        # Position check: near top (< 70pt) or near bottom (> page_height - 70pt)
        top_y = bbox[1]
        is_margin_area = (top_y < 70 or top_y > page_height - 70)

        return is_num_pattern and is_margin_area

    @staticmethod
    def is_heading(text: str, font_size: float, page_avg_font_size: float, is_centered: bool = False) -> bool:
        clean = text.strip()
        if not clean:
            return False

        # Heading indicators: short text, larger font, title case/all caps, no trailing period (or digit like story number)
        is_short = len(clean) < 80
        is_larger_font = font_size >= page_avg_font_size + 1.5
        is_story_num = bool(re.match(r"^\d+$", clean))

        if is_story_num and is_short:
            return True

        if is_larger_font and is_short and not clean.endswith("."):
            return True

        if is_centered and is_short and not clean.endswith("."):
            return True

        return False
