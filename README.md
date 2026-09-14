# English → Bangla PDF Translator

A production-quality Python PySide6 desktop application for translating English PDF documents into beautifully formatted Unicode Bangla (Bengali) PDFs with complete document structure preservation, accurate Bengali typography/script shaping, translation caching, interrupted job resume support, OCR fallback, and side-by-side preview.

---

## Table of Contents
1. [Key Features](#key-features)
2. [Architecture Overview](#architecture-overview)
3. [Prerequisites & Installation](#prerequisites--installation)
4. [Environment Configuration & API Key Setup](#environment-configuration--api-key-setup)
5. [Google Cloud Translation Setup](#google-cloud-translation-setup)
6. [How to Launch & Use the Application](#how-to-launch--use-the-application)
7. [Side-by-Side Preview](#side-by-side-preview)
8. [Translation Cache & Job Resume System](#translation-cache--job-resume-system)
9. [Bengali Font Handling & Script Shaping](#bengali-font-handling--script-shaping)
10. [OCR Fallback for Scanned Pages](#ocr-fallback-for-scanned-pages)
11. [Running Automated Tests](#running-automated-tests)
12. [Troubleshooting & FAQs](#troubleshooting--faqs)

---

## Key Features

- **Multiple Translation Providers**: Supports OpenAI (`gpt-4o`, `gpt-4o-mini`), **Local AI Translator** (Meta NLLB-200 local model - 100% free, offline, no API key), official Google Cloud Translation API (`en` → `bn`), and offline `mock-translator`.
- **Document Analysis & Detection**: Automatically counts pages, measures text density, and detects scanned/image vs. selectable text pages.
- **Structure Preservation**: Preserves paragraph flow, story headings, page numbers, margins, images, and visual hierarchy.
- **Natural Bengali Typography**: Uses embedded `Noto Sans Bengali` / `Noto Serif Bengali` fonts with MuPDF HTML shaping engine to ensure flawless rendering of Bengali complex scripts, conjuncts (যুক্তাক্ষর), and vowel signs (কার).
- **Persistent Translation Cache**: Uses SQLite database with SHA-256 keys to avoid re-translating identical text chunks across sessions and save API costs (with provider isolation).
- **Interrupted Job Resume**: Automatically saves translation state chunk-by-chunk; if interrupted, restarting resumes from the exact paused location.
- **Side-by-Side Paragraph Inspection**: Built-in tab for side-by-side verification of original English paragraphs alongside Bangla translations.
- **OCR Support**: Integrates `pytesseract` and `pdf2image` for automatic fallback on scanned PDF pages.
- **Safety First**: Never modifies or overwrites the original input PDF.

---

## Architecture Overview

```
app/
├── main.py                     # GUI Application Entry Point
├── config/
│   └── settings.py             # Settings & Environment Configuration
├── gui/
│   ├── main_window.py          # PySide6 Main Application Window
│   ├── widgets/
│   │   └── preview_widget.py   # Side-by-Side Preview Widget
│   ├── dialogs/
│   │   └── report_dialog.py    # Translation Summary Job Report Dialog
│   └── styles/
│       └── theme.py            # GUI Styling Theme
├── pdf/
│   ├── analyzer.py             # PDF Page Density & Scanned Page Detection
│   ├── text_extractor.py       # PyMuPDF Block, Line & Font Extractor
│   ├── page_parser.py          # Paragraph Reconstruction & Page Number Filter
│   ├── layout_analyzer.py      # Story Heading & Layout Structure Classifier
│   └── pdf_builder.py          # PyMuPDF Unicode Bangla PDF Generator
├── ocr/
│   └── ocr_engine.py           # Tesseract OCR Integration Wrapper
├── translation/
│   ├── translator.py           # Abstract Base Translator Interface
│   ├── openai_translator.py    # Official OpenAI SDK & Mock Translators
│   ├── google_translator.py    # Official Google Cloud Translation API Provider
│   ├── local_translator.py     # Local AI NLLB-200 Multilingual Model Translator
│   ├── model_manager.py        # Model Download, Device Placement & RAM/VRAM Lifecycle Manager
│   ├── translation_cache.py    # SQLite SHA-256 Translation Cache
│   ├── translation_validator.py# Bengali Unicode & Integrity Validator
│   └── prompts.py              # Literary Bangla Translation Prompts
├── document/
│   ├── document_model.py       # High-level Document Model
│   ├── page_model.py           # Page Model & Bounding Boxes
│   ├── block_model.py          # Extraction Block Model
│   └── paragraph_model.py      # Reconstructed Paragraph Unit Model
├── fonts/
│   └── font_manager.py         # Bengali Font Discovery & Validation
├── processing/
│   ├── pipeline.py             # Job State & Resume Persistence Manager
│   └── worker.py               # Background PySide6 QThread Worker
└── utils/
    ├── logging.py              # Centralized Application Logging
    └── paths.py                # Platform Path Resolution Utilities

assets/
└── fonts/
    ├── NotoSansBengali-Regular.ttf
    └── NotoSerifBengali-Regular.ttf
```

---

## Prerequisites & Installation

### Requirements
- **Python Version**: Python 3.10 or higher (Tested on Python 3.12).
- **Tesseract OCR (Optional for scanned PDFs)**: Installed system binary for `tesseract`.

### Setup Steps
1. Clone or extract the repository.
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

---

## Environment Configuration & API Key Setup

Create a `.env` file in the project root directory (or copy from `.env.example`):
```bash
cp .env.example .env
```
Edit `.env` to set your OpenAI API key and model or Google credentials:
```env
TRANSLATION_PROVIDER=openai
OPENAI_API_KEY=sk-your-actual-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Google Cloud Translation Settings (Optional if using Google Provider)
GOOGLE_PROJECT_ID=your-google-project-id
GOOGLE_CREDENTIALS_PATH=/path/to/your/service_account_credentials.json
```
*Note: You can also enter or override credentials directly within the GUI setting fields.*

---

## Local AI Translator Setup & Model Management

The **Local AI Translator** option allows you to translate English PDFs into Bangla **completely locally** on your computer without any cloud service, API key, credit card, or web scraping.

### Features:
- **Model**: Meta NLLB-200 (`facebook/nllb-200-distilled-600M`).
- **No API Key or Internet Required**: Runs 100% offline once downloaded.
- **Hardware Acceleration**: Automatically selects CUDA GPU if available and supported, otherwise seamlessly uses CPU.
- **Model Storage**: Saved in the `models/` directory inside the application folder using `pathlib`.
- **First-Run Download**: The model (~2.4 GB) is downloaded only when requested via the GUI `[ Download Model ]` button or when starting a job with the provider selected for the first time.

### Device Selection Options:
- `auto`: Uses CUDA if an NVIDIA GPU is available, otherwise CPU.
- `cpu`: Forces translation on CPU.
- `cuda`: Forces translation on CUDA GPU (falls back to CPU if unavailable or out-of-memory).

---

## Google Cloud Translation Setup

To use Google Cloud Translation as a real translation provider in the application:

1. **Create or select a Google Cloud Project** in the [Google Cloud Console](https://console.cloud.google.com/).
2. **Enable the Cloud Translation API** for your project:
   - Go to APIs & Services > Enabled APIs & Services.
   - Click **+ ENABLE APIS AND SERVICES** and search for **Cloud Translation API**.
   - Click **Enable**.
3. **Configure Authentication**:
   - Create a Service Account under **IAM & Admin > Service Accounts**.
   - Grant appropriate roles (e.g., `Cloud Translation API User`).
   - Create and download a JSON Service Account Key file to your computer.
4. **Provide Credentials to Application**:
   - In the GUI under **LANGUAGE & MODEL SETTINGS**, select `Google Cloud Translation` in **Translation Provider**.
   - Enter your **Google Project ID** (or leave empty if included in the service account JSON).
   - Click **Browse...** next to **Google Credentials** to select your downloaded Service Account JSON key file.
   - Alternatively, set `GOOGLE_CREDENTIALS_PATH` and `GOOGLE_PROJECT_ID` in your `.env` file or environment variables.
5. **Test the Connection**:
   - Click **[ Test Google Connection ]** in the GUI to verify that credentials are valid and the Cloud Translation API is accessible.
6. **Run a Small Test Translation First**:
   - Use **Test Mode (Pages)** setting (e.g., `1` or `3` pages) to test integration before running full translations.

---

## How to Launch & Use the Application

1. **Launch the GUI**:
   ```bash
   python3 main.py
   ```
2. **Select Input PDF**: Click **Browse...** to select an English PDF document.
3. **Analyze PDF**: Click **Analyze PDF**. The app scans pages, extracts layout blocks, reconstructs broken lines into paragraphs, and displays file metadata.
4. **Choose Settings**:
   - Select **Translation Provider** (`OpenAI`, `Google Cloud Translation`, or `Mock Translator`).
   - Configure model/credentials for the chosen provider.
   - Select font (`Noto Sans Bengali` or `Noto Serif Bengali`).
   - Test Mode (optional: enter `1`, `3`, or `5` pages to test a subset first).
   - Checkboxes for headings, paragraphs, page numbers, images, and OCR.
5. **Translate PDF**: Click **Translate PDF**. Real-time progress bar, page count, chunk stats, and error counter will update.
6. **Output Location**: Generated PDFs are safely saved in the `output/` folder with `_Bangla.pdf` appended to avoid modifying the original file. Click **Open Output Folder** to view generated files.

---

## Side-by-Side Preview

Switch to the **Side-by-Side Preview** tab in the GUI at any point during or after analysis/translation. Select any extracted paragraph block from the table to view the original English source text side-by-side with its Bangla translation.

---

## Translation Cache & Job Resume System

- **Caching**: Every translated paragraph is cached locally in `cache/translation_cache.db` indexed by a SHA-256 hash of `(source_text, source_lang, target_lang, model_name)`. Re-running translation on identical text instantly returns cached translations without making external API calls. Cache keys strictly distinguish between OpenAI (`gpt-4o-mini`), Google (`google-cloud-translate`), and Mock providers.
- **Job Resume**: The system records active job progress in SQLite (`job_state` table). If a job is interrupted or cancelled, re-running the application on the same file loads the previous progress map and resumes directly from the remaining untranslated blocks.

---

## Bengali Font Handling & Script Shaping

Bengali script requires complex shaping (joining consonants and placing vowel diacritics / কার signs correctly). Standard canvas rendering often misplaces vowels or breaks conjuncts. This application embeds true Unicode `Noto Sans Bengali` / `Noto Serif Bengali` OpenType TTF fonts and utilizes PyMuPDF's HTML box engine for native font shaping, producing accurate Bengali script without broken glyphs.

---

## OCR Fallback for Scanned Pages

For PDF documents containing scanned pages or images with low text density, the application detects scanned pages and routes them to `TesseractOCREngine` (`pytesseract` + `pdf2image`) to extract readable English text before paragraph reconstruction.

---

## Running Automated Tests

Run the unit test suite to verify extraction, paragraph parsing, layout analysis, font loading, Google & OpenAI translation providers, caching, job state saving, and PDF creation:
```bash
python3 -m unittest discover tests
```

---

## Troubleshooting & FAQs

- **Q: Bengali characters appear broken or blank in third-party viewers.**
  - **A**: Ensure `assets/fonts/NotoSansBengali-Regular.ttf` is present. The application embeds the font inside the generated PDF for universal viewing across PDF readers.
- **Q: Translation fails due to Google API authentication errors.**
  - **A**: Verify your Google Project ID and Service Account JSON key path. Click **Test Google Connection** in the GUI to diagnose authentication issues.
- **Q: Translation fails due to OpenAI API key errors.**
  - **A**: Verify your key in `.env` or in the GUI field. You can test full application flow offline without an API key by selecting `Mock Translator` in the Translation Provider dropdown.
- **Q: Application shows GUI display warning on headless Linux server.**
  - **A**: If running on a headless Linux environment without an X server, set `QT_QPA_PLATFORM=offscreen python3 main.py`.
