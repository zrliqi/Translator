import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from app.translation.groq_translator import GroqTranslator
from app.translation.translation_cache import TranslationCache
from app.processing.worker import TranslationWorker
from app.document.paragraph_model import ParagraphModel

class TestGroqTranslator(unittest.TestCase):
    def test_initialization(self):
        translator = GroqTranslator(api_key="gsk_dummy_123", model="llama-3.3-70b-versatile")
        self.assertEqual(translator.api_key, "gsk_dummy_123")
        self.assertEqual(translator.model, "llama-3.3-70b-versatile")

    def test_missing_api_key(self):
        with patch.dict("os.environ", {}, clear=True):
            translator = GroqTranslator(api_key="")
            success, msg = translator.validate_connection()
            self.assertFalse(success)
            self.assertIn("GROQ_API_KEY was not found", msg)

    @patch("app.translation.groq_translator.Groq")
    def test_validate_connection_success(self, mock_groq_class):
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "Pong"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        translator = GroqTranslator(api_key="gsk_dummy_123", model="llama-3.3-70b-versatile")
        success, msg = translator.validate_connection()

        self.assertTrue(success)
        self.assertIn("Successfully connected", msg)

    @patch("app.translation.groq_translator.Groq")
    def test_translate_paragraph(self, mock_groq_class):
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = "দ্য গিফট অব দ্য ম্যাজাই"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        translator = GroqTranslator(api_key="gsk_dummy_123", model="llama-3.3-70b-versatile")
        res = translator.translate_paragraph("The Gift of the Magi")

        self.assertEqual(res, "দ্য গিফট অব দ্য ম্যাজাই")
        mock_client.chat.completions.create.assert_called_once()

    @patch("app.translation.groq_translator.Groq")
    def test_translate_batch(self, mock_groq_class):
        mock_client = MagicMock()
        mock_groq_class.return_value = mock_client

        mock_choice = MagicMock()
        mock_choice.message.content = '{"items": [{"id": "p1", "translated_text": "শিরোনাম"}, {"id": "p2", "translated_text": "এক ডলার এবং সাতাশি সেন্ট।"}]}'
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        translator = GroqTranslator(api_key="gsk_dummy_123", model="llama-3.3-70b-versatile")
        paras = [
            ParagraphModel(id="p1", text="Heading", is_heading=True),
            ParagraphModel(id="p2", text="One dollar and eighty-seven cents.")
        ]
        results = translator.translate_batch(paras)

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0], "শিরোনাম")
        self.assertEqual(results[1], "এক ডলার এবং সাতাশি সেন্ট।")

    def test_cache_provider_separation(self):
        cache = TranslationCache()

        source_text = "The Gift of the Magi"
        groq_res = "দ্য গিফট অব দ্য ম্যাজাই (Groq)"
        openai_res = "দ্য গিফট অব দ্য ম্যাজাই (OpenAI)"

        cache.put(source_text, groq_res, model_name="groq-llama-3.3-70b-versatile")
        cache.put(source_text, openai_res, model_name="gpt-4o-mini")

        self.assertEqual(cache.get(source_text, model_name="groq-llama-3.3-70b-versatile"), groq_res)
        self.assertEqual(cache.get(source_text, model_name="gpt-4o-mini"), openai_res)

    def test_worker_groq_provider_selection(self):
        worker_groq = TranslationWorker(
            input_path=Path("test_bengali.pdf"),
            provider="groq",
            model_name="llama-3.3-70b-versatile"
        )
        self.assertEqual(worker_groq.provider, "groq")
        self.assertEqual(worker_groq.model_name, "llama-3.3-70b-versatile")

if __name__ == "__main__":
    unittest.main()
