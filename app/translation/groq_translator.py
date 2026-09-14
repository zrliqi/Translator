import json
import os
import time
from typing import List
from groq import Groq
from app.translation.translator import BaseTranslator
from app.translation.prompts import SYSTEM_PROMPT, build_batch_user_prompt
from app.translation.translation_validator import TranslationValidator
from app.document.paragraph_model import ParagraphModel
from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

GROQ_SYSTEM_PROMPT = """You are an expert English-to-Bangla literary translator.
Translate the supplied English text into natural, fluent Bangla.

Rules:
- Translate faithfully.
- Do not summarize.
- Do not omit content.
- Do not add explanations.
- Preserve paragraph boundaries.
- Preserve dialogue.
- Preserve names and proper nouns appropriately.
- Preserve numbers and monetary values.
- Preserve punctuation and quotation structure.
- Maintain the literary tone.
- Return ONLY the Bangla translation.
"""

class GroqTranslator(BaseTranslator):
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or settings.groq_api_key
        self.model = model or settings.groq_model or "llama-3.3-70b-versatile"
        self._client = None

    @property
    def client(self) -> Groq:
        if self._client is None:
            if not self.api_key:
                raise ValueError("GROQ_API_KEY was not found. Please add GROQ_API_KEY=... to the .env file.")
            try:
                self._client = Groq(api_key=self.api_key)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Groq client: {self._sanitize_error(str(e))}")
        return self._client

    def _sanitize_error(self, err_msg: str) -> str:
        """Ensure API key is never exposed in error messages."""
        if self.api_key and self.api_key in err_msg:
            err_msg = err_msg.replace(self.api_key, "[REDACTED_API_KEY]")
        return err_msg

    def _clean_response(self, text: str) -> str:
        """Strip markdown wrappers like ```text or ``` json if present."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if len(lines) >= 2 and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
        return cleaned

    def validate_connection(self) -> tuple[bool, str]:
        """Validate API key and model availability with a lightweight check."""
        if not self.api_key:
            return False, "GROQ_API_KEY was not found. Please add GROQ_API_KEY=... to the .env file."
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a translator."},
                    {"role": "user", "content": "Ping"}
                ],
                max_tokens=5
            )
            return True, f"Successfully connected to Groq API ({self.model})."
        except Exception as e:
            err = self._sanitize_error(str(e))
            if "authentication" in err.lower() or "401" in err or "invalid api key" in err.lower():
                return False, "Groq API authentication failed."
            if "rate limit" in err.lower() or "429" in err:
                return False, "Groq API rate limit reached."
            if "model" in err.lower() and ("not found" in err.lower() or "does not exist" in err.lower() or "404" in err):
                return False, f"The selected Groq model ({self.model}) is unavailable."
            return False, f"Groq connection check failed: {err}"

    def translate_paragraph(self, text: str, is_heading: bool = False) -> str:
        if not text.strip():
            return ""

        prompt = f"Translate the following {'heading' if is_heading else 'paragraph'} into natural Bangla. Return ONLY the Bangla translation without any commentary or markdown blocks:\n\n{text}"

        for attempt in range(settings.retry_count):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": GROQ_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                res_text = response.choices[0].message.content or ""
                res_text = self._clean_response(res_text)

                valid, msg = TranslationValidator.validate(text, res_text)
                if valid:
                    return res_text
                else:
                    logger.warning(f"Groq translation validation failed (attempt {attempt+1}): {msg}")
            except Exception as e:
                err_clean = self._sanitize_error(str(e))
                logger.error(f"Groq API call failed (attempt {attempt+1}): {err_clean}")
                if "401" in err_clean or "authentication" in err_clean.lower():
                    raise RuntimeError("Groq API authentication failed.") from e
                time.sleep(1.0 * (attempt + 1))

        return f"[Translation Failed: {text}]"

    def translate_batch(self, paragraphs: List[ParagraphModel]) -> List[str]:
        if not paragraphs:
            return []

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
                raw_text = response.choices[0].message.content or ""
                cleaned_text = self._clean_response(raw_text)
                parsed = json.loads(cleaned_text)

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
                            translated.append(self.translate_paragraph(p.text, p.is_heading))
                    return translated
            except Exception as e:
                err_clean = self._sanitize_error(str(e))
                logger.error(f"Batch Groq translation failed (attempt {attempt+1}): {err_clean}")
                if "401" in err_clean or "authentication" in err_clean.lower():
                    raise RuntimeError("Groq API authentication failed.") from e
                time.sleep(1.0 * (attempt + 1))

        # Fallback to individual translations if batch fails completely
        return [self.translate_paragraph(p.text, p.is_heading) for p in paragraphs]
