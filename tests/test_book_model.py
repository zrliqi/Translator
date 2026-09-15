import unittest
import tempfile
from pathlib import Path
from app.book import BookModel, BookStatus, CoverStatus, BookManager

class TestBookModel(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_books.db"
        self.manager = BookManager(db_path=self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_create_and_save_book(self):
        book = BookModel(
            title="The Gift of the Magi",
            author="O. Henry",
            source_pdf_path="/path/to/magi.pdf",
            translator="John Doe"
        )
        saved_book = self.manager.save_book(book)
        self.assertEqual(saved_book.title, "The Gift of the Magi")
        self.assertEqual(saved_book.author, "O. Henry")
        self.assertEqual(saved_book.translator, "John Doe")

        loaded_book = self.manager.get_book(book.book_id)
        self.assertIsNotNone(loaded_book)
        self.assertEqual(loaded_book.title, "The Gift of the Magi")
        self.assertEqual(loaded_book.translator, "John Doe")
        self.assertEqual(loaded_book.translation_status, BookStatus.DRAFT)

    def test_assign_translator(self):
        book = BookModel(
            title="1984",
            author="George Orwell",
            source_pdf_path="/path/to/1984.pdf"
        )
        self.manager.save_book(book)

        updated_book = self.manager.update_translator(book.book_id, "Jane Smith")
        self.assertIsNotNone(updated_book)
        self.assertEqual(updated_book.translator, "Jane Smith")

        loaded = self.manager.get_book(book.book_id)
        self.assertEqual(loaded.translator, "Jane Smith")

    def test_list_and_delete_books(self):
        book1 = BookModel(title="Book 1", author="Author 1", source_pdf_path="1.pdf")
        book2 = BookModel(title="Book 2", author="Author 2", source_pdf_path="2.pdf")
        self.manager.save_book(book1)
        self.manager.save_book(book2)

        books = self.manager.list_books()
        self.assertEqual(len(books), 2)

        deleted = self.manager.delete_book(book1.book_id)
        self.assertTrue(deleted)

        books_after = self.manager.list_books()
        self.assertEqual(len(books_after), 1)
        self.assertEqual(books_after[0].title, "Book 2")

if __name__ == '__main__':
    unittest.main()
