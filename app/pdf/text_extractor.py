import pymupdf
from pathlib import Path
from typing import List, Tuple
from app.document.block_model import BlockModel
from app.document.page_model import PageModel
from app.document.document_model import DocumentModel
from app.utils.logging import get_logger

logger = get_logger(__name__)

class TextExtractor:
    def __init__(self, extract_images: bool = True):
        self.extract_images = extract_images

    def extract_document(self, pdf_path: Path) -> DocumentModel:
        doc = pymupdf.open(str(pdf_path))
        file_size = pdf_path.stat().st_size
        pages: List[PageModel] = []

        for idx, page in enumerate(doc):
            page_num = idx + 1
            rect = page.rect
            text_layout = page.get_text("dict")
            raw_text = page.get_text("text") or ""

            blocks: List[BlockModel] = []
            block_idx = 0

            for b in text_layout.get("blocks", []):
                block_type_num = b.get("type", 0)
                bbox = tuple(b.get("bbox", (0, 0, 0, 0)))
                block_id = f"p{page_num}_b{block_idx}"

                if block_type_num == 0:  # Text block
                    lines_data = []
                    full_block_text_lines = []
                    max_font_size = 12.0
                    dominant_font = ""

                    for line in b.get("lines", []):
                        line_text = ""
                        spans_data = []
                        for span in line.get("spans", []):
                            span_text = span.get("text", "")
                            font_size = span.get("size", 12.0)
                            font_name = span.get("font", "")
                            if font_size > max_font_size:
                                max_font_size = font_size
                            if font_name:
                                dominant_font = font_name

                            spans_data.append({
                                "text": span_text,
                                "font_size": font_size,
                                "font_name": font_name,
                                "bbox": tuple(span.get("bbox", (0, 0, 0, 0)))
                            })
                            line_text += span_text

                        lines_data.append({
                            "bbox": tuple(line.get("bbox", (0, 0, 0, 0))),
                            "spans": spans_data,
                            "text": line_text
                        })
                        full_block_text_lines.append(line_text)

                    block_text = "\n".join(full_block_text_lines).strip()
                    if block_text:
                        blocks.append(BlockModel(
                            id=block_id,
                            bbox=bbox,
                            text=block_text,
                            block_type="text",
                            font_size=max_font_size,
                            font_name=dominant_font,
                            lines=lines_data
                        ))
                        block_idx += 1

                elif block_type_num == 1 and self.extract_images:  # Image block
                    img_bytes = b.get("image")
                    img_ext = b.get("ext", "png")
                    blocks.append(BlockModel(
                        id=block_id,
                        bbox=bbox,
                        text="",
                        block_type="image",
                        image_bytes=img_bytes,
                        image_ext=img_ext,
                        image_info=b
                    ))
                    block_idx += 1

            area = rect.width * rect.height
            char_count = len(raw_text.strip())
            density = char_count / area if area > 0 else 0.0

            pages.append(PageModel(
                page_num=page_num,
                width=rect.width,
                height=rect.height,
                blocks=blocks,
                extracted_text=raw_text,
                text_density=density
            ))

        doc.close()
        return DocumentModel(
            file_path=pdf_path,
            file_name=pdf_path.name,
            file_size_bytes=file_size,
            total_pages=len(pages),
            pages=pages
        )
