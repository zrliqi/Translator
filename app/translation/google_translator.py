import html
import json
import time
from pathlib import Path
from typing import List, Tuple, Optional

from app.translation.translator import BaseTranslator
from app.translation.translation_validator import TranslationValidator
from app.document.paragraph_model import ParagraphModel
from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

class GoogleTranslator(BaseTranslator):
    def __init__(self, project_id: Optional[str] = None, credentials_path: Optional[str] = None):
        self.project_id = project_id if project_id is not None else settings.google_project_id
        self.credentials_path = credentials_path if credentials_path is not None else settings.google_credentials_path

    def _resolve_project_id_and_credentials(self) -> Tuple[str, Optional[object]]:
        """
        Resolves the Google Project ID and Service Account Credentials object.
        Returns (project_id, credentials_obj).
        """
        from google.oauth2 import service_account

        cred_path_str = self.credentials_path or settings.google_credentials_path
        project_id = self.project_id or settings.google_project_id

        credentials_obj = None

        if cred_path_str:
            cred_file = Path(cred_path_str)
            if not cred_file.exists():
                raise FileNotFoundError(f"Google credentials file not found: {cred_path_str}")

            try:
                credentials_obj = service_account.Credentials.from_service_account_file(str(cred_file))
            except Exception as e:
                raise ValueError(f"Failed to parse Google credentials file: {e}")

            if not project_id:
                try:
                    with open(cred_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        project_id = data.get("project_id", "")
                except Exception as e:
                    logger.warning(f"Could not read project_id from credentials JSON: {e}")

        if not project_id:
            raise ValueError("Google Project ID is missing. Please set Google Project ID or provide a service account credential file containing project_id.")

        return project_id, credentials_obj

    def _get_client(self):
        from google.cloud import translate_v3
        project_id, credentials_obj = self._resolve_project_id_and_credentials()
        if credentials_obj:
            client = translate_v3.TranslationServiceClient(credentials=credentials_obj)
        else:
            client = translate_v3.TranslationServiceClient()
        return client, project_id

    def validate_connection(self) -> Tuple[bool, str]:
        """
        Validates credentials and tests access to the Google Cloud Translation API.
        Returns (True, "Success message") or (False, "Error message").
        """
        try:
            client, project_id = self._get_client()
            parent = f"projects/{project_id}/locations/global"
            from google.cloud import translate_v3
            request = translate_v3.TranslateTextRequest(
                parent=parent,
                contents=["Hello"],
                mime_type="text/plain",
                source_language_code="en",
                target_language_code="bn"
            )
            response = client.translate_text(request=request)
            if response.translations:
                return True, "Google Cloud Translation connection successful!"
            else:
                return False, "Google Cloud Translation returned empty response."
        except FileNotFoundError as e:
            return False, str(e)
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            err_str = str(e)
            if "PermissionDenied" in err_str or "403" in err_str:
                return False, f"Google Cloud Translation API is not available or disabled for project '{self.project_id}'. Please check API permissions."
            elif "Unauthenticated" in err_str or "401" in err_str:
                return False, "Google Cloud Translation authentication failed. Please check credentials."
            elif "ResourceExhausted" in err_str or "429" in err_str:
                return False, "Google API quota/rate limit was reached."
            else:
                return False, f"Google Cloud Translation connection failed: {err_str}"

    def translate_paragraph(self, text: str, is_heading: bool = False) -> str:
        if not text.strip():
            return ""

        for attempt in range(settings.retry_count):
            try:
                client, project_id = self._get_client()
                parent = f"projects/{project_id}/locations/global"
                from google.cloud import translate_v3
                request = translate_v3.TranslateTextRequest(
                    parent=parent,
                    contents=[text],
                    mime_type="text/plain",
                    source_language_code="en",
                    target_language_code="bn"
                )
                response = client.translate_text(request=request)
                if response.translations:
                    raw_res = response.translations[0].translated_text
                    res_text = html.unescape(raw_res).strip()
                    valid, msg = TranslationValidator.validate(text, res_text)
                    if valid:
                        return res_text
                    else:
                        logger.warning(f"Google Translation validation failed (attempt {attempt+1}): {msg}")
            except (FileNotFoundError, ValueError) as e:
                logger.error(f"Google configuration error: {e}")
                raise e
            except Exception as e:
                err_str = str(e)
                if "PermissionDenied" in err_str or "Unauthenticated" in err_str:
                    logger.error(f"Google authentication error: {e}")
                    raise e
                logger.error(f"Google API call failed (attempt {attempt+1}): {e}")
                time.sleep(1.0 * (attempt + 1))

        return f"[Translation Failed: {text}]"

    def translate_batch(self, paragraphs: List[ParagraphModel]) -> List[str]:
        if not paragraphs:
            return []

        contents = [p.text for p in paragraphs]

        for attempt in range(settings.retry_count):
            try:
                client, project_id = self._get_client()
                parent = f"projects/{project_id}/locations/global"
                from google.cloud import translate_v3
                request = translate_v3.TranslateTextRequest(
                    parent=parent,
                    contents=contents,
                    mime_type="text/plain",
                    source_language_code="en",
                    target_language_code="bn"
                )
                response = client.translate_text(request=request)

                if response.translations and len(response.translations) == len(paragraphs):
                    translated = []
                    for p, trans in zip(paragraphs, response.translations):
                        res_text = html.unescape(trans.translated_text).strip()
                        valid, _ = TranslationValidator.validate(p.text, res_text)
                        if valid:
                            translated.append(res_text)
                        else:
                            translated.append(self.translate_paragraph(p.text, p.is_heading))
                    return translated
            except (FileNotFoundError, ValueError) as e:
                logger.error(f"Google configuration error: {e}")
                raise e
            except Exception as e:
                err_str = str(e)
                if "PermissionDenied" in err_str or "Unauthenticated" in err_str:
                    logger.error(f"Google authentication error: {e}")
                    raise e
                logger.error(f"Batch Google translation failed (attempt {attempt+1}): {e}")
                time.sleep(1.0 * (attempt + 1))

        return [self.translate_paragraph(p.text, p.is_heading) for p in paragraphs]
