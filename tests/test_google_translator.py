import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from app.translation.google_translator import GoogleTranslator
from app.translation.translation_cache import TranslationCache
from app.processing.worker import TranslationWorker
from app.document.paragraph_model import ParagraphModel

class TestGoogleTranslator(unittest.TestCase):
    def test_initialization(self):
        translator = GoogleTranslator(project_id="test-proj-123", credentials_path="dummy.json")
        self.assertEqual(translator.project_id, "test-proj-123")
        self.assertEqual(translator.credentials_path, "dummy.json")

    def test_credential_file_not_found(self):
        translator = GoogleTranslator(project_id="test-proj", credentials_path="/path/does/not/exist/cred.json")
        success, msg = translator.validate_connection()
        self.assertFalse(success)
        self.assertIn("not found", msg.lower())

    @patch("app.translation.google_translator.GoogleTranslator._get_client")
    def test_validate_connection_success(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_trans = MagicMock()
        mock_trans.translated_text = "হ্যালো"
        mock_response.translations = [mock_trans]
        mock_client.translate_text.return_value = mock_response

        mock_get_client.return_value = (mock_client, "test-proj")

        translator = GoogleTranslator(project_id="test-proj")
        success, msg = translator.validate_connection()
        self.assertTrue(success)
        self.assertIn("successful", msg)

    @patch("app.translation.google_translator.GoogleTranslator._get_client")
    def test_translate_paragraph_single(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_trans = MagicMock()
        mock_trans.translated_text = "দ্য গিফট অব দ্য ম্যাজাই"
        mock_response.translations = [mock_trans]
        mock_client.translate_text.return_value = mock_response

        mock_get_client.return_value = (mock_client, "test-proj")

        translator = GoogleTranslator(project_id="test-proj")
        res = translator.translate_paragraph("The Gift of the Magi")

        self.assertEqual(res, "দ্য গিফট অব দ্য ম্যাজাই")
        mock_client.translate_text.assert_called_once()
        call_kwargs = mock_client.translate_text.call_args[1]
        req = call_kwargs['request']
        self.assertEqual(req.parent, "projects/test-proj/locations/global")
        self.assertEqual(req.source_language_code, "en")
        self.assertEqual(req.target_language_code, "bn")
        self.assertEqual(req.contents, ["The Gift of the Magi"])

    @patch("app.translation.google_translator.GoogleTranslator._get_client")
    def test_translate_batch(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock()

        trans1 = MagicMock()
        trans1.translated_text = "শিরোনাম"
        trans2 = MagicMock()
        trans2.translated_text = "এক ডলার এবং সাতাশি সেন্ট।"

        mock_response.translations = [trans1, trans2]
        mock_client.translate_text.return_value = mock_response

        mock_get_client.return_value = (mock_client, "test-proj")

        translator = GoogleTranslator(project_id="test-proj")
        paras = [
            ParagraphModel(id="p1", text="Heading", is_heading=True),
            ParagraphModel(id="p2", text="One dollar and eighty-seven cents.")
        ]
        results = translator.translate_batch(paras)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], "শিরোনাম")
        self.assertEqual(results[1], "এক ডলার এবং সাতাশি সেন্ট।")

    @patch("app.translation.google_translator.GoogleTranslator._get_client")
    def test_retry_on_transient_failure(self, mock_get_client):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_trans = MagicMock()
        mock_trans.translated_text = "অনুবাদ"
        mock_response.translations = [mock_trans]

        # Fail on attempt 1, succeed on attempt 2
        mock_client.translate_text.side_effect = [Exception("Network timeout"), mock_response]
        mock_get_client.return_value = (mock_client, "test-proj")

        translator = GoogleTranslator(project_id="test-proj")
        res = translator.translate_paragraph("Some English text")
        self.assertEqual(res, "অনুবাদ")
        self.assertEqual(mock_client.translate_text.call_count, 2)

    def test_cache_provider_separation(self):
        cache = TranslationCache()

        source_text = "A Cosmopolite in a Café"
        google_res = "কাফেতে একজন বিশ্বনাগরিক"
        openai_res = "ক্যাফেতে এক কসমোপলিটান"

        cache.put(source_text, google_res, model_name="google-cloud-translate")
        cache.put(source_text, openai_res, model_name="gpt-4o-mini")

        self.assertEqual(cache.get(source_text, model_name="google-cloud-translate"), google_res)
        self.assertEqual(cache.get(source_text, model_name="gpt-4o-mini"), openai_res)

    def test_worker_provider_selection(self):
        worker_google = TranslationWorker(
            input_path=Path("test_bengali.pdf"),
            provider="google",
            google_project_id="my-gcp-project"
        )
        self.assertEqual(worker_google.provider, "google")
        self.assertEqual(worker_google.google_project_id, "my-gcp-project")

        worker_openai = TranslationWorker(
            input_path=Path("test_bengali.pdf"),
            provider="openai",
            model_name="gpt-4o"
        )
        self.assertEqual(worker_openai.provider, "openai")
        self.assertEqual(worker_openai.model_name, "gpt-4o")

        worker_mock = TranslationWorker(
            input_path=Path("test_bengali.pdf"),
            provider="mock"
        )
        self.assertEqual(worker_mock.provider, "mock")

if __name__ == "__main__":
    unittest.main()
