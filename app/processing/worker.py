import hashlib
from pathlib import Path
from typing import Optional, Callable
from PySide6.QtCore import QThread, Signal
from app.document.document_model import DocumentModel
from app.pdf.analyzer import PDFAnalyzer
from app.pdf.text_extractor import TextExtractor
from app.pdf.page_parser import PageParser
from app.pdf.pdf_builder import PDFBuilder
from app.ocr.ocr_engine import TesseractOCREngine
from app.translation.openai_translator import OpenAITranslator, MockTranslator
from app.translation.translation_cache import TranslationCache
from app.translation.translation_validator import TranslationValidator
from app.processing.pipeline import JobManager, JobState
from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

class TranslationWorker(QThread):
    progress_updated = Signal(int, int, str)  # current, total, status_message
    stats_updated = Signal(int, int, int, int) # pages_done, total_pages, chunks_done, errors
    job_finished = Signal(str, str)            # output_path, report_summary
    job_failed = Signal(str)

    def __init__(
        self,
        input_path: Path,
        model_name: str = "gpt-4o-mini",
        api_key: str = "",
        font_name: str = "Noto Sans Bengali",
        page_limit: int = 0,
        preserve_headings: bool = True,
        preserve_paragraphs: bool = True,
        preserve_page_numbers: bool = True,
        preserve_images: bool = True,
        preserve_structure: bool = True,
        use_ocr: bool = True,
        keep_page_breaks: bool = False,
        parent=None
    ):
        super().__init__(parent)
        self.input_path = input_path
        self.model_name = model_name
        self.api_key = api_key
        self.font_name = font_name
        self.page_limit = page_limit
        self.preserve_headings = preserve_headings
        self.preserve_paragraphs = preserve_paragraphs
        self.preserve_page_numbers = preserve_page_numbers
        self.preserve_images = preserve_images
        self.preserve_structure = preserve_structure
        self.use_ocr = use_ocr
        self.keep_page_breaks = keep_page_breaks

        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self.progress_updated.emit(5, 100, "Analyzing PDF structure...")
            analyzer = PDFAnalyzer()
            analysis_res = analyzer.analyze(self.input_path)

            if self._is_cancelled:
                self.job_failed.emit("Job cancelled by user.")
                return

            self.progress_updated.emit(15, 100, "Extracting text and blocks...")
            extractor = TextExtractor(extract_images=self.preserve_images)
            doc_model = extractor.extract_document(self.input_path)

            if self.page_limit > 0:
                doc_model.pages = doc_model.pages[:self.page_limit]
                doc_model.total_pages = len(doc_model.pages)

            parser = PageParser(
                preserve_headings=self.preserve_headings,
                preserve_page_numbers=self.preserve_page_numbers
            )

            # OCR fallback setup
            ocr_engine = TesseractOCREngine() if self.use_ocr else None

            total_pages = len(doc_model.pages)
            for idx, page in enumerate(doc_model.pages):
                if self._is_cancelled:
                    self.job_failed.emit("Job cancelled by user.")
                    return

                # If page is scanned and OCR requested
                if page.needs_ocr or page.is_scanned:
                    if ocr_engine and ocr_engine.is_available():
                        try:
                            # Render page image for OCR
                            import pymupdf
                            doc = pymupdf.open(str(self.input_path))
                            p = doc[idx]
                            pix = p.get_pixmap()
                            img_bytes = pix.tobytes("png")
                            ocr_text = ocr_engine.extract_text_from_image(img_bytes, lang="eng")
                            doc.close()

                            if ocr_text.strip():
                                page.extracted_text = ocr_text
                                # Create synthetic text block for OCR extracted text
                                from app.document.block_model import BlockModel
                                page.blocks = [
                                    BlockModel(
                                        id=f"p{page.page_num}_ocr_b0",
                                        bbox=(50, 50, page.width - 50, page.height - 50),
                                        text=ocr_text,
                                        block_type="text",
                                        font_size=12.0
                                    )
                                ]
                        except Exception as e:
                            logger.error(f"OCR extraction failed on page {page.page_num}: {e}")
                parser.parse_page(page)

            translatable_paras = doc_model.get_translatable_paragraphs()
            total_chunks = len(translatable_paras)

            if self.model_name == "mock-translator":
                translator = MockTranslator()
            else:
                translator = OpenAITranslator(api_key=self.api_key, model=self.model_name)

            cache = TranslationCache()

            # Generate unique hash for file resume
            file_hash = hashlib.sha256(self.input_path.read_bytes()[:10000]).hexdigest()
            job_id = f"job_{file_hash[:12]}"
            job_manager = JobManager()

            existing_job = job_manager.load_job(job_id)
            translated_map = existing_job.translated_map if existing_job else {}

            cached_count = 0
            api_count = 0
            failed_count = 0

            # Process paragraphs in batches
            batch_size = settings.batch_size
            completed_chunks = 0

            for i in range(0, total_chunks, batch_size):
                if self._is_cancelled:
                    job = JobState(
                        job_id=job_id,
                        source_pdf_path=str(self.input_path),
                        source_pdf_hash=file_hash,
                        total_pages=total_pages,
                        completed_blocks=completed_chunks,
                        status="PAUSED",
                        translated_map=translated_map
                    )
                    job_manager.save_job(job)
                    self.job_failed.emit("Translation paused/cancelled. Progress saved for resume.")
                    return

                batch = translatable_paras[i:i + batch_size]
                untranslated_batch = []

                for p in batch:
                    # Check in-job map first
                    if p.id in translated_map:
                        p.translated_text = translated_map[p.id]
                        p.status = "translated"
                        cached_count += 1
                    else:
                        # Check SQLite cache
                        cached_text = cache.get(p.text, model_name=self.model_name)
                        if cached_text:
                            p.translated_text = cached_text
                            p.status = "translated"
                            translated_map[p.id] = cached_text
                            cached_count += 1
                        else:
                            untranslated_batch.append(p)

                if untranslated_batch:
                    try:
                        results = translator.translate_batch(untranslated_batch)
                        for p, res_text in zip(untranslated_batch, results):
                            valid, msg = TranslationValidator.validate(p.text, res_text)
                            if valid:
                                p.translated_text = res_text
                                p.status = "translated"
                                translated_map[p.id] = res_text
                                cache.put(p.text, res_text, model_name=self.model_name)
                                api_count += 1
                            else:
                                p.status = "failed"
                                p.error_message = msg
                                p.translated_text = f"[Translation Error: {p.text}]"
                                failed_count += 1
                    except Exception as e:
                        logger.error(f"Batch translation error: {e}")
                        for p in untranslated_batch:
                            p.status = "failed"
                            p.error_message = str(e)
                            p.translated_text = f"[Translation Error: {p.text}]"
                            failed_count += 1

                completed_chunks += len(batch)
                prog_pct = 20 + int((completed_chunks / max(1, total_chunks)) * 60)
                curr_page = min(total_pages, max(1, int((completed_chunks / max(1, total_chunks)) * total_pages)))

                self.progress_updated.emit(prog_pct, 100, f"Translating paragraph {completed_chunks} / {total_chunks}")
                self.stats_updated.emit(curr_page, total_pages, completed_chunks, failed_count)

            # Building final PDF
            self.progress_updated.emit(85, 100, "Building Bangla PDF...")
            builder = PDFBuilder(font_name=self.font_name)
            output_pdf_path = builder.build_pdf(
                doc_model,
                preserve_images=self.preserve_images,
                preserve_page_numbers=self.preserve_page_numbers,
                keep_page_breaks=self.keep_page_breaks
            )

            # Save finished job state
            job = JobState(
                job_id=job_id,
                source_pdf_path=str(self.input_path),
                source_pdf_hash=file_hash,
                total_pages=total_pages,
                completed_pages=total_pages,
                total_blocks=total_chunks,
                completed_blocks=completed_chunks,
                failed_blocks=failed_count,
                status="COMPLETED",
                translated_map=translated_map
            )
            job_manager.save_job(job)

            self.progress_updated.emit(100, 100, "Translation completed successfully!")

            report_summary = (
                f"Translation Completed Successfully!\n\n"
                f"Source File:            {self.input_path.name}\n"
                f"Total Pages:            {total_pages}\n"
                f"Total Paragraph Chunks: {total_chunks}\n"
                f"Successful Chunks:      {completed_chunks - failed_count}\n"
                f"Failed Chunks:          {failed_count}\n"
                f"Cached Translations:    {cached_count}\n"
                f"API Translations:       {api_count}\n\n"
                f"Output PDF:\n{output_pdf_path}"
            )

            self.job_finished.emit(str(output_pdf_path), report_summary)

        except Exception as e:
            logger.error(f"Pipeline execution error: {e}", exc_info=True)
            self.job_failed.emit(str(e))
