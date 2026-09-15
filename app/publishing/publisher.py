import pymupdf
from pathlib import Path
from typing import Tuple, List, Optional
from app.book.book_model import BookModel, BookStatus, CoverStatus
from app.utils.paths import get_output_dir
from app.utils.logging import get_logger

logger = get_logger(__name__)

class BookPublisher:
    @staticmethod
    def validate_for_publishing(book: BookModel, cover_pdf_path: Optional[Path] = None, translated_content_pdf_path: Optional[Path] = None) -> Tuple[bool, List[str]]:
        errors = []

        if not book.title.strip():
            errors.append("Book title is missing.")
        if not book.author.strip():
            errors.append("Author / Writer name is missing.")
        if not book.translator.strip():
            errors.append("Assigned translator is required before publishing.")

        source_path = Path(book.source_pdf_path) if book.source_pdf_path else None
        if not source_path or not source_path.exists():
            errors.append(f"Source PDF file does not exist: {book.source_pdf_path}")

        if book.cover_status not in (CoverStatus.GENERATED, CoverStatus.HUMAN_SELECTED, CoverStatus.APPROVED):
            errors.append("An approved book front cover is required before publishing.")

        if cover_pdf_path and not cover_pdf_path.exists():
            errors.append(f"Cover PDF file not found: {cover_pdf_path}")

        if translated_content_pdf_path and not translated_content_pdf_path.exists():
            errors.append(f"Translated content PDF file not found: {translated_content_pdf_path}")

        return (len(errors) == 0, errors)

    def publish_book(
        self,
        book: BookModel,
        cover_pdf_path: Path,
        translated_content_pdf_path: Path,
        output_dir: Optional[Path] = None
    ) -> Path:
        is_valid, errors = self.validate_for_publishing(book, cover_pdf_path, translated_content_pdf_path)
        if not is_valid:
            err_msg = "; ".join(errors)
            logger.error(f"Publishing validation failed for '{book.title}': {err_msg}")
            raise ValueError(f"Book is not ready for publishing: {err_msg}")

        target_dir = output_dir or get_output_dir()
        target_dir.mkdir(parents=True, exist_ok=True)

        clean_title = "".join(c for c in book.title if c.isalnum() or c in (" ", "_", "-")).strip()
        out_pdf_path = target_dir / f"{clean_title}_Published.pdf"
        counter = 2
        while out_pdf_path.exists():
            out_pdf_path = target_dir / f"{clean_title}_Published_{counter}.pdf"
            counter += 1

        # Combine Front Cover PDF + Translated Content PDF into final published book
        final_doc = pymupdf.open()

        # 1. Insert Front Cover Page(s)
        cover_doc = pymupdf.open(str(cover_pdf_path))
        final_doc.insert_pdf(cover_doc)
        cover_doc.close()

        # 2. Insert Translated Content Pages
        content_doc = pymupdf.open(str(translated_content_pdf_path))
        final_doc.insert_pdf(content_doc)
        content_doc.close()

        final_doc.save(str(out_pdf_path))
        final_doc.close()

        book.published_pdf_path = str(out_pdf_path)
        book.overall_status = BookStatus.PUBLISHED
        book.update_timestamp()

        logger.info(f"Published final book for '{book.title}' at: {out_pdf_path}")
        return out_pdf_path
