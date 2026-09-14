import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from app.translation.model_manager import ModelManager
from app.translation.local_translator import LocalTranslator
from app.document.paragraph_model import ParagraphModel

class TestModelManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.models_dir = Path(self.temp_dir.name)
        self.mm = ModelManager(model_repo="facebook/nllb-200-distilled-600M", models_dir=self.models_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_is_model_installed_false_when_empty(self):
        self.assertFalse(self.mm.is_model_installed())
        self.assertEqual(self.mm.get_model_size_mb(), 0.0)

    def test_is_model_installed_true_when_files_present(self):
        model_path = self.models_dir / "nllb-200-distilled-600M"
        model_path.mkdir(parents=True, exist_ok=True)
        (model_path / "config.json").write_text("{}")
        (model_path / "model.safetensors").write_bytes(b"dummy weights data")

        self.assertTrue(self.mm.is_model_installed())
        self.assertGreater(self.mm.get_model_size_mb(), 0.0)

    def test_resolve_device(self):
        dev_cpu = self.mm.resolve_device("cpu")
        self.assertEqual(dev_cpu, "cpu")

        dev_auto = self.mm.resolve_device("auto")
        self.assertIn(dev_auto, ["cpu", "cuda"])

    def test_hardware_info(self):
        info = self.mm.get_system_hardware_info()
        self.assertIn("cuda_available", info)
        self.assertIn("device_name", info)

class TestLocalTranslator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.models_dir = Path(self.temp_dir.name)
        self.mm = ModelManager(model_repo="facebook/nllb-200-distilled-600M", models_dir=self.models_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("app.translation.model_manager.ModelManager.load_model")
    def test_translate_paragraph_mocked_model(self, mock_load_model):
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()

        mock_tokenizer.convert_tokens_to_ids.return_value = 1234
        mock_tokenizer.lang_code_to_id = {"ben_Beng": 1234}
        mock_tokenizer.return_value = {"input_ids": MagicMock()}
        mock_tokenizer.batch_decode.return_value = ["দ্য গিফট অব দ্য ম্যাজাই"]

        mock_load_model.return_value = (mock_tokenizer, mock_model, "cpu")

        lt = LocalTranslator(model_manager=self.mm, preferred_device="cpu")
        translated = lt.translate_paragraph("The Gift of the Magi")

        self.assertEqual(translated, "দ্য গিফট অব দ্য ম্যাজাই")

    @patch("app.translation.model_manager.ModelManager.load_model")
    def test_translate_batch_mocked_model(self, mock_load_model):
        mock_tokenizer = MagicMock()
        mock_model = MagicMock()

        mock_tokenizer.convert_tokens_to_ids.return_value = 1234
        mock_tokenizer.lang_code_to_id = {"ben_Beng": 1234}
        mock_tokenizer.return_value = {"input_ids": MagicMock()}
        mock_tokenizer.batch_decode.return_value = ["এক ডলার এবং সাতাশি সেন্ট।"]

        mock_load_model.return_value = (mock_tokenizer, mock_model, "cpu")

        lt = LocalTranslator(model_manager=self.mm, preferred_device="cpu")
        paras = [
            ParagraphModel(id="p1", text="One dollar and eighty-seven cents.")
        ]
        results = lt.translate_batch(paras)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], "এক ডলার এবং সাতাশি সেন্ট।")

if __name__ == "__main__":
    unittest.main()
