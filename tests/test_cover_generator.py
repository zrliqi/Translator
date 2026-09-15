import unittest
import tempfile
from pathlib import Path
from app.book import BookModel, CoverStatus
from app.cover import CoverGenerator

class TestCoverGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)
        self.generator = CoverGenerator()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_cover(self):
        book = BookModel(
            title="The Gift of the Magi",
            author="O. Henry",
            source_pdf_path="gift.pdf",
            translator="John Doe"
        )
        png_path, pdf_path = self.generator.generate_cover(book, output_dir=self.output_dir)

        self.assertTrue(png_path.exists())
        self.assertTrue(pdf_path.exists())
        self.assertEqual(book.cover_status, CoverStatus.GENERATED)
        self.assertEqual(book.cover_image_path, str(png_path))

    def test_exact_metadata_integrity(self):
        book = BookModel(
            title="1984",
            author="George Orwell",
            source_pdf_path="1984.pdf",
            translator="Jane Smith"
        )
        png_path, pdf_path = self.generator.generate_cover(book, output_dir=self.output_dir)

        # Inspect generated cover PDF to ensure text metadata elements are present
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
        page = doc[0]
        text = page.get_text()

        self.assertIn("1984", text)
        self.assertIn("George Orwell", text)
        self.assertIn("Jane Smith", text)
        doc.close()

if __name__ == '__main__':
    unittest.main()
