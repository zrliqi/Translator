from abc import ABC, abstractmethod
from typing import List
from app.document.paragraph_model import ParagraphModel

class BaseTranslator(ABC):
    @abstractmethod
    def translate_paragraph(self, text: str, is_heading: bool = False) -> str:
        """Translate a single paragraph string from English to Bangla."""
        pass

    @abstractmethod
    def translate_batch(self, paragraphs: List[ParagraphModel]) -> List[str]:
        """Translate a batch of paragraph objects from English to Bangla."""
        pass
