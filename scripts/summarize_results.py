"""Validate WAV artifacts and preserve compact, measured benchmark results in docs."""
import hashlib
import json
from pathlib import Path
import numpy as np
import soundfile as sf

root = Path(__file__).resolve().parents[1]
reports = []
for path in sorted((root / "benchmarks/results").glob("*/*.json")):
    d = json.loads(path.read_text(encoding="utf-8"))
    if d.get("model") not in ("kokoro", "chatterbox", "turbo"):
        continue  # Reference consent/inspection records are not benchmark cases.
    if d.get("status") == "ok":
        audio, sr = sf.read(root / d["file"], dtype="float32")
        assert sr == d["sample_rate"]
        assert np.isfinite(audio).all() and len(audio) > 0
        assert abs(len(audio) / sr - d["audio_seconds"]) < 1 / sr
        assert hashlib.sha256((root / d["file"]).read_bytes()).hexdigest() == d["audio_sha256"]
        assert abs(sum(s["duration_seconds"] for s in d["segments"]) - d["audio_seconds"]) < .001
        d["validated_pcm_sha256"] = hashlib.sha256(audio.astype("<f4").tobytes()).hexdigest()
        d["wav_validation"] = "pass: finite, decodable, sample rate, duration, file hash, segment duration sum"
    reports.append(d)
for case in ("neutral", "documentary", "pronunciation", "long", "restart"):
    comparable = [r for r in reports if r.get("case") == case and r.get("status") == "ok"]
    assert len({r["text_sha256"] for r in comparable}) <= 1, f"Different scripts for {case}"
    assert len({tuple(s["text"] for s in r["segments"]) for r in comparable}) <= 1, f"Different chunks for {case}"
    refs = {r["reference_sha256"] for r in comparable if r.get("reference_sha256")}
    assert len(refs) <= 1, f"Different cloning references for {case}"
restart = {}
for model in ("kokoro", "chatterbox", "turbo"):
    a = next((r for r in reports if r["model"] == model and r.get("case") == "neutral" and r.get("status") == "ok"), None)
    b = next((r for r in reports if r["model"] == model and r.get("case") == "restart" and r.get("status") == "ok"), None)
    if a and b:
        restart[model] = {"process_a": a["pid"], "process_b": b["pid"], "different_processes": a["pid"] != b["pid"],
                          "identical_decoded_pcm": a["validated_pcm_sha256"] == b["validated_pcm_sha256"],
                          "listening_score": None}
output = {"reports": reports, "restart_comparison": restart, "notes": [
    "Peak allocated/reserved are PyTorch CUDA allocator statistics; driver/context and other GPU allocations are excluded.",
    "Generation seconds includes shared chunk text processing and reference preparation when supplied; model load is separate.",
    "One measured run per case; timings are observations, not statistical confidence intervals.",
    "Numerical checks do not establish naturalness, correct pronunciation, or speaker consent."]}
(root / "docs/benchmark-results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
print(json.dumps([{k:r.get(k) for k in ("model", "case", "status", "audio_seconds", "generation_seconds", "load_seconds", "peak_allocated_bytes", "peak_reserved_bytes")} for r in reports], indent=2))
print(json.dumps(restart, indent=2))
