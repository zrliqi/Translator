from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel, QGroupBox
)
from PySide6.QtCore import Qt

class ReportDialog(QDialog):
    def __init__(self, report_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Translation Job Report")
        self.resize(550, 450)
        self._init_ui(report_text)

    def _init_ui(self, report_text: str):
        layout = QVBoxLayout(self)

        group = QGroupBox("Execution Summary")
        g_layout = QVBoxLayout(group)

        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFontFamily("Monospace")
        self.text_edit.setPlainText(report_text)
        g_layout.addWidget(self.text_edit)

        layout.addWidget(group)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        btn_box.addWidget(ok_btn)

        layout.addLayout(btn_box)
