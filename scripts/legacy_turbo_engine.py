"""Historical benchmark support only; never imported by the production application."""
import importlib.metadata as md
import json
import os
import time
from dataclasses import dataclass

import numpy as np

from app.config import ROOT
CODE_REVISION = "5de7a54aa4e5e2baadb0182dde554908b48b85c2"
MODEL_REPO = "ResembleAI/chatterbox-turbo"
MODEL_REVISION = "749d1c1a46eb10492095d68fbcf55691ccf137cd"
PARAMETERS = {"seed":1234,"temperature":.8,"repetition_penalty":1.2,"top_p":.95,"top_k":1000,"cfg_weight":0.0,"exaggeration":0.0,"norm_loudness":True}
from app.projects import file_hash


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


# Frozen historical segmentation; never used by the application.
"""Conservative English paragraph/sentence segmentation for the tested model."""
import re

ABBREVIATIONS = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "no", "fig", "inc"}
BOUNDARY = re.compile(r'''[.!?]+["'”’)\]]*(?:\s+|$)''')


def sentences(paragraph):
    start = 0
    for match in BOUNDARY.finditer(paragraph):
        end = match.end()
        prefix = paragraph[:match.start()+1]
        if paragraph[match.start()] == ".":
            token = prefix.split()[-1].strip('"“(‘')
            if token[:-1].lower() in ABBREVIATIONS or re.search(r"(?:[A-Za-z]\.){2,}$", token) or re.fullmatch(r"[A-Z]\.", token):
                continue
        yield paragraph[start:end].strip()
        start = end
    if paragraph[start:].strip():
        yield paragraph[start:].strip()


def segment_text(text, max_chars=350):
    if max_chars < 20:
        raise ValueError("Segment size must be at least 20 characters.")
    if not text.strip() or not any(c.isalnum() for c in text):
        raise ValueError("Enter a script containing letters or numbers.")
    result = []
    for paragraph in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        current = ""
        for sentence in sentences(paragraph):
            pieces = []
            while len(sentence) > max_chars:
                cut = sentence.rfind(" ", 0, max_chars + 1)
                if cut <= 0:
                    cut = max_chars
                pieces.append(sentence[:cut].strip())
                sentence = sentence[cut:].strip()
            if sentence:
                pieces.append(sentence)
            for piece in pieces:
                if current and len(current) + len(piece) + 1 > max_chars:
                    result.append(current)
                    current = ""
                current = f"{current} {piece}".strip()
        if current:
            result.append(current)
    return result
