import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Settings:
    translation_provider: str = field(default_factory=lambda: os.getenv("TRANSLATION_PROVIDER", "openai"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    google_project_id: str = field(default_factory=lambda: os.getenv("GOOGLE_PROJECT_ID", ""))
    google_credentials_path: str = field(default_factory=lambda: os.getenv("GOOGLE_CREDENTIALS_PATH", os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")))
    local_model: str = field(default_factory=lambda: os.getenv("LOCAL_MODEL", "facebook/nllb-200-distilled-600M"))
    local_device: str = field(default_factory=lambda: os.getenv("LOCAL_DEVICE", "auto"))
    models_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "models")
    batch_size: int = 10
    max_batch_chars: int = 3000
    retry_count: int = 3
    ocr_enabled: bool = True
    scanned_text_density_threshold: float = 0.05
    default_font: str = "Noto Sans Bengali"
    output_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "output")
    preserve_headings: bool = True
    preserve_paragraphs: bool = True
    preserve_page_numbers: bool = True
    preserve_images: bool = True
    preserve_structure: bool = True
    keep_original_page_breaks: bool = False
    log_level: str = "INFO"

    def reload_env(self):
        load_dotenv(override=True)
        self.translation_provider = os.getenv("TRANSLATION_PROVIDER", self.translation_provider)
        self.openai_api_key = os.getenv("OPENAI_API_KEY", self.openai_api_key)
        self.openai_model = os.getenv("OPENAI_MODEL", self.openai_model)
        self.google_project_id = os.getenv("GOOGLE_PROJECT_ID", self.google_project_id)
        self.google_credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", os.getenv("GOOGLE_APPLICATION_CREDENTIALS", self.google_credentials_path))
        self.local_model = os.getenv("LOCAL_MODEL", self.local_model)
        self.local_device = os.getenv("LOCAL_DEVICE", self.local_device)

settings = Settings()
