import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE_ID = "qwen3-tts-0.6b-base"
MODEL_REPO = "Qwen/Qwen3-TTS-12Hz-0.6B-Base"
MODEL_REVISION = "5d83992436eae1d760afd27aff78a71d676296fc"
CODE_REVISION = "022e286b98fbec7e1e916cb940cdf532cd9f488e"
SAMPLE_RATE = 24000


def model_cache():
    """Installer-selected persistent cache; preserve existing manual defaults."""
    if os.environ.get("HF_HOME"):
        return Path(os.environ["HF_HOME"])
    config = ROOT / ".local-config.json"
    if config.exists():
        import json
        record = json.loads(config.read_text(encoding="utf-8"))
        path = Path(record["cache_root"])
        if record.get("schema_version") != 1 or not path.is_absolute():
            raise ValueError("Invalid .local-config.json; rerun setup.bat.")
        return path
    return Path(tempfile.gettempdir()) / "local-youtube-tts-cache/huggingface"

PARAMETERS = {"seed": 1234, "do_sample": True, "temperature": .9, "repetition_penalty": 1.05,
              "top_p": 1.0, "top_k": 50, "subtalker_dosample": True,
              "subtalker_top_k": 50, "subtalker_top_p": 1.0, "subtalker_temperature": .9,
              "max_new_tokens": 8192, "non_streaming_mode": False,
              "language": "English", "x_vector_only_mode": False}


def qwen_model_dir():
    if os.environ.get("AWAL_QWEN_MODEL"):
        return Path(os.environ["AWAL_QWEN_MODEL"])
    config = ROOT / ".local-config.json"
    if config.exists():
        import json
        value = json.loads(config.read_text(encoding="utf-8")).get("qwen_model_dir")
        if value:
            path = Path(value)
            if not path.is_absolute():
                raise ValueError("qwen_model_dir must be an absolute local path.")
            return path
    return None


@dataclass(frozen=True)
class Settings:
    data_root: Path = field(default_factory=lambda: Path(os.environ.get("TTS_DATA_DIR", ROOT / "data")))
    cache_root: Path = field(default_factory=model_cache)
    segment_chars: int = 600
    qwen_model_dir: Path | None = field(default_factory=qwen_model_dir)
    max_script_chars: int = 100_000
    max_upload_bytes: int = 15 * 1024 * 1024
    default_speed: float = 1.10
