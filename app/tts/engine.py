"""Single production engine: pinned Qwen3-TTS Base, local default ICL cloning."""
import hashlib
import importlib.metadata as md
import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..config import CODE_REVISION, MODEL_REPO, MODEL_REVISION, ROOT
from ..projects import file_hash


@dataclass
class AudioResult:
    samples: np.ndarray
    sample_rate: int
    metrics: dict


def local_snapshot(settings, verify=True):
    receipt = json.loads((ROOT / "docs/qwen-download.json").read_text(encoding="utf-8"))
    if receipt["repo"] != MODEL_REPO or receipt["revision"] != MODEL_REVISION or receipt["code_revision"] != CODE_REVISION:
        raise RuntimeError("Qwen asset receipt differs from the approved revision.")
    folder = settings.qwen_model_dir
    if folder is None:
        from huggingface_hub import snapshot_download
        folder = Path(snapshot_download(MODEL_REPO, revision=MODEL_REVISION, local_files_only=True,
            allow_patterns=[x["name"] for x in receipt["files"]], cache_dir=str(settings.cache_root / "hub")))
    folder = Path(folder)
    for item in receipt["files"]:
        path = folder / item["name"]
        if not path.is_file() or path.stat().st_size != item["bytes"]:
            raise RuntimeError("Missing pinned Qwen asset: " + item["name"] + ". Run setup.bat.")
        if verify and file_hash(path) != item["sha256"]:
            raise RuntimeError("Qwen model checksum mismatch: " + item["name"])
    return folder


def verify_code():
    dist = md.distribution("qwen-tts")
    if dist.version != "0.1.1":
        raise RuntimeError("Qwen code version changed. Restore requirements.txt in .venv-qwen3.")
    receipt = json.loads((ROOT / "docs/qwen-download.json").read_text(encoding="utf-8"))
    package = Path(dist.locate_file("qwen_tts"))
    for name, expected in receipt["code_files"].items():
        path = package / name
        data = path.read_bytes() if path.is_file() else b""
        if name.endswith(".py"):
            data = data.replace(b"\r\n", b"\n")
        if not path.is_file() or hashlib.sha256(data).hexdigest() != expected:
            raise RuntimeError("Qwen code checksum mismatch: " + name)


class QwenEngine:
    def __init__(self, settings):
        self.settings = settings
        self.model = None
        self.prepared = False
        self.prompt_key = None
        self.prompt = None

    def prepare_runtime(self):
        if self.prepared:
            return
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        os.environ.setdefault("HF_HOME", str(self.settings.cache_root))
        import scipy.linalg
        import scipy.signal
        import torch
        import torchaudio
        import librosa
        verify_code()
        from qwen_tts import Qwen3TTSModel
        torch.set_num_threads(4)
        librosa.resample(np.zeros(480, dtype=np.float32), orig_sr=48000, target_sr=24000)
        self.prepared = True

    @property
    def loaded(self):
        return self.model is not None

    @property
    def gpu_available(self):
        import torch
        return torch.cuda.is_available()

    def load(self):
        if self.model is not None:
            return
        self.prepare_runtime()
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("NVIDIA CUDA is unavailable. Run check.bat before generating.")
        if torch.cuda.mem_get_info()[0] < 6 * 1024**3:
            raise RuntimeError("Qwen needs at least 6 GiB free GPU memory before loading. Close other GPU workloads and retry.")
        from qwen_tts import Qwen3TTSModel
        self.model = Qwen3TTSModel.from_pretrained(local_snapshot(self.settings),
            device_map="cuda:0", dtype=torch.bfloat16, attn_implementation="sdpa", local_files_only=True)

    def synthesize(self, text, narrator_reference, options):
        self.load()
        import torch
        if torch.cuda.mem_get_info()[0] < 1024**3:
            raise RuntimeError("Insufficient free GPU memory for the next section. Previous audio is preserved.")
        parameters = dict(options)
        seed = parameters.pop("seed")
        transcript = parameters.pop("reference_text", "")
        language = parameters.pop("language", "English")
        x_vector_only = parameters.pop("x_vector_only_mode", False)
        if language != "English" or x_vector_only:
            raise ValueError("Only approved English ICL voice cloning is supported.")
        if not transcript.strip():
            raise ValueError("A confirmed reference transcript is required for Qwen voice cloning.")
        if parameters.get("non_streaming_mode") is not False:
            raise ValueError("Only approved default ICL conditioning is supported.")
        key = (file_hash(narrator_reference), hashlib.sha256(transcript.encode()).hexdigest())
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        try:
            with torch.random.fork_rng(devices=[torch.cuda.current_device()]):
                torch.manual_seed(seed)
                random.seed(seed)
                np.random.seed(seed)
                with torch.inference_mode():
                    if key != self.prompt_key:
                        self.prompt = self.model.create_voice_clone_prompt(ref_audio=str(narrator_reference),
                            ref_text=transcript, x_vector_only_mode=False)
                        self.prompt_key = key
                    # Public API returns decoded arrays; count generated frames to reject a cap hit.
                    generate = self.model.model.generate
                    lengths = []
                    def measured(*args, **kwargs):
                        answer = generate(*args, **kwargs)
                        lengths[:] = [int(c.shape[0]) for c in answer[0]]
                        return answer
                    self.model.model.generate = measured
                    try:
                        waves, sr = self.model.generate_voice_clone(text=text, language="English",
                            voice_clone_prompt=self.prompt, **parameters)
                    finally:
                        self.model.model.generate = generate
                    if not lengths or any(n >= parameters["max_new_tokens"] - 1 for n in lengths):
                        raise RuntimeError("Qwen reached its generation limit; the take was not saved. Previous audio remains intact.")
                torch.cuda.synchronize()
            return AudioResult(np.asarray(waves[0], dtype=np.float32).squeeze(), sr,
                {"generation_seconds": time.perf_counter()-started,
                 "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                 "peak_reserved_bytes": torch.cuda.max_memory_reserved(), "codec_frames": lengths,
                 "dtype": "bfloat16", "attention": "sdpa", "language": "English", "x_vector_only_mode": False})
        except torch.cuda.OutOfMemoryError as error:
            self.prompt = self.prompt_key = None
            torch.cuda.empty_cache()
            raise RuntimeError("GPU memory was exhausted. Previous recordings are preserved; close other GPU applications before retrying.") from error
