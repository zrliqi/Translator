from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLabel, QSplitter, QTextEdit, QPushButton, QComboBox,
    QTabWidget, QListWidget, QListWidgetItem, QMessageBox, QGroupBox, QLineEdit
)
from PySide6.QtCore import Qt, Signal
from typing import List, Optional
from app.document.paragraph_model import ParagraphModel
from app.translation.ai_recheck import AIRecheckEngine
from app.utils.logging import get_logger

logger = get_logger(__name__)

class SideBySidePreviewWidget(QWidget):
    units_updated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.paragraphs: List[ParagraphModel] = []
        self.filtered_paragraphs: List[ParagraphModel] = []
        self.current_index: int = -1
        self.recheck_engine = AIRecheckEngine()

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Navigation & Queue Control Bar
        queue_bar = QHBoxLayout()

        queue_bar.addWidget(QLabel("<b>Review Queue:</b>"))
        self.prev_btn = QPushButton("◄ Previous")
        self.prev_btn.clicked.connect(self._on_prev)
        self.next_btn = QPushButton("Next ►")
        self.next_btn.clicked.connect(self._on_next)

        self.prev_issue_btn = QPushButton("◄ Prev Issue")
        self.prev_issue_btn.clicked.connect(self._on_prev_issue)
        self.next_issue_btn = QPushButton("Next Issue ►")
        self.next_issue_btn.clicked.connect(self._on_next_issue)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "All Units", "Needs Review", "Human Edited",
            "AI Rechecked", "Approved", "Issues Only"
        ])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)

        queue_bar.addWidget(self.prev_btn)
        queue_bar.addWidget(self.next_btn)
        queue_bar.addWidget(self.prev_issue_btn)
        queue_bar.addWidget(self.next_issue_btn)
        queue_bar.addWidget(QLabel("Filter:"))
        queue_bar.addWidget(self.filter_combo)
        queue_bar.addStretch()

        layout.addLayout(queue_bar)

        # Main Splitter: Left (Text Editors) vs Right (Inspector Panel)
        main_splitter = QSplitter(Qt.Horizontal)

        # Dual Pane Editor Splitter
        text_splitter = QSplitter(Qt.Horizontal)

        # Left Text Editor Panel: English Source
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("<b>Original English Text</b>"))
        self.source_text_edit = QTextEdit()
        self.source_text_edit.setReadOnly(True)
        left_layout.addWidget(self.source_text_edit)

        # Right Text Editor Panel: Bangla Translation (Editable)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("<b>Bangla Translation (Human Review & Edit)</b>"))
        self.target_text_edit = QTextEdit()
        right_layout.addWidget(self.target_text_edit)

        # Action Buttons below translation edit box
        edit_actions_layout = QHBoxLayout()
        self.save_edit_btn = QPushButton("Save Human Edit")
        self.save_edit_btn.setStyleSheet("background-color: #2b6cb0; color: white; font-weight: bold;")
        self.save_edit_btn.clicked.connect(self._on_save_edit)

        self.ai_recheck_btn = QPushButton("AI Recheck")
        self.ai_recheck_btn.clicked.connect(self._on_ai_recheck)

        self.approve_btn = QPushButton("Mark Approved")
        self.approve_btn.setStyleSheet("background-color: #2f855a; color: white; font-weight: bold;")
        self.approve_btn.clicked.connect(self._on_mark_approved)

        edit_actions_layout.addWidget(self.save_edit_btn)
        edit_actions_layout.addWidget(self.ai_recheck_btn)
        edit_actions_layout.addWidget(self.approve_btn)
        right_layout.addLayout(edit_actions_layout)

        # Status & Feedback Banner
        self.recheck_status_lbl = QLabel("Recheck Status: Pending")
        self.recheck_status_lbl.setStyleSheet("padding: 4px; background-color: #333; color: #fff;")
        right_layout.addWidget(self.recheck_status_lbl)

        text_splitter.addWidget(left_widget)
        text_splitter.addWidget(right_widget)
        text_splitter.setSizes([350, 450])

        main_splitter.addWidget(text_splitter)

        # Right Inspector Panel (Revisions & Comments Tabs)
        inspector_tabs = QTabWidget()

        # Revisions Tab
        revisions_widget = QWidget()
        rev_layout = QVBoxLayout(revisions_widget)
        self.revisions_list = QListWidget()
        self.revert_btn = QPushButton("Revert to Selected Version")
        self.revert_btn.clicked.connect(self._on_revert_version)
        rev_layout.addWidget(QLabel("<b>Version History</b>"))
        rev_layout.addWidget(self.revisions_list)
        rev_layout.addWidget(self.revert_btn)
        inspector_tabs.addTab(revisions_widget, "Version History")

        # Comments Tab
        comments_widget = QWidget()
        comm_layout = QVBoxLayout(comments_widget)
        self.comments_list = QListWidget()

        add_comm_layout = QHBoxLayout()
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("Enter review comment/suggestion...")
        self.add_comment_btn = QPushButton("Add")
        self.add_comment_btn.clicked.connect(self._on_add_comment)
        add_comm_layout.addWidget(self.comment_input)
        add_comm_layout.addWidget(self.add_comment_btn)

        comm_layout.addWidget(QLabel("<b>Reviewer Comments</b>"))
        comm_layout.addWidget(self.comments_list)
        comm_layout.addLayout(add_comm_layout)
        inspector_tabs.addTab(comments_widget, "Comments")

        main_splitter.addWidget(inspector_tabs)
        main_splitter.setSizes([650, 250])

        layout.addWidget(main_splitter)

        # Table View below for unit selection
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Type", "Review Status", "AI Recheck", "English Preview"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._on_row_selected)
        layout.addWidget(self.table)

    def load_paragraphs(self, paragraphs: List[ParagraphModel]):
        self.paragraphs = paragraphs
        self._apply_filter(self.filter_combo.currentText())

    def _apply_filter(self, filter_text: str):
        if not self.paragraphs:
            self.filtered_paragraphs = []
            self.table.setRowCount(0)
            return

        if filter_text == "Needs Review":
            self.filtered_paragraphs = [p for p in self.paragraphs if p.review_status == "Needs Review"]
        elif filter_text == "Human Edited":
            self.filtered_paragraphs = [p for p in self.paragraphs if p.review_status == "Human Edited"]
        elif filter_text == "AI Rechecked":
            self.filtered_paragraphs = [p for p in self.paragraphs if p.review_status == "AI Rechecked"]
        elif filter_text == "Approved":
            self.filtered_paragraphs = [p for p in self.paragraphs if p.review_status == "Approved"]
        elif filter_text == "Issues Only":
            self.filtered_paragraphs = [
                p for p in self.paragraphs
                if p.ai_recheck_status == "POTENTIAL ISSUE" or p.review_status != "Approved"
            ]
        else:
            self.filtered_paragraphs = list(self.paragraphs)

        self._populate_table()

    def _populate_table(self):
        self.table.setRowCount(0)
        for p in self.filtered_paragraphs:
            row = self.table.rowCount()
            self.table.insertRow(row)

            p_type = "Page Num" if p.is_page_number else ("Heading" if p.is_heading else "Paragraph")

            self.table.setItem(row, 0, QTableWidgetItem(p.id))
            self.table.setItem(row, 1, QTableWidgetItem(p_type))
            self.table.setItem(row, 2, QTableWidgetItem(p.review_status))
            self.table.setItem(row, 3, QTableWidgetItem(p.ai_recheck_status or "-"))

            preview_text = p.text[:70] + ("..." if len(p.text) > 70 else "")
            self.table.setItem(row, 4, QTableWidgetItem(preview_text))

        if self.filtered_paragraphs:
            self.table.selectRow(0)
        else:
            self._clear_editor()

    def _clear_editor(self):
        self.current_index = -1
        self.source_text_edit.setPlainText("")
        self.target_text_edit.setPlainText("")
        self.recheck_status_lbl.setText("Recheck Status: N/A")
        self.revisions_list.clear()
        self.comments_list.clear()

    def _on_row_selected(self):
        row = self.table.currentRow()
        if 0 <= row < len(self.filtered_paragraphs):
            self.current_index = row
            para = self.filtered_paragraphs[row]

            self.source_text_edit.setPlainText(para.source_text)
            self.target_text_edit.setPlainText(para.current_translation)

            # Update Recheck status label
            status_text = para.ai_recheck_status or "Not Rechecked"
            feedback_text = f" - {para.ai_recheck_feedback}" if para.ai_recheck_feedback else ""
            self.recheck_status_lbl.setText(f"AI Recheck Status: {status_text}{feedback_text}")
            if para.ai_recheck_status == "PASS":
                self.recheck_status_lbl.setStyleSheet("padding: 4px; background-color: #1c4532; color: #9ae6b4;")
            elif para.ai_recheck_status == "POTENTIAL ISSUE":
                self.recheck_status_lbl.setStyleSheet("padding: 4px; background-color: #742a2a; color: #feb2b2;")
            elif para.ai_recheck_status == "SUGGESTION":
                self.recheck_status_lbl.setStyleSheet("padding: 4px; background-color: #744210; color: #fbd38d;")
            else:
                self.recheck_status_lbl.setStyleSheet("padding: 4px; background-color: #333333; color: #ffffff;")

            # Update Revisions List
            self.revisions_list.clear()
            for idx, rev in enumerate(para.revisions):
                item_text = f"v{rev.get('version', idx+1)} ({rev.get('type', 'Rev')} by {rev.get('editor', 'User')}): {rev.get('text', '')[:50]}..."
                item = QListWidgetItem(item_text)
                item.setData(Qt.UserRole, idx)
                self.revisions_list.addItem(item)

            # Update Comments List
            self.comments_list.clear()
            for comm in para.comments:
                item_text = f"[{comm.get('author', 'Reviewer')}]: {comm.get('text', '')}"
                self.comments_list.addItem(item_text)

    def _get_current_paragraph(self) -> Optional[ParagraphModel]:
        if 0 <= self.current_index < len(self.filtered_paragraphs):
            return self.filtered_paragraphs[self.current_index]
        return None

    def _on_save_edit(self):
        para = self._get_current_paragraph()
        if not para:
            return
        new_text = self.target_text_edit.toPlainText().strip()
        if not new_text:
            QMessageBox.warning(self, "Warning", "Translation text cannot be empty.")
            return

        para.add_human_edit(new_text, editor="Human Reviewer")
        self._update_current_row_ui(para)
        self.units_updated.emit()
        QMessageBox.information(self, "Saved", "Human correction saved successfully.")

    def _on_ai_recheck(self):
        para = self._get_current_paragraph()
        if not para:
            return
        res = self.recheck_engine.recheck_paragraph(para)
        self._on_row_selected()
        self._update_current_row_ui(para)
        self.units_updated.emit()

    def _on_mark_approved(self):
        para = self._get_current_paragraph()
        if not para:
            return
        para.review_status = "Approved"
        self._update_current_row_ui(para)
        self.units_updated.emit()

    def _update_current_row_ui(self, para: ParagraphModel):
        if 0 <= self.current_index < self.table.rowCount():
            self.table.setItem(self.current_index, 2, QTableWidgetItem(para.review_status))
            self.table.setItem(self.current_index, 3, QTableWidgetItem(para.ai_recheck_status or "-"))

    def _on_prev(self):
        if self.table.rowCount() > 0 and self.current_index > 0:
            self.table.selectRow(self.current_index - 1)

    def _on_next(self):
        if self.table.rowCount() > 0 and self.current_index < self.table.rowCount() - 1:
            self.table.selectRow(self.current_index + 1)

    def _on_prev_issue(self):
        for i in range(self.current_index - 1, -1, -1):
            para = self.filtered_paragraphs[i]
            if para.review_status != "Approved" or para.ai_recheck_status == "POTENTIAL ISSUE":
                self.table.selectRow(i)
                return

    def _on_next_issue(self):
        for i in range(self.current_index + 1, len(self.filtered_paragraphs)):
            para = self.filtered_paragraphs[i]
            if para.review_status != "Approved" or para.ai_recheck_status == "POTENTIAL ISSUE":
                self.table.selectRow(i)
                return

    def _on_revert_version(self):
        para = self._get_current_paragraph()
        selected_item = self.revisions_list.currentItem()
        if not para or not selected_item:
            return
        rev_idx = selected_item.data(Qt.UserRole)
        if para.revert_to_version(rev_idx):
            self._on_row_selected()
            self._update_current_row_ui(para)
            self.units_updated.emit()
            QMessageBox.information(self, "Reverted", "Reverted to selected version.")

    def _on_add_comment(self):
        para = self._get_current_paragraph()
        comm_text = self.comment_input.text().strip()
        if not para or not comm_text:
            return
        para.add_comment(comm_text, author="Reviewer")
        self.comment_input.clear()
        self._on_row_selected()
        self.units_updated.emit()
