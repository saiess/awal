"""The sole production TTS implementation: pinned English Chatterbox Turbo."""
import importlib.metadata as md
import json
import os
import time
from dataclasses import dataclass

import numpy as np

from ..config import CODE_REVISION, MODEL_REPO, MODEL_REVISION, ROOT
from ..projects import file_hash


@dataclass
class AudioResult:
    samples: np.ndarray
    sample_rate: int
    metrics: dict


class TurboEngine:
    def __init__(self, settings):
        self.settings = settings
        self.model = None
        self.prepared = False

    def prepare_runtime(self):
        """Initialize native DLLs on the server main thread; keep weights lazy.

        On this Windows stack, first importing SciPy/OpenBLAS inside the GPU
        worker can stall in DLL initialization. Import code before accepting work.
        """
        if self.prepared:
            return
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ.setdefault("HF_HOME", str(self.settings.cache_root))
        import scipy.linalg
        import scipy.signal
        import torch
        import torchaudio
        from chatterbox.tts_turbo import ChatterboxTurboTTS
        import librosa
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
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ.setdefault("HF_HOME", str(self.settings.cache_root))
        import torch
        if not torch.cuda.is_available():
            raise RuntimeError("NVIDIA CUDA is unavailable. Run check.bat before generating.")
        dist = md.distribution("chatterbox-tts")
        origin = json.loads(dist.read_text("direct_url.json") or "{}")
        if dist.version != "0.1.7" or origin.get("vcs_info", {}).get("commit_id") != CODE_REVISION:
            raise RuntimeError("Chatterbox code differs from the approved revision. Restore requirements.txt.")
        from huggingface_hub import snapshot_download
        from chatterbox.tts_turbo import ChatterboxTurboTTS
        receipt = json.loads((ROOT / "docs/turbo-download.json").read_text())
        folder = snapshot_download(MODEL_REPO, revision=MODEL_REVISION, local_files_only=True,
                                   allow_patterns=[item["name"] for item in receipt["files"]],
                                   cache_dir=str(self.settings.cache_root / "hub"))
        from pathlib import Path
        for item in receipt["files"]:
            if file_hash(Path(folder) / item["name"]) != item["sha256"]:
                raise RuntimeError("Cached Turbo model checksum failed. Restore the pinned official snapshot.")
        self.model = ChatterboxTurboTTS.from_local(folder, device="cuda")

    def synthesize(self, text, narrator_reference, options):
        self.load()
        import torch
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        parameters = dict(options)
        seed = parameters.pop("seed", 1234)
        # Reference is supplied for every section; no mutable bundled speaker is used.
        with torch.random.fork_rng(devices=[torch.cuda.current_device()]):
            torch.manual_seed(seed)
            with torch.inference_mode():
                result = self.model.generate(text, audio_prompt_path=str(narrator_reference), **parameters)
            samples = result.detach().cpu().numpy().squeeze()
            torch.cuda.synchronize()
        return AudioResult(np.asarray(samples, dtype=np.float32), self.model.sr,
                           {"generation_seconds": time.perf_counter()-started,
                            "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                            "peak_reserved_bytes": torch.cuda.max_memory_reserved()})
