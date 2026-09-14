from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional

class OCREngine(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        """Check if OCR binary dependencies are installed."""
        pass

    @abstractmethod
    def extract_text_from_image(self, image_path_or_bytes: Any, lang: str = "eng") -> str:
        """Extract plain text from an image."""
        pass

class TesseractOCREngine(OCREngine):
    def __init__(self, tesseract_cmd: Optional[str] = None):
        self.tesseract_cmd = tesseract_cmd

    def is_available(self) -> bool:
        try:
            import pytesseract
            if self.tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
            # Perform quick check
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract_text_from_image(self, image_path_or_bytes: Any, lang: str = "eng") -> str:
        if not self.is_available():
            raise RuntimeError("Tesseract OCR is not installed or available on this system.")
        import pytesseract
        from PIL import Image
        import io

        if isinstance(image_path_or_bytes, bytes):
            image = Image.open(io.BytesIO(image_path_or_bytes))
        else:
            image = Image.open(image_path_or_bytes)

        return pytesseract.image_to_string(image, lang=lang)
