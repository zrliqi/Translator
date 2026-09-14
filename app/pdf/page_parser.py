from typing import List
from app.document.page_model import PageModel
from app.document.block_model import BlockModel
from app.document.paragraph_model import ParagraphModel
from app.pdf.layout_analyzer import LayoutAnalyzer
from app.utils.logging import get_logger

logger = get_logger(__name__)

class PageParser:
    def __init__(self, preserve_headings: bool = True, preserve_page_numbers: bool = True):
        self.preserve_headings = preserve_headings
        self.preserve_page_numbers = preserve_page_numbers

    def parse_page(self, page: PageModel) -> List[ParagraphModel]:
        paragraphs: List[ParagraphModel] = []

        # Calculate average font size for text blocks on page
        text_font_sizes = [b.font_size for b in page.blocks if b.block_type == "text" and b.text.strip()]
        avg_font_size = sum(text_font_sizes) / len(text_font_sizes) if text_font_sizes else 12.0

        para_idx = 0

        for block in page.blocks:
            if block.block_type != "text" or not block.text.strip():
                continue

            text = block.text.strip()

            # Check page number
            is_page_num = LayoutAnalyzer.is_page_number(text, block.bbox, page.height)
            if is_page_num:
                para_id = f"p{page.page_num}_num_{para_idx}"
                paragraphs.append(ParagraphModel(
                    id=para_id,
                    text=text,
                    is_heading=False,
                    is_page_number=True,
                    bbox=block.bbox,
                    font_size=block.font_size,
                    status="skipped"
                ))
                para_idx += 1
                continue

            # Check heading
            is_centered = False
            if block.bbox:
                # Approximate centered alignment check
                block_center = (block.bbox[0] + block.bbox[2]) / 2.0
                page_center = page.width / 2.0
                if abs(block_center - page_center) < 40:
                    is_centered = True

            is_hd = LayoutAnalyzer.is_heading(text, block.font_size, avg_font_size, is_centered)

            # Reconstruct lines within the block
            reconstructed_text = self._reconstruct_block_lines(block)

            para_id = f"p{page.page_num}_para_{para_idx}"
            paragraphs.append(ParagraphModel(
                id=para_id,
                text=reconstructed_text,
                is_heading=is_hd,
                is_page_number=False,
                bbox=block.bbox,
                font_size=block.font_size,
                status="pending"
            ))
            para_idx += 1

        page.paragraphs = paragraphs
        return paragraphs

    def _reconstruct_block_lines(self, block: BlockModel) -> str:
        if not block.lines:
            return block.text

        lines_text = [l["text"].strip() for l in block.lines if l.get("text", "").strip()]
        if not lines_text:
            return block.text

        merged_paragraph = ""
        for i, line in enumerate(lines_text):
            if not merged_paragraph:
                merged_paragraph = line
            else:
                # If previous line ends with hyphen, remove hyphen and merge directly
                if merged_paragraph.endswith("-") and len(merged_paragraph) > 1 and merged_paragraph[-2].isalpha():
                    merged_paragraph = merged_paragraph[:-1] + line
                else:
                    merged_paragraph += " " + line

        return merged_paragraph
