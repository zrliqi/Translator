import unittest
import tempfile
from pathlib import Path
import pymupdf

from app.book import BookModel, BookStatus, CoverStatus
from app.cover import CoverGenerator
from app.publishing import BookPublisher

class TestBookPublisher(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

        # Create dummy source PDF
        self.source_pdf = self.output_dir / "test_source.pdf"
        doc = pymupdf.open()
        doc.new_page()
        doc.save(str(self.source_pdf))
        doc.close()

        # Create dummy content PDF
        self.content_pdf = self.output_dir / "test_content.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Bangla Content")
        doc.save(str(self.content_pdf))
        doc.close()

        self.publisher = BookPublisher()
        self.cover_generator = CoverGenerator()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_validation_fails_when_translator_or_cover_missing(self):
        book = BookModel(
            title="Test Book",
            author="Test Author",
            source_pdf_path=str(self.source_pdf),
            translator="" # Missing translator!
        )
        is_valid, errors = self.publisher.validate_for_publishing(book)
        self.assertFalse(is_valid)
        self.assertTrue(any("translator" in err.lower() for err in errors))

    def test_successful_book_publishing(self):
        book = BookModel(
            title="The Gift of the Magi",
            author="O. Henry",
            source_pdf_path=str(self.source_pdf),
            translator="John Doe"
        )

        # Generate cover
        png_cover, pdf_cover = self.cover_generator.generate_cover(book, output_dir=self.output_dir)
        book.cover_status = CoverStatus.APPROVED

        # Publish book
        published_path = self.publisher.publish_book(
            book=book,
            cover_pdf_path=pdf_cover,
            translated_content_pdf_path=self.content_pdf,
            output_dir=self.output_dir
        )

        self.assertTrue(published_path.exists())
        self.assertEqual(book.overall_status, BookStatus.PUBLISHED)
        self.assertEqual(book.published_pdf_path, str(published_path))

        # Check total pages of published PDF (1 cover + 1 content page = 2 pages)
        pub_doc = pymupdf.open(str(published_path))
        self.assertEqual(len(pub_doc), 2)
        pub_doc.close()

if __name__ == '__main__':
    unittest.main()
