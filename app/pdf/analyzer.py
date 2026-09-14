import pymupdf
from pathlib import Path
from dataclasses import dataclass
from app.utils.logging import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

@dataclass
class PageAnalysis:
    page_num: int
    width: float
    height: float
    char_count: int
    word_count: int
    text_density: float
    has_images: bool
    is_scanned: bool

@dataclass
class PDFAnalysisResult:
    file_path: Path
    file_size_bytes: int
    total_pages: int
    is_scanned: bool
    text_pages_count: int
    scanned_pages_count: int
    page_analyses: list[PageAnalysis]

class PDFAnalyzer:
    def __init__(self, scanned_threshold: float = None):
        self.scanned_threshold = scanned_threshold if scanned_threshold is not None else settings.scanned_text_density_threshold

    def analyze(self, pdf_path: Path) -> PDFAnalysisResult:
        doc = pymupdf.open(str(pdf_path))
        file_size = pdf_path.stat().st_size
        total_pages = len(doc)

        page_analyses = []
        scanned_count = 0
        text_count = 0

        for idx, page in enumerate(doc):
            rect = page.rect
            width, height = rect.width, rect.height
            area = width * height
            text = page.get_text("text") or ""
            char_count = len(text.strip())
            word_count = len(text.split())
            text_density = char_count / area if area > 0 else 0.0

            image_list = page.get_images()
            has_images = len(image_list) > 0

            # Page is scanned if text density is low and it contains images or has practically no text
            is_scanned = (text_density < self.scanned_threshold and (has_images or char_count < 20))

            if is_scanned:
                scanned_count += 1
            else:
                text_count += 1

            page_analyses.append(PageAnalysis(
                page_num=idx + 1,
                width=width,
                height=height,
                char_count=char_count,
                word_count=word_count,
                text_density=text_density,
                has_images=has_images,
                is_scanned=is_scanned
            ))

        doc.close()
        is_overall_scanned = scanned_count > text_count

        return PDFAnalysisResult(
            file_path=pdf_path,
            file_size_bytes=file_size,
            total_pages=total_pages,
            is_scanned=is_overall_scanned,
            text_pages_count=text_count,
            scanned_pages_count=scanned_count,
            page_analyses=page_analyses
        )
