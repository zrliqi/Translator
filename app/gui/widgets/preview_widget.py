from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QSplitter, QTextEdit, QFrame
)
from PySide6.QtCore import Qt
from typing import List
from app.document.paragraph_model import ParagraphModel

class SideBySidePreviewWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        splitter = QSplitter(Qt.Horizontal)

        # Left panel: Source English
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("<b>Source English Text</b>"))
        self.source_text_edit = QTextEdit()
        self.source_text_edit.setReadOnly(True)
        left_layout.addWidget(self.source_text_edit)

        # Right panel: Target Bangla
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("<b>Target Bangla Translation</b>"))
        self.target_text_edit = QTextEdit()
        self.target_text_edit.setReadOnly(True)
        right_layout.addWidget(self.target_text_edit)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 400])

        layout.addWidget(splitter)

        # Table view below for block-by-block selection
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Type", "Status", "English Preview"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        layout.addWidget(self.table)

        self.paragraphs: List[ParagraphModel] = []

    def load_paragraphs(self, paragraphs: List[ParagraphModel]):
        self.paragraphs = paragraphs
        self.table.setRowCount(0)

        for p in paragraphs:
            row = self.table.rowCount()
            self.table.insertRow(row)

            p_type = "Page Num" if p.is_page_number else ("Heading" if p.is_heading else "Paragraph")

            self.table.setItem(row, 0, QTableWidgetItem(p.id))
            self.table.setItem(row, 1, QTableWidgetItem(p_type))
            self.table.setItem(row, 2, QTableWidgetItem(p.status))

            preview_text = p.text[:80] + ("..." if len(p.text) > 80 else "")
            self.table.setItem(row, 3, QTableWidgetItem(preview_text))

        if paragraphs:
            self.table.selectRow(0)

    def _on_row_selected(self):
        selected = self.table.selectedItems()
        if not selected:
            return
        row = self.table.currentRow()
        if 0 <= row < len(self.paragraphs):
            para = self.paragraphs[row]
            self.source_text_edit.setPlainText(para.text)
            self.target_text_edit.setPlainText(para.translated_text or "(Translation pending...)")
