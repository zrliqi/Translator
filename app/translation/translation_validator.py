import re
from app.utils.logging import get_logger

logger = get_logger(__name__)

class TranslationValidator:
    @staticmethod
    def contains_bengali(text: str) -> bool:
        if not text:
            return False
        # Bengali Unicode block: U+0980 to U+09FF
        bengali_pattern = re.compile(r'[\u0980-\u09FF]')
        return bool(bengali_pattern.search(text))

    @staticmethod
    def validate(source_text: str, translated_text: str) -> tuple[bool, str]:
        if not source_text or not source_text.strip():
            return True, "Empty source text"

        if not translated_text or not translated_text.strip():
            return False, "Translation result is empty"

        # Check for model commentary artifacts like "Here is the translation:"
        if "Here is the translation" in translated_text or "Translation:" in translated_text:
            return False, "Contains model commentary artifact"

        # Verify Bengali characters exist if source contained alphabetic letters
        if any(c.isalpha() for c in source_text) and not TranslationValidator.contains_bengali(translated_text):
            # Allow pure numbers/punctuation to pass, but alphabetic text must contain Bengali
            return False, "Translation does not contain Bengali Unicode characters"

        return True, "Valid"
