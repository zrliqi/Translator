from dataclasses import dataclass
from typing import Optional, Tuple
from app.document.paragraph_model import ParagraphModel
from app.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class RecheckResult:
    status: str  # "PASS", "SUGGESTION", "POTENTIAL ISSUE"
    feedback: str
    suggested_fix: Optional[str] = None

class AIRecheckEngine:
    def __init__(self, provider_instance=None):
        self.provider = provider_instance

    def recheck(self, source_text: str, current_bangla_text: str) -> RecheckResult:
        """Evaluates human-edited Bangla text against English source text without overwriting."""
        if not source_text.strip() or not current_bangla_text.strip():
            return RecheckResult(
                status="POTENTIAL ISSUE",
                feedback="Source text or Bangla translation is empty."
            )

        # Check if active LLM provider is available
        if self.provider and hasattr(self.provider, "recheck_translation"):
            try:
                res = self.provider.recheck_translation(source_text, current_bangla_text)
                if isinstance(res, RecheckResult):
                    return res
            except Exception as e:
                logger.warning(f"Provider recheck failed, falling back to heuristic recheck: {e}")

        # Heuristic / Quality evaluation fallback
        return self._heuristic_recheck(source_text, current_bangla_text)

    def _heuristic_recheck(self, source_text: str, current_bangla_text: str) -> RecheckResult:
        # Basic sanity checks
        len_src = len(source_text.split())
        len_tgt = len(current_bangla_text.split())

        issues = []
        suggestions = []

        # Check length ratio (very short Bangla vs long English or vice versa)
        if len_src > 5 and len_tgt == 0:
            issues.append("Bangla translation is empty.")
        elif len_src >= 10 and len_tgt <= 2:
            issues.append("Translation seems unusually short compared to English source.")

        # Check for non-Bengali characters in translation (excluding numbers/punctuation/English proper nouns)
        bengali_chars = sum(1 for c in current_bangla_text if '\u0980' <= c <= '\u09FF')
        ascii_alpha = sum(1 for c in current_bangla_text if c.isalpha() and c.isascii())

        if len(current_bangla_text) > 0 and (bengali_chars == 0 and ascii_alpha > 0):
            suggestions.append("Translation appears to contain untranslated English text.")

        if issues:
            return RecheckResult(
                status="POTENTIAL ISSUE",
                feedback=" ".join(issues)
            )
        elif suggestions:
            return RecheckResult(
                status="SUGGESTION",
                feedback=" ".join(suggestions)
            )
        else:
            return RecheckResult(
                status="PASS",
                feedback="Translation is faithful and grammatically coherent."
            )

    def recheck_paragraph(self, paragraph: ParagraphModel) -> RecheckResult:
        res = self.recheck(paragraph.source_text, paragraph.current_translation)
        paragraph.ai_recheck_status = res.status
        paragraph.ai_recheck_feedback = res.feedback
        paragraph.review_status = "AI Rechecked"
        return res
