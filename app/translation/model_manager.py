import os
import shutil
import gc
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Tuple
import torch
from app.utils.paths import get_models_dir
from app.utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL_REPO = "facebook/nllb-200-distilled-600M"
DEFAULT_MODEL_NAME = "nllb-200-distilled-600M"

class ModelManager:
    """
    Manages local AI model detection, disk space checking, downloading with progress callbacks,
    loading, device placement (Auto/CPU/CUDA), and resource cleanup/unloading.
    """
    def __init__(self, model_repo: str = DEFAULT_MODEL_REPO, models_dir: Optional[Path] = None):
        self.model_repo = model_repo
        self.models_dir = Path(models_dir) if models_dir else get_models_dir()
        self.model_folder_name = self.model_repo.split("/")[-1]
        self.local_model_path = self.models_dir / self.model_folder_name

        self._tokenizer = None
        self._model = None
        self._current_device = None

    def is_model_installed(self) -> bool:
        """Check if the model files exist locally in the designated folder."""
        if not self.local_model_path.exists() or not self.local_model_path.is_dir():
            return False

        required_files = ["config.json"]
        for f in required_files:
            if not (self.local_model_path / f).exists():
                return False

        weights_exist = (
            (self.local_model_path / "model.safetensors").exists() or
            (self.local_model_path / "pytorch_model.bin").exists() or
            any(self.local_model_path.glob("*.safetensors")) or
            any(self.local_model_path.glob("*.bin"))
        )
        return weights_exist

    def get_model_size_mb(self) -> float:
        """Return total size of local model files in megabytes."""
        if not self.local_model_path.exists():
            return 0.0
        total_bytes = sum(f.stat().st_size for f in self.local_model_path.glob("**/*") if f.is_file())
        return total_bytes / (1024 * 1024)

    def get_available_disk_space_mb(self) -> float:
        """Return free disk space in MB for the models directory drive."""
        try:
            usage = shutil.disk_usage(self.models_dir)
            return usage.free / (1024 * 1024)
        except Exception as e:
            logger.warning(f"Could not retrieve disk space info: {e}")
            return 100000.0  # Fallback optimistic estimate if disk_usage fails

    def resolve_device(self, preferred_device: str = "auto") -> str:
        """
        Resolve 'auto', 'cpu', 'cuda' into actual device string ('cuda' or 'cpu').
        Falls back to 'cpu' if 'cuda' is requested but unavailable.
        """
        pref = (preferred_device or "auto").lower()
        cuda_available = torch.cuda.is_available()

        if pref == "cuda":
            if cuda_available:
                return "cuda"
            else:
                logger.warning("CUDA requested but not available on this system. Falling back to CPU.")
                return "cpu"
        elif pref == "cpu":
            return "cpu"
        else:  # auto
            return "cuda" if cuda_available else "cpu"

    def get_system_hardware_info(self) -> Dict[str, Any]:
        """Return hardware details including CPU, CUDA availability, RAM, VRAM."""
        cuda_avail = torch.cuda.is_available()
        info = {
            "cuda_available": cuda_avail,
            "device_count": torch.cuda.device_count() if cuda_avail else 0,
            "device_name": torch.cuda.get_device_name(0) if cuda_avail else "CPU",
            "vram_mb": 0,
            "ram_mb": 0
        }
        if cuda_avail:
            try:
                info["vram_mb"] = torch.cuda.get_device_properties(0).total_memory / (1024 * 1024)
            except Exception:
                pass
        try:
            import psutil
            info["ram_mb"] = psutil.virtual_memory().total / (1024 * 1024)
        except Exception:
            pass
        return info

    def download_model(
        self,
        progress_callback: Optional[Callable[[int, str], None]] = None,
        cancel_checker: Optional[Callable[[], bool]] = None
    ) -> bool:
        """
        Download the model from Hugging Face Hub into local_model_path with progress reporting.
        """
        avail_mb = self.get_available_disk_space_mb()
        if avail_mb < 3000:
            raise RuntimeError(f"Insufficient disk space for model download. Required: ~3000 MB, Available: {avail_mb:.1f} MB")

        if progress_callback:
            progress_callback(5, f"Starting model download: {self.model_repo}...")

        from huggingface_hub import snapshot_download
        self.local_model_path.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(15, "Downloading weights and tokenizer files...")

        try:
            snapshot_download(
                repo_id=self.model_repo,
                local_dir=str(self.local_model_path),
                local_dir_use_symlinks=False
            )
            if progress_callback:
                progress_callback(100, f"Model downloaded successfully ({self.get_model_size_mb():.1f} MB).")
            return True
        except Exception as e:
            logger.error(f"Failed to download model: {e}")
            if progress_callback:
                progress_callback(0, f"Download failed: {e}")
            raise RuntimeError(f"Model download failed: {e}")

    def load_model(self, preferred_device: str = "auto") -> Tuple[Any, Any, str]:
        """
        Loads tokenizer and model, placing model on target device.
        Returns (tokenizer, model, actual_device).
        """
        if self._tokenizer is not None and self._model is not None:
            return self._tokenizer, self._model, self._current_device

        if not self.is_model_installed():
            raise FileNotFoundError(f"Local model not found at {self.local_model_path}. Please download the model first.")

        device = self.resolve_device(preferred_device)
        logger.info(f"Loading local translation model from {self.local_model_path} on device {device}...")

        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

        model_path_str = str(self.local_model_path)
        tokenizer = AutoTokenizer.from_pretrained(model_path_str, src_lang="eng_Latn")

        try:
            model = AutoModelForSeq2SeqLM.from_pretrained(model_path_str)
            model.to(device)
            model.eval()
        except Exception as e:
            if device == "cuda":
                logger.warning(f"Failed to load model on CUDA ({e}). Falling back to CPU...")
                device = "cpu"
                model = AutoModelForSeq2SeqLM.from_pretrained(model_path_str)
                model.to(device)
                model.eval()
            else:
                raise e

        self._tokenizer = tokenizer
        self._model = model
        self._current_device = device

        logger.info(f"Model successfully loaded on {device}.")
        return self._tokenizer, self._model, self._current_device

    def unload_model(self):
        """Unload model and tokenizer to free RAM/VRAM."""
        if self._model is not None or self._tokenizer is not None:
            logger.info("Unloading local translation model and freeing RAM/VRAM...")
            self._model = None
            self._tokenizer = None
            self._current_device = None
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
