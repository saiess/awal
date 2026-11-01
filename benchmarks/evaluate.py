"""Small, offline benchmark. Run again in a new process for restart comparison."""
import argparse
import hashlib
import importlib.metadata as md
import json
import os
import re
import random
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path(tempfile.gettempdir()) / "local-youtube-tts-cache"
os.environ.setdefault("HF_HOME", str(CACHE / "huggingface"))
os.environ.setdefault("TORCH_HOME", str(CACHE / "torch"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"


def chunks(text, limit=350):
    # Shared conservative sentence chunks, with no word or punctuation edits.
    result, current = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", text.strip()):
        if current and len(current) + len(sentence) + 1 > limit:
            result.append(current)
            current = ""
        current = (current + " " + sentence).strip()
    if current:
        result.append(current)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", choices=["kokoro", "chatterbox", "turbo"], required=True)
    p.add_argument("--cases", nargs="+", choices=["smoke", "neutral", "documentary", "pronunciation", "long", "restart"], default=["neutral", "documentary", "pronunciation", "long"])
    p.add_argument("--reference", type=Path)
    p.add_argument("--load-only", action="store_true", help="Check GPU loading without synthesizing or using a speaker")
    p.add_argument("--consent-record", type=Path, help="JSON: identity, rights_confirmed=true, scope; required for cloning")
    args = p.parse_args()
    if args.model != "kokoro" and not args.load_only:
        if not args.reference or not args.consent_record:
            p.error("A consented reference and provenance record are required; no bundled speaker assumed cleared.")
        consent = json.loads(args.consent_record.read_text(encoding="utf-8"))
        if consent.get("rights_confirmed") is not True or not consent.get("identity") or not consent.get("scope"):
            p.error("Consent record must identify the recording and confirm cloning/publication rights.")
    import numpy as np
    import soundfile as sf
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required: no CPU fallback in this GPU benchmark")
    torch.manual_seed(1234)
    np.random.seed(1234)
    random.seed(1234)
    out = ROOT / "benchmarks" / "results" / args.model
    out.mkdir(parents=True, exist_ok=True)
    sources = json.loads((ROOT / "docs/licenses/revisions.json").read_text())
    model_revision = sources["models"][args.model]["revision"]
    from huggingface_hub import snapshot_download
    # Offline only: explicit download step pins exact bytes before inference.
    model_dir = Path(snapshot_download(sources["models"][args.model]["repo"], revision=model_revision, local_files_only=True))
    torch.cuda.reset_peak_memory_stats()
    load_start = time.perf_counter()
    if args.model == "kokoro":
        from kokoro import KModel, KPipeline
        model = KModel(config=str(model_dir / "config.json"), model=str(model_dir / "kokoro-v1_0.pth")).to("cuda").eval()
        pipeline = KPipeline(lang_code="a", model=model, device="cuda")
        voice = torch.load(model_dir / "voices/af_heart.pt", weights_only=True, map_location="cpu")
        sr = 24000
        def synth(text):
            return np.concatenate([r.audio.cpu().numpy() for r in pipeline(text, voice=voice, speed=1)])
    else:
        if args.model == "chatterbox":
            from chatterbox.tts import ChatterboxTTS as Engine
        else:
            from chatterbox.tts_turbo import ChatterboxTurboTTS as Engine
        model = Engine.from_local(model_dir, device="cuda")
        sr = model.sr
        if not args.load_only:
            ref, ref_sr = sf.read(args.reference)
            if not 10 <= len(ref) / ref_sr <= 30:
                raise ValueError("Reference must be 10–30 seconds")
        def synth(text):
            return model.generate(text, audio_prompt_path=str(args.reference)).detach().cpu().numpy().reshape(-1)
    torch.cuda.synchronize()
    load_seconds = time.perf_counter() - load_start
    if args.load_only:
        report = {"model": args.model, "revision": model_revision, "status": "loaded_only_no_speech_generated",
                  "device": torch.cuda.get_device_name(), "load_seconds": load_seconds,
                  "peak_allocated_bytes": torch.cuda.max_memory_allocated(), "peak_reserved_bytes": torch.cuda.max_memory_reserved()}
        (out / "load-only.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0
    base = {"model": args.model, "revision": model_revision, "pid": os.getpid(),
            "code_revision_reviewed": sources["code"]["kokoro" if args.model == "kokoro" else "chatterbox"]["revision"],
            "package_versions": {n: md.version(n) for n in ("torch", "torchaudio", "kokoro" if args.model == "kokoro" else "chatterbox-tts")},
            "started_at": datetime.now(timezone.utc).isoformat(), "seed": 1234,
            "load_seconds": load_seconds, "sample_rate": sr, "device": torch.cuda.get_device_name(),
            "voice": "af_heart preset (not a unique clone)" if args.model == "kokoro" else consent,
            "reference_sha256": hashlib.sha256(args.reference.read_bytes()).hexdigest() if args.reference else None,
            "cache": str(CACHE), "python": sys.version}
    base["parameters"] = ({"voice": "af_heart", "speed": 1} if args.model == "kokoro" else
                          {"temperature": 0.8, "repetition_penalty": 1.2, "cfg_weight": 0.5 if args.model == "chatterbox" else 0.0,
                           "exaggeration": 0.5 if args.model == "chatterbox" else 0.0, "upstream_other_defaults": True})
    for case in args.cases:
        report = dict(base, case=case, status="failed", segments=[])
        try:
            text = (ROOT / "benchmarks/scripts" / (("neutral" if case == "restart" else case) + ".txt")).read_text(encoding="utf-8")
            report["text_sha256"] = hashlib.sha256(text.encode()).hexdigest()
            torch.cuda.reset_peak_memory_stats()
            arrays, generation = [], 0.0
            segment_dir = out / (case + "-segments")
            segment_dir.mkdir(exist_ok=True)
            started = time.perf_counter()
            for i, chunk in enumerate(chunks(text)):
                torch.cuda.synchronize()
                t = time.perf_counter()
                with torch.inference_mode():
                    audio = synth(chunk)
                torch.cuda.synchronize()
                elapsed = time.perf_counter() - t
                generation += elapsed
                if not len(audio) or not np.isfinite(audio).all() or np.max(np.abs(audio)) < 1e-5:
                    raise ValueError("Empty, nonfinite, or silent output")
                path = segment_dir / f"{i:03}.wav"
                sf.write(path, audio, sr, subtype="FLOAT")
                arrays.append(audio)
                report["segments"].append({"text": chunk, "generation_seconds": elapsed, "duration_seconds": len(audio) / sr, "peak": float(np.max(np.abs(audio))), "file": str(path.relative_to(ROOT))})
                print(f"{args.model} {case} segment {i}: {elapsed:.2f}s / {len(audio)/sr:.2f}s audio", flush=True)
            combined = np.concatenate(arrays)  # No normalization or artificial pauses.
            target = out / (case + ".wav")
            sf.write(target, combined, sr, subtype="FLOAT")
            duration = len(combined) / sr
            report.update(status="ok", generation_seconds=generation, wall_seconds=time.perf_counter()-started,
                          audio_seconds=duration, real_time_factor=generation/duration,
                          peak_allocated_bytes=torch.cuda.max_memory_allocated(), peak_reserved_bytes=torch.cuda.max_memory_reserved(),
                          file=str(target.relative_to(ROOT)), audio_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                          pcm_float32_sha256=hashlib.sha256(combined.astype("<f4").tobytes()).hexdigest())
        except Exception:
            report["error"] = traceback.format_exc()
            print(report["error"], flush=True)
        (out / (case + ".json")).write_text(json.dumps(report, indent=2), encoding="utf-8")
        if report["status"] != "ok":
            return 1
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        folder = ROOT / "benchmarks/results"
        folder.mkdir(parents=True, exist_ok=True)
        error = traceback.format_exc()
        (folder / "last-initialization-error.txt").write_text(error, encoding="utf-8")
        raise
