import unittest
from pathlib import Path
from app.pdf.text_extractor import TextExtractor
from app.processing.worker import TranslationWorker
from app.pdf.pdf_builder import PDFBuilder

class TestPageSelectionPipeline(unittest.TestCase):
    def setUp(self):
        self.sample_pdf = Path("test_page_flow.pdf")

    def test_worker_selected_pages_filtering(self):
        extractor = TextExtractor(extract_images=False)
        doc_model = extractor.extract_document(self.sample_pdf)
        total_orig_pages = doc_model.total_pages

        selected_pages = [2, 3] if total_orig_pages >= 3 else [1]
        worker = TranslationWorker(
            input_path=self.sample_pdf,
            provider="mock",
            model_name="mock-translator",
            selected_pages=selected_pages
        )

        selected_set = set(selected_pages)
        filtered_pages = [p for p in doc_model.pages if p.page_num in selected_set]
        self.assertEqual(len(filtered_pages), len(selected_pages))
        for p in filtered_pages:
            self.assertIn(p.page_num, selected_pages)

    def test_output_pdf_page_count_with_selected_pages(self):
        extractor = TextExtractor(extract_images=False)
        doc_model = extractor.extract_document(self.sample_pdf)
        if doc_model.total_pages > 1:
            doc_model.pages = [p for p in doc_model.pages if p.page_num in [2]]
            doc_model.total_pages = len(doc_model.pages)

        builder = PDFBuilder()
        out_pdf = builder.build_pdf(doc_model, keep_page_breaks=True)
        self.assertTrue(out_pdf.exists())

        import pymupdf
        res_doc = pymupdf.open(str(out_pdf))
        self.assertEqual(len(res_doc), len(doc_model.pages))
        res_doc.close()

if __name__ == "__main__":
    unittest.main()
