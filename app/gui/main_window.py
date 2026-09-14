import os
import sys
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QPushButton, QCheckBox, QComboBox, QProgressBar, QTabWidget,
    QFileDialog, QMessageBox, QSpinBox, QFormLayout
)
from PySide6.QtCore import Qt, QThread, Signal, Slot

from app.config.settings import settings
from app.fonts.font_manager import FontManager
from app.translation.model_manager import ModelManager
from app.utils.paths import get_output_dir
from app.utils.logging import get_logger
from app.gui.styles.theme import STYLE_SHEET
from app.gui.widgets.preview_widget import SideBySidePreviewWidget
from app.gui.dialogs.report_dialog import ReportDialog

logger = get_logger(__name__)

class ModelDownloadWorker(QThread):
    progress_updated = Signal(int, str)
    download_finished = Signal(bool, str)

    def __init__(self, model_manager: ModelManager, parent=None):
        super().__init__(parent)
        self.model_manager = model_manager

    def run(self):
        try:
            def cb(pct, msg):
                self.progress_updated.emit(pct, msg)

            self.model_manager.download_model(progress_callback=cb)
            self.download_finished.emit(True, "Model downloaded and verified successfully!")
        except Exception as e:
            logger.error(f"Model download error: {e}")
            self.download_finished.emit(False, str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("English → Bangla PDF Translator")
        self.resize(950, 750)
        self.setStyleSheet(STYLE_SHEET)

        self.input_pdf_path: Path = None
        self.analyzed_doc = None
        self.worker_thread: QThread = None
        self.model_manager = ModelManager(model_repo=settings.local_model)
        self.download_worker: QThread = None

        self._init_ui()

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Tab Widget for Main App vs Preview
        self.tabs = QTabWidget()

        # Main Tab
        main_tab = QWidget()
        main_tab_layout = QVBoxLayout(main_tab)

        # Header
        header_layout = QVBoxLayout()
        title_lbl = QLabel("<h1>English → Bangla PDF Translator</h1>")
        subtitle_lbl = QLabel("Translate English PDF documents into properly formatted Unicode Bangla PDFs.")
        subtitle_lbl.setStyleSheet("color: #555555; margin-bottom: 10px;")
        header_layout.addWidget(title_lbl)
        header_layout.addWidget(subtitle_lbl)
        main_tab_layout.addLayout(header_layout)

        # Input Section
        input_group = QGroupBox("INPUT SECTION")
        input_layout = QFormLayout(input_group)

        file_picker_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setReadOnly(True)
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self._on_browse_file)
        file_picker_layout.addWidget(self.file_path_edit)
        file_picker_layout.addWidget(self.browse_btn)

        input_layout.addRow("Input PDF:", file_picker_layout)

        # Metadata labels
        self.file_info_lbl = QLabel("File: N/A | Pages: 0 | Type: N/A | Status: Not Loaded")
        input_layout.addRow("Display Info:", self.file_info_lbl)

        main_tab_layout.addWidget(input_group)

        # Settings Grid (Language, Engine, Options)
        settings_hbox = QHBoxLayout()

        # Language & Model Section
        lang_group = QGroupBox("LANGUAGE & MODEL SETTINGS")
        lang_layout = QFormLayout(lang_group)

        self.src_lang_lbl = QLabel("English")
        self.tgt_lang_lbl = QLabel("বাংলা (Bangla)")
        lang_layout.addRow("Source Language:", self.src_lang_lbl)
        lang_layout.addRow("Target Language:", self.tgt_lang_lbl)

        # Provider Selector
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "Local AI Translator", "Google Cloud Translation", "Mock Translator"])
        lang_layout.addRow("Translation Provider:", self.provider_combo)

        # OpenAI Container Widget
        self.openai_container = QWidget()
        openai_layout = QFormLayout(self.openai_container)
        openai_layout.setContentsMargins(0, 0, 0, 0)

        self.model_combo = QComboBox()
        self.model_combo.addItems(["gpt-4o-mini", "gpt-4o"])
        self.model_combo.setCurrentText(settings.openai_model if settings.openai_model in ["gpt-4o-mini", "gpt-4o"] else "gpt-4o-mini")
        openai_layout.addRow("Translation Model:", self.model_combo)

        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Loaded from .env if left empty")
        self.api_key_edit.setText(settings.openai_api_key)
        openai_layout.addRow("API Key:", self.api_key_edit)

        lang_layout.addRow(self.openai_container)

        # Local AI Translator Container Widget
        self.local_container = QWidget()
        local_layout = QFormLayout(self.local_container)
        local_layout.setContentsMargins(0, 0, 0, 0)

        self.local_model_lbl = QLabel("Meta NLLB-200 (distilled-600M)")
        local_layout.addRow("Local Model:", self.local_model_lbl)

        self.local_device_combo = QComboBox()
        self.local_device_combo.addItems(["auto", "cpu", "cuda"])
        self.local_device_combo.setCurrentText(settings.local_device)
        local_layout.addRow("Hardware Device:", self.local_device_combo)

        self.local_status_lbl = QLabel("Checking status...")
        local_layout.addRow("Status:", self.local_status_lbl)

        self.download_model_btn = QPushButton("Download Model")
        self.download_model_btn.clicked.connect(self._on_download_model)
        local_layout.addRow("Model Management:", self.download_model_btn)

        lang_layout.addRow(self.local_container)

        # Google Cloud Translation Container Widget
        self.google_container = QWidget()
        google_layout = QFormLayout(self.google_container)
        google_layout.setContentsMargins(0, 0, 0, 0)

        self.google_project_edit = QLineEdit()
        self.google_project_edit.setPlaceholderText("Optional if in credentials JSON")
        self.google_project_edit.setText(settings.google_project_id)
        google_layout.addRow("Google Project ID:", self.google_project_edit)

        google_cred_picker_layout = QHBoxLayout()
        self.google_cred_edit = QLineEdit()
        self.google_cred_edit.setPlaceholderText("Path to service account JSON file")
        self.google_cred_edit.setText(settings.google_credentials_path)
        self.google_cred_browse_btn = QPushButton("Browse...")
        self.google_cred_browse_btn.clicked.connect(self._on_browse_google_cred)
        google_cred_picker_layout.addWidget(self.google_cred_edit)
        google_cred_picker_layout.addWidget(self.google_cred_browse_btn)

        google_layout.addRow("Google Credentials:", google_cred_picker_layout)

        self.test_conn_btn = QPushButton("Test Google Connection")
        self.test_conn_btn.clicked.connect(self._on_test_google_connection)
        google_layout.addRow("Connection Test:", self.test_conn_btn)

        lang_layout.addRow(self.google_container)

        # Connect Provider Change Signal
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)

        # Set initial provider selection
        if settings.translation_provider.lower() in ["google", "google cloud translation"]:
            self.provider_combo.setCurrentText("Google Cloud Translation")
        elif settings.translation_provider.lower() in ["local", "local ai translator"]:
            self.provider_combo.setCurrentText("Local AI Translator")
        elif settings.translation_provider.lower() in ["mock", "mock-translator"]:
            self.provider_combo.setCurrentText("Mock Translator")
        else:
            self.provider_combo.setCurrentText("OpenAI")
        self._on_provider_changed(self.provider_combo.currentText())

        self.font_combo = QComboBox()
        available_fonts = FontManager.get_instance().list_available_fonts()
        self.font_combo.addItems(available_fonts)
        if settings.default_font in available_fonts:
            self.font_combo.setCurrentText(settings.default_font)
        lang_layout.addRow("Bangla Font:", self.font_combo)

        # Test Mode (Limit pages)
        self.page_limit_spin = QSpinBox()
        self.page_limit_spin.setRange(0, 1000)
        self.page_limit_spin.setValue(0)
        self.page_limit_spin.setSpecialValueText("All Pages")
        lang_layout.addRow("Test Mode (Pages):", self.page_limit_spin)

        settings_hbox.addWidget(lang_group)

        # Document Options Section
        doc_opts_group = QGroupBox("DOCUMENT OPTIONS")
        doc_opts_layout = QVBoxLayout(doc_opts_group)

        self.chk_headings = QCheckBox("Preserve headings")
        self.chk_headings.setChecked(settings.preserve_headings)
        self.chk_paragraphs = QCheckBox("Preserve paragraphs")
        self.chk_paragraphs.setChecked(settings.preserve_paragraphs)
        self.chk_page_nums = QCheckBox("Preserve page numbers")
        self.chk_page_nums.setChecked(settings.preserve_page_numbers)
        self.chk_images = QCheckBox("Preserve images")
        self.chk_images.setChecked(settings.preserve_images)
        self.chk_structure = QCheckBox("Preserve document structure")
        self.chk_structure.setChecked(settings.preserve_structure)
        self.chk_ocr = QCheckBox("Use OCR when necessary")
        self.chk_ocr.setChecked(settings.ocr_enabled)
        self.chk_page_breaks = QCheckBox("Keep original page breaks")
        self.chk_page_breaks.setChecked(settings.keep_original_page_breaks)

        doc_opts_layout.addWidget(self.chk_headings)
        doc_opts_layout.addWidget(self.chk_paragraphs)
        doc_opts_layout.addWidget(self.chk_page_nums)
        doc_opts_layout.addWidget(self.chk_images)
        doc_opts_layout.addWidget(self.chk_structure)
        doc_opts_layout.addWidget(self.chk_ocr)
        doc_opts_layout.addWidget(self.chk_page_breaks)

        settings_hbox.addWidget(doc_opts_group)
        main_tab_layout.addLayout(settings_hbox)

        # Action Buttons
        action_layout = QHBoxLayout()
        self.analyze_btn = QPushButton("Analyze PDF")
        self.analyze_btn.clicked.connect(self._on_analyze_pdf)
        self.analyze_btn.setEnabled(False)

        self.translate_btn = QPushButton("Translate PDF")
        self.translate_btn.clicked.connect(self._on_translate_pdf)
        self.translate_btn.setEnabled(False)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_button")
        self.cancel_btn.clicked.connect(self._on_cancel)
        self.cancel_btn.setEnabled(False)

        self.open_out_btn = QPushButton("Open Output Folder")
        self.open_out_btn.clicked.connect(self._on_open_output_folder)

        action_layout.addWidget(self.analyze_btn)
        action_layout.addWidget(self.translate_btn)
        action_layout.addWidget(self.cancel_btn)
        action_layout.addWidget(self.open_out_btn)

        main_tab_layout.addLayout(action_layout)

        # Progress Section
        progress_group = QGroupBox("PROGRESS SECTION")
        progress_layout = QVBoxLayout(progress_group)

        self.status_lbl = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        self.stats_lbl = QLabel("Pages processed: 0 / 0 | Chunks: 0 / 0 | Errors: 0")

        progress_layout.addWidget(self.status_lbl)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.stats_lbl)

        main_tab_layout.addWidget(progress_group)

        self.tabs.addTab(main_tab, "Translation Job")

        # Preview Tab
        self.preview_widget = SideBySidePreviewWidget()
        self.tabs.addTab(self.preview_widget, "Side-by-Side Preview")

        main_layout.addWidget(self.tabs)

    def _on_provider_changed(self, provider_text: str):
        if provider_text == "OpenAI":
            self.openai_container.setVisible(True)
            self.local_container.setVisible(False)
            self.google_container.setVisible(False)
        elif provider_text == "Local AI Translator":
            self.openai_container.setVisible(False)
            self.local_container.setVisible(True)
            self.google_container.setVisible(False)
            self._update_local_status()
        elif provider_text == "Google Cloud Translation":
            self.openai_container.setVisible(False)
            self.local_container.setVisible(False)
            self.google_container.setVisible(True)
        else: # Mock Translator
            self.openai_container.setVisible(False)
            self.local_container.setVisible(False)
            self.google_container.setVisible(False)

    def _update_local_status(self):
        if self.model_manager.is_model_installed():
            size_mb = self.model_manager.get_model_size_mb()
            self.local_status_lbl.setText(f"✓ Ready ({size_mb:.1f} MB)")
            self.download_model_btn.setText("Re-download / Verify Model")
        else:
            self.local_status_lbl.setText("Status: Not Installed")
            self.download_model_btn.setText("Download Model")

    def _on_download_model(self):
        if self.download_worker and self.download_worker.isRunning():
            QMessageBox.information(self, "Download in Progress", "Model download is already in progress.")
            return

        self.download_model_btn.setEnabled(False)
        self.status_lbl.setText("Downloading translation model...")

        self.download_worker = ModelDownloadWorker(self.model_manager, self)
        self.download_worker.progress_updated.connect(self._on_download_progress)
        self.download_worker.download_finished.connect(self._on_download_finished)
        self.download_worker.start()

    def _on_download_progress(self, pct: int, msg: str):
        self.progress_bar.setValue(pct)
        self.status_lbl.setText(msg)
        self.local_status_lbl.setText(f"Downloading... ({pct}%)")

    def _on_download_finished(self, success: bool, msg: str):
        self.download_model_btn.setEnabled(True)
        self._update_local_status()
        if success:
            self.progress_bar.setValue(100)
            self.status_lbl.setText("Local translation model is ready.")
            QMessageBox.information(self, "Download Complete", msg)
        else:
            self.status_lbl.setText(f"Download failed: {msg}")
            QMessageBox.critical(self, "Download Error", f"Failed to download model:\n{msg}")

    def _on_browse_google_cred(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Google Service Account JSON Key",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.google_cred_edit.setText(file_path)

    def _on_test_google_connection(self):
        project_id = self.google_project_edit.text().strip()
        credentials_path = self.google_cred_edit.text().strip()

        from app.translation.google_translator import GoogleTranslator
        translator = GoogleTranslator(project_id=project_id, credentials_path=credentials_path)

        success, msg = translator.validate_connection()
        if success:
            QMessageBox.information(self, "Google Connection Test", msg)
        else:
            QMessageBox.warning(self, "Google Connection Failed", msg)

    def _on_browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Input English PDF", "", "PDF Files (*.pdf)")
        if file_path:
            self.input_pdf_path = Path(file_path)
            self.file_path_edit.setText(str(self.input_pdf_path))
            self.file_info_lbl.setText(f"File: {self.input_pdf_path.name} | Status: Selected (Pending Analysis)")
            self.analyze_btn.setEnabled(True)
            self.translate_btn.setEnabled(False)

    def _on_analyze_pdf(self):
        if not self.input_pdf_path or not self.input_pdf_path.exists():
            QMessageBox.warning(self, "Error", "Selected PDF file does not exist.")
            return

        from app.pdf.analyzer import PDFAnalyzer
        from app.pdf.text_extractor import TextExtractor
        from app.pdf.page_parser import PageParser

        try:
            self.status_lbl.setText("Analyzing PDF...")
            analyzer = PDFAnalyzer()
            res = analyzer.analyze(self.input_pdf_path)

            extractor = TextExtractor(extract_images=self.chk_images.isChecked())
            self.analyzed_doc = extractor.extract_document(self.input_pdf_path)

            parser = PageParser(
                preserve_headings=self.chk_headings.isChecked(),
                preserve_page_numbers=self.chk_page_nums.isChecked()
            )
            for page in self.analyzed_doc.pages:
                parser.parse_page(page)

            pdf_type = "Scanned PDF (OCR Required)" if res.is_scanned else "Text PDF"
            size_mb = res.file_size_bytes / (1024 * 1024)
            self.file_info_lbl.setText(
                f"File: {res.file_path.name} ({size_mb:.2f} MB) | Pages: {res.total_pages} | Type: {pdf_type} | Analysis Complete"
            )

            # Load into side-by-side preview tab
            all_paras = self.analyzed_doc.get_all_paragraphs()
            self.preview_widget.load_paragraphs(all_paras)

            self.status_lbl.setText("Analysis completed successfully. Ready to translate.")
            self.translate_btn.setEnabled(True)
        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            QMessageBox.critical(self, "Analysis Failed", f"An error occurred during analysis: {e}")

    def _on_translate_pdf(self):
        if not self.analyzed_doc or not self.input_pdf_path:
            QMessageBox.warning(self, "Warning", "Please analyze the PDF first.")
            return

        provider_text = self.provider_combo.currentText()
        api_key = self.api_key_edit.text().strip()
        model_name = self.model_combo.currentText()
        google_proj = self.google_project_edit.text().strip()
        google_cred = self.google_cred_edit.text().strip()

        if provider_text == "OpenAI":
            provider = "openai"
            if not api_key:
                QMessageBox.warning(self, "API Key Missing", "Please enter an OpenAI API key.")
                return
        elif provider_text == "Local AI Translator":
            provider = "local"
            model_name = settings.local_model
            if not self.model_manager.is_model_installed():
                reply = QMessageBox.question(
                    self,
                    "Model Not Installed",
                    "Local translation model is not installed.\n\n"
                    "Download the model now to enable offline English → Bangla translation?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self._on_download_model()
                return
        elif provider_text == "Google Cloud Translation":
            provider = "google"
            model_name = "google-cloud-translate"
            if google_cred and not Path(google_cred).exists():
                QMessageBox.warning(self, "Credentials Error", f"Google credentials file not found: {google_cred}")
                return
        else: # Mock Translator
            provider = "mock"
            model_name = "mock-translator"

        from app.processing.worker import TranslationWorker
        self.worker = TranslationWorker(
            input_path=self.input_pdf_path,
            provider=provider,
            model_name=model_name,
            api_key=api_key,
            google_project_id=google_proj,
            google_credentials_path=google_cred,
            local_device=self.local_device_combo.currentText(),
            font_name=self.font_combo.currentText(),
            page_limit=self.page_limit_spin.value(),
            preserve_headings=self.chk_headings.isChecked(),
            preserve_paragraphs=self.chk_paragraphs.isChecked(),
            preserve_page_numbers=self.chk_page_nums.isChecked(),
            preserve_images=self.chk_images.isChecked(),
            preserve_structure=self.chk_structure.isChecked(),
            use_ocr=self.chk_ocr.isChecked(),
            keep_page_breaks=self.chk_page_breaks.isChecked()
        )

        self.worker.progress_updated.connect(self._on_progress_update)
        self.worker.stats_updated.connect(self._on_stats_update)
        self.worker.job_finished.connect(self._on_job_finished)
        self.worker.job_failed.connect(self._on_job_failed)

        self.translate_btn.setEnabled(False)
        self.analyze_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        self.worker.start()

    def _on_progress_update(self, val: int, max_val: int, msg: str):
        self.progress_bar.setMaximum(max_val)
        self.progress_bar.setValue(val)
        self.status_lbl.setText(msg)

    def _on_stats_update(self, p_done: int, p_total: int, chunks: int, errors: int):
        self.stats_lbl.setText(f"Pages processed: {p_done} / {p_total} | Chunks: {chunks} | Errors: {errors}")

    def _on_job_finished(self, out_path: str, report: str):
        self.translate_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

        # Update preview with translated text
        all_paras = self.analyzed_doc.get_all_paragraphs()
        self.preview_widget.load_paragraphs(all_paras)

        dialog = ReportDialog(report, self)
        dialog.exec()

    def _on_job_failed(self, error_msg: str):
        self.translate_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.status_lbl.setText(f"Failed: {error_msg}")
        QMessageBox.critical(self, "Job Error", f"Translation job halted: {error_msg}")

    def _on_cancel(self):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.cancel()
            self.status_lbl.setText("Cancelling worker thread...")

    def _on_open_output_folder(self):
        out_dir = get_output_dir()
        if sys.platform == "win32":
            os.startfile(out_dir)
        elif sys.platform == "darwin":
            import subprocess
            subprocess.Popen(["open", out_dir])
        else:
            import subprocess
            subprocess.Popen(["xdg-open", out_dir])
