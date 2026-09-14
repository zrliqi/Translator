import unittest
from pathlib import Path
from app.pdf.analyzer import PDFAnalyzer
from app.pdf.text_extractor import TextExtractor
from app.pdf.page_parser import PageParser
from app.pdf.layout_analyzer import LayoutAnalyzer
from app.pdf.pdf_builder import PDFBuilder
from app.fonts.font_manager import FontManager
from app.translation.translation_cache import TranslationCache
from app.translation.translation_validator import TranslationValidator
from app.translation.openai_translator import MockTranslator
from app.processing.pipeline import JobManager, JobState
from app.document.document_model import DocumentModel
from app.document.page_model import PageModel
from app.document.block_model import BlockModel
from app.document.paragraph_model import ParagraphModel

class TestPDFTranslatorSuite(unittest.TestCase):
    def setUp(self):
        self.sample_pdf = Path("test_bengali.pdf")

    def test_font_manager(self):
        fm = FontManager.get_instance()
        self.assertTrue(fm.is_font_available("Noto Sans Bengali"))
        self.assertTrue(fm.is_font_available("Noto Serif Bengali"))

    def test_pdf_analyzer(self):
        analyzer = PDFAnalyzer()
        res = analyzer.analyze(self.sample_pdf)
        self.assertEqual(res.total_pages, 1)
        self.assertFalse(res.is_scanned)

    def test_text_extractor(self):
        extractor = TextExtractor()
        doc_model = extractor.extract_document(self.sample_pdf)
        self.assertEqual(doc_model.total_pages, 1)
        self.assertGreater(len(doc_model.pages[0].blocks), 0)

    def test_layout_analyzer_and_parser(self):
        is_num = LayoutAnalyzer.is_page_number("104", (250, 780, 270, 795), 842)
        self.assertTrue(is_num)

        is_hd = LayoutAnalyzer.is_heading("The Gift of the Magi", 18.0, 12.0, True)
        self.assertTrue(is_hd)

        page = PageModel(
            page_num=1, width=595, height=842,
            blocks=[
                BlockModel(id='b0', bbox=(250, 780, 270, 795), text='104', font_size=10.0),
                BlockModel(id='b1', bbox=(150, 100, 450, 130), text='The Gift of the Magi', font_size=20.0),
                BlockModel(id='b2', bbox=(50, 150, 545, 200), text='One dollar and\neighty-seven cents.', font_size=12.0, lines=[
                    {'text': 'One dollar and'},
                    {'text': 'eighty-seven cents.'}
                ])
            ]
        )
        parser = PageParser()
        paras = parser.parse_page(page)
        self.assertEqual(len(paras), 3)
        self.assertTrue(paras[0].is_page_number)
        self.assertTrue(paras[1].is_heading)
        self.assertEqual(paras[2].text, "One dollar and eighty-seven cents.")

    def test_translation_cache_and_validator(self):
        cache = TranslationCache()
        cache.put("Test text", "পরীক্ষা পাঠ্য", model_name="test_model")
        self.assertEqual(cache.get("Test text", model_name="test_model"), "পরীক্ষা পাঠ্য")

        v_pass, _ = TranslationValidator.validate("Hello", "হ্যালো")
        self.assertTrue(v_pass)

        v_fail, _ = TranslationValidator.validate("Hello", "Hello")
        self.assertFalse(v_fail)

    def test_mock_translator(self):
        translator = MockTranslator()
        para = ParagraphModel(id='p1', text='The Gift of the Magi')
        res = translator.translate_batch([para])
        self.assertEqual(res[0], "দ্য গিফট অব দ্য ম্যাজাই")

    def test_job_resume(self):
        jm = JobManager()
        job = JobState(
            job_id="job_unittest",
            source_pdf_path="test.pdf",
            source_pdf_hash="abc",
            total_pages=5,
            completed_blocks=2,
            translated_map={"p0": "অনুবাদ"}
        )
        jm.save_job(job)
        loaded = jm.load_job("job_unittest")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.completed_blocks, 2)
        self.assertEqual(loaded.translated_map["p0"], "অনুবাদ")

    def test_pdf_builder(self):
        doc_model = DocumentModel(
            file_path=Path("sample.pdf"),
            file_name="sample.pdf",
            file_size_bytes=1000,
            total_pages=1,
            pages=[
                PageModel(
                    page_num=1, width=595, height=842,
                    paragraphs=[
                        ParagraphModel(id='p0', text='Heading', translated_text='শিরোনাম', is_heading=True),
                        ParagraphModel(id='p1', text='Body', translated_text='বাংলা অনুবাদ্।', is_heading=False)
                    ]
                )
            ]
        )
        builder = PDFBuilder()
        out_pdf = builder.build_pdf(doc_model, output_path=Path("output/test_unit_bangla.pdf"))
        self.assertTrue(out_pdf.exists())

if __name__ == "__main__":
    unittest.main()
