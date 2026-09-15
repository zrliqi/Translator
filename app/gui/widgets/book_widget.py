import os
from pathlib import Path
from typing import Optional, List, Callable
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QFileDialog, QDialog, QFormLayout, QSplitter, QProgressBar, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

from app.book.book_model import BookModel, BookStatus, CoverStatus
from app.book.book_manager import BookManager
from app.cover.cover_generator import CoverGenerator
from app.publishing.publisher import BookPublisher
from app.utils.logging import get_logger
from app.utils.paths import get_output_dir

logger = get_logger(__name__)

class BookDialog(QDialog):
    def __init__(self, book: Optional[BookModel] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Book Metadata" if book else "Create New Book")
        self.resize(500, 350)
        self.book = book

        layout = QFormLayout(self)

        self.title_edit = QLineEdit(book.title if book else "")
        self.author_edit = QLineEdit(book.author if book else "")
        self.translator_edit = QLineEdit(book.translator if book else "")

        pdf_layout = QHBoxLayout()
        self.pdf_edit = QLineEdit(book.source_pdf_path if book else "")
        self.pdf_browse_btn = QPushButton("Browse...")
        self.pdf_browse_btn.clicked.connect(self._on_browse_pdf)
        pdf_layout.addWidget(self.pdf_edit)
        pdf_layout.addWidget(self.pdf_browse_btn)

        layout.addRow("Book Title *:", self.title_edit)
        layout.addRow("Original Author *:", self.author_edit)
        layout.addRow("Assigned Translator *:", self.translator_edit)
        layout.addRow("Source PDF *:", pdf_layout)

        btn_box = QHBoxLayout()
        self.save_btn = QPushButton("Save Book")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(self.save_btn)
        btn_box.addWidget(self.cancel_btn)

        layout.addRow(btn_box)

    def _on_browse_pdf(self):
        fpath, _ = QFileDialog.getOpenFileName(self, "Select Source English PDF", "", "PDF Files (*.pdf)")
        if fpath:
            self.pdf_edit.setText(fpath)
            if not self.title_edit.text().strip():
                stem = Path(fpath).stem.replace("_", " ").title()
                self.title_edit.setText(stem)

    def get_data(self) -> dict:
        return {
            "title": self.title_edit.text().strip(),
            "author": self.author_edit.text().strip(),
            "translator": self.translator_edit.text().strip(),
            "source_pdf_path": self.pdf_edit.text().strip()
        }

class BookWidget(QWidget):
    open_translation_job = Signal(BookModel)
    open_human_review = Signal(BookModel)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.book_manager = BookManager()
        self.cover_generator = CoverGenerator()
        self.publisher = BookPublisher()
        self.selected_book: Optional[BookModel] = None

        self._init_ui()
        self.refresh_book_list()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)

        splitter = QSplitter(Qt.Horizontal)

        # Left: Book Library List & Actions
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        left_layout.addWidget(QLabel("<h2>Book Library</h2>"))

        lib_btn_layout = QHBoxLayout()
        self.add_book_btn = QPushButton("+ New Book")
        self.add_book_btn.clicked.connect(self._on_add_book)

        self.edit_book_btn = QPushButton("Edit Metadata")
        self.edit_book_btn.clicked.connect(self._on_edit_book)
        self.edit_book_btn.setEnabled(False)

        self.delete_book_btn = QPushButton("Delete Book")
        self.delete_book_btn.clicked.connect(self._on_delete_book)
        self.delete_book_btn.setEnabled(False)

        lib_btn_layout.addWidget(self.add_book_btn)
        lib_btn_layout.addWidget(self.edit_book_btn)
        lib_btn_layout.addWidget(self.delete_book_btn)
        left_layout.addLayout(lib_btn_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Title", "Author", "Translator", "Cover", "Overall Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        left_layout.addWidget(self.table)

        splitter.addWidget(left_widget)

        # Right: Active Book Details & Dashboard
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 0, 0, 0)

        right_layout.addWidget(QLabel("<h2>Book Workflow Dashboard</h2>"))

        self.details_group = QGroupBox("BOOK DETAILS & WORKFLOW")
        details_form = QFormLayout(self.details_group)

        self.lbl_title = QLabel("-")
        self.lbl_author = QLabel("-")
        self.lbl_translator = QLabel("-")
        self.lbl_source_pdf = QLabel("-")
        self.lbl_trans_status = QLabel("-")
        self.lbl_review_status = QLabel("-")
        self.lbl_cover_status = QLabel("-")
        self.lbl_overall_status = QLabel("-")

        details_form.addRow("Book Title:", self.lbl_title)
        details_form.addRow("Author:", self.lbl_author)
        details_form.addRow("Translator:", self.lbl_translator)
        details_form.addRow("Source PDF:", self.lbl_source_pdf)
        details_form.addRow("Translation Status:", self.lbl_trans_status)
        details_form.addRow("Review Status:", self.lbl_review_status)
        details_form.addRow("Cover Status:", self.lbl_cover_status)
        details_form.addRow("Overall Status:", self.lbl_overall_status)

        right_layout.addWidget(self.details_group)

        # Workflow Actions Group
        action_group = QGroupBox("WORKFLOW ACTIONS")
        action_layout = QVBoxLayout(action_group)

        self.btn_translate = QPushButton("1. Start / Open Translation Job")
        self.btn_translate.clicked.connect(self._on_open_translation_job)
        self.btn_translate.setEnabled(False)

        self.btn_review = QPushButton("2. Open Side-by-Side Review")
        self.btn_review.clicked.connect(self._on_open_human_review)
        self.btn_review.setEnabled(False)

        self.btn_cover = QPushButton("3. Generate Front Cover")
        self.btn_cover.clicked.connect(self._on_generate_cover)
        self.btn_cover.setEnabled(False)

        self.btn_publish = QPushButton("4. Publish Final Book PDF")
        self.btn_publish.clicked.connect(self._on_publish_book)
        self.btn_publish.setEnabled(False)

        action_layout.addWidget(self.btn_translate)
        action_layout.addWidget(self.btn_review)
        action_layout.addWidget(self.btn_cover)
        action_layout.addWidget(self.btn_publish)

        right_layout.addWidget(action_group)

        # Cover Preview Widget
        cover_group = QGroupBox("FRONT COVER PREVIEW")
        cover_layout = QVBoxLayout(cover_group)
        self.cover_preview_lbl = QLabel("No cover generated yet.")
        self.cover_preview_lbl.setAlignment(Qt.AlignCenter)
        self.cover_preview_lbl.setStyleSheet("background-color: #2b2b2b; color: #aaaaaa; border: 1px dashed #666;")
        self.cover_preview_lbl.setFixedHeight(220)
        cover_layout.addWidget(self.cover_preview_lbl)

        right_layout.addWidget(cover_group)

        splitter.addWidget(right_widget)
        splitter.setSizes([550, 400])

        main_layout.addWidget(splitter)

    def refresh_book_list(self):
        books = self.book_manager.list_books()
        self.table.setRowCount(0)
        for b in books:
            row = self.table.rowCount()
            self.table.insertRow(row)

            title_item = QTableWidgetItem(b.title)
            title_item.setData(Qt.UserRole, b.book_id)

            self.table.setItem(row, 0, title_item)
            self.table.setItem(row, 1, QTableWidgetItem(b.author))
            self.table.setItem(row, 2, QTableWidgetItem(b.translator or "[Unassigned]"))
            self.table.setItem(row, 3, QTableWidgetItem(b.cover_status))
            self.table.setItem(row, 4, QTableWidgetItem(b.overall_status))

        if books:
            self.table.selectRow(0)
        else:
            self._clear_details()

    def _clear_details(self):
        self.selected_book = None
        self.lbl_title.setText("-")
        self.lbl_author.setText("-")
        self.lbl_translator.setText("-")
        self.lbl_source_pdf.setText("-")
        self.lbl_trans_status.setText("-")
        self.lbl_review_status.setText("-")
        self.lbl_cover_status.setText("-")
        self.lbl_overall_status.setText("-")
        self.cover_preview_lbl.setText("No cover generated yet.")
        self.cover_preview_lbl.setPixmap(QPixmap())

        self.btn_translate.setEnabled(False)
        self.btn_review.setEnabled(False)
        self.btn_cover.setEnabled(False)
        self.btn_publish.setEnabled(False)
        self.edit_book_btn.setEnabled(False)
        self.delete_book_btn.setEnabled(False)

    def _on_row_selected(self):
        selected = self.table.selectedItems()
        if not selected:
            self._clear_details()
            return
        row = self.table.currentRow()
        book_id_item = self.table.item(row, 0)
        if book_id_item:
            book_id = book_id_item.data(Qt.UserRole)
            self.selected_book = self.book_manager.get_book(book_id)
            if self.selected_book:
                self._update_details_view(self.selected_book)

    def _update_details_view(self, book: BookModel):
        self.lbl_title.setText(f"<b>{book.title}</b>")
        self.lbl_author.setText(book.author)
        self.lbl_translator.setText(book.translator or "<font color='red'>[Translator Required]</font>")
        self.lbl_source_pdf.setText(book.source_pdf_path)
        self.lbl_trans_status.setText(book.translation_status)
        self.lbl_review_status.setText(book.review_status)
        self.lbl_cover_status.setText(book.cover_status)
        self.lbl_overall_status.setText(f"<b>{book.overall_status}</b>")

        self.btn_translate.setEnabled(True)
        self.btn_review.setEnabled(True)
        self.btn_cover.setEnabled(True)
        self.btn_publish.setEnabled(True)
        self.edit_book_btn.setEnabled(True)
        self.delete_book_btn.setEnabled(True)

        # Update cover preview
        if book.cover_image_path and Path(book.cover_image_path).exists():
            pixmap = QPixmap(book.cover_image_path)
            self.cover_preview_lbl.setPixmap(pixmap.scaled(self.cover_preview_lbl.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.cover_preview_lbl.setText("No cover generated yet.\nClick '3. Generate Front Cover' to create.")
            self.cover_preview_lbl.setPixmap(QPixmap())

    def _on_add_book(self):
        dlg = BookDialog(parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data["title"] or not data["source_pdf_path"]:
                QMessageBox.warning(self, "Missing Fields", "Book Title and Source PDF are required.")
                return
            book = BookModel(
                title=data["title"],
                author=data["author"] or "Unknown Author",
                source_pdf_path=data["source_pdf_path"],
                translator=data["translator"]
            )
            self.book_manager.save_book(book)
            self.refresh_book_list()

    def _on_edit_book(self):
        if not self.selected_book:
            return
        dlg = BookDialog(book=self.selected_book, parent=self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            self.selected_book.title = data["title"]
            self.selected_book.author = data["author"]
            self.selected_book.translator = data["translator"]
            self.selected_book.source_pdf_path = data["source_pdf_path"]
            self.book_manager.save_book(self.selected_book)
            self.refresh_book_list()

    def _on_delete_book(self):
        if not self.selected_book:
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete book '{self.selected_book.title}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.book_manager.delete_book(self.selected_book.book_id)
            self.refresh_book_list()

    def _on_open_translation_job(self):
        if self.selected_book:
            self.open_translation_job.emit(self.selected_book)

    def _on_open_human_review(self):
        if self.selected_book:
            self.open_human_review.emit(self.selected_book)

    def _on_generate_cover(self):
        if not self.selected_book:
            return
        if not self.selected_book.translator.strip():
            QMessageBox.warning(self, "Translator Missing", "Please assign a translator to the book before generating cover.")
            return
        try:
            png_path, pdf_path = self.cover_generator.generate_cover(self.selected_book)
            self.selected_book.cover_status = CoverStatus.APPROVED
            self.book_manager.save_book(self.selected_book)
            self._update_details_view(self.selected_book)
            QMessageBox.information(self, "Cover Generated", f"Book front cover generated successfully!\nImage: {png_path.name}")
        except Exception as e:
            logger.error(f"Failed generating cover: {e}")
            QMessageBox.critical(self, "Cover Error", f"Failed to generate cover: {e}")

    def _on_publish_book(self):
        if not self.selected_book:
            return

        cover_stem = f"cover_{self.selected_book.book_id}"
        out_dir = get_output_dir()
        cover_pdf_path = out_dir / f"{cover_stem}.pdf"

        # Check if cover exists
        if not cover_pdf_path.exists():
            # Generate cover first automatically if missing
            if self.selected_book.translator.strip():
                png_path, cover_pdf_path = self.cover_generator.generate_cover(self.selected_book)
                self.selected_book.cover_status = CoverStatus.APPROVED
            else:
                QMessageBox.warning(self, "Missing Requirements", "An assigned translator and cover are required to publish.")
                return

        # Find translated PDF candidate
        stem = Path(self.selected_book.source_pdf_path).stem
        content_pdf_path = out_dir / f"{stem}_Bangla.pdf"

        if not content_pdf_path.exists():
            # Check for numbered outputs
            candidates = list(out_dir.glob(f"{stem}_Bangla*.pdf"))
            if candidates:
                content_pdf_path = candidates[0]
            else:
                QMessageBox.warning(self, "Translation Missing", f"Could not find translated PDF in output folder for '{stem}'. Please run translation first.")
                return

        try:
            pub_path = self.publisher.publish_book(
                book=self.selected_book,
                cover_pdf_path=cover_pdf_path,
                translated_content_pdf_path=content_pdf_path
            )
            self.book_manager.save_book(self.selected_book)
            self.refresh_book_list()
            QMessageBox.information(self, "Book Published!", f"Published Book PDF generated successfully!\nFile: {pub_path}")
        except Exception as e:
            logger.error(f"Publish error: {e}")
            QMessageBox.critical(self, "Publish Failed", str(e))
