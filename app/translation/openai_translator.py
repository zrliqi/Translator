import json
import time
from typing import List
from openai import OpenAI
from app.translation.translator import BaseTranslator
from app.translation.prompts import SYSTEM_PROMPT, build_batch_user_prompt
from app.translation.translation_validator import TranslationValidator
from app.document.paragraph_model import ParagraphModel
from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

class OpenAITranslator(BaseTranslator):
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None

    def translate_paragraph(self, text: str, is_heading: bool = False) -> str:
        if not text.strip():
            return ""
        if not self.client:
            raise ValueError("OpenAI API Key is missing.")

        prompt = f"Translate the following {'heading' if is_heading else 'paragraph'} into natural Bangla:\n\n{text}"

        for attempt in range(settings.retry_count):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                res_text = response.choices[0].message.content.strip()
                valid, msg = TranslationValidator.validate(text, res_text)
                if valid:
                    return res_text
                else:
                    logger.warning(f"Translation validation failed (attempt {attempt+1}): {msg}")
            except Exception as e:
                logger.error(f"OpenAI API call failed (attempt {attempt+1}): {e}")
                time.sleep(1.0 * (attempt + 1))

        return f"[Translation Failed: {text}]"

    def translate_batch(self, paragraphs: List[ParagraphModel]) -> List[str]:
        if not paragraphs:
            return []
        if not self.client:
            raise ValueError("OpenAI API Key is missing.")

        items = [{"id": p.id, "text": p.text} for p in paragraphs]
        user_prompt = build_batch_user_prompt(items)

        for attempt in range(settings.retry_count):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                raw_json = response.choices[0].message.content.strip()
                parsed = json.loads(raw_json)

                # Support both {"items": [...]} or raw [...] list wrapper
                results_list = parsed.get("items", parsed) if isinstance(parsed, dict) else parsed
                if isinstance(results_list, list):
                    res_map = {item.get("id"): item.get("translated_text", "") for item in results_list if isinstance(item, dict)}
                    translated = []
                    for p in paragraphs:
                        t_text = res_map.get(p.id, "")
                        valid, _ = TranslationValidator.validate(p.text, t_text)
                        if valid:
                            translated.append(t_text)
                        else:
                            # Fallback individual call if batch element failed validation
                            translated.append(self.translate_paragraph(p.text, p.is_heading))
                    return translated
            except Exception as e:
                logger.error(f"Batch OpenAI translation failed (attempt {attempt+1}): {e}")
                time.sleep(1.0 * (attempt + 1))

        # Fallback to individual translations if batch fails completely
        return [self.translate_paragraph(p.text, p.is_heading) for p in paragraphs]

class MockTranslator(BaseTranslator):
    """Offline mock translator for testing without API keys."""
    def translate_paragraph(self, text: str, is_heading: bool = False) -> str:
        if not text.strip():
            return ""
        if "Magi" in text or "Gift" in text:
            return "দ্য গিফট অব দ্য ম্যাজাই"
        if "dollar" in text or "cents" in text:
            return "এক ডলার এবং সাতাশি সেন্ট। এই ছিল তার সম্বল।"
        return f"বাংলা অনুবাদ্: {text}"

    def translate_batch(self, paragraphs: List[ParagraphModel]) -> List[str]:
        return [self.translate_paragraph(p.text, p.is_heading) for p in paragraphs]
