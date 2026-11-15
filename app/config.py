import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE_ID = "chatterbox-turbo"
MODEL_REPO = "ResembleAI/chatterbox-turbo"
MODEL_REVISION = "749d1c1a46eb10492095d68fbcf55691ccf137cd"
CODE_REVISION = "5de7a54aa4e5e2baadb0182dde554908b48b85c2"
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

PARAMETERS = {"seed": 1234, "temperature": .8, "repetition_penalty": 1.2,
              "top_p": .95, "top_k": 1000, "cfg_weight": 0.0, "exaggeration": 0.0,
              "norm_loudness": True}


@dataclass(frozen=True)
class Settings:
    data_root: Path = field(default_factory=lambda: Path(os.environ.get("TTS_DATA_DIR", ROOT / "data")))
    cache_root: Path = field(default_factory=model_cache)
    segment_chars: int = 350
    max_script_chars: int = 100_000
    max_upload_bytes: int = 15 * 1024 * 1024
    default_speed: float = 1.10
