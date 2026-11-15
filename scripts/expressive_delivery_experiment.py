"""One-off, offline, three-configuration experiment; never imported by the app.

Reuses TurboEngine, segmentation, audio verification, and the existing ignored
benchmarks/results location. Creates an exclusive run directory, never projects.
"""
import argparse
import hashlib
import inspect
import json
import os
import re
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

from app.audio import combine, convert, validate_audio, write_raw
from app.config import CODE_REVISION, MODEL_REPO, MODEL_REVISION, PARAMETERS, Settings
from app.projects import file_hash
from app.segmentation import segment_text, sentences
from app.tts.engine import TurboEngine

SCRIPT = """Before sunrise, the harbor is already at work, as a baker lifts the shutters, delivery drivers check their routes, the first fishing boats move beyond the breakwater, and a small team in the control room follows the tide, the wind, and the quiet, carefully coordinated sequence of decisions that will keep the town moving long before most residents have opened their eyes. From the waterfront, it looks almost effortless.

But what happens when the weather changes? A warning arrives, a route closes, and plans made hours earlier have to change in minutes. The team does not need every decision to be dramatic. It needs the right person to notice one small detail, ask the right question, and pass the answer along before a minor delay becomes a serious problem.

By evening, the harbor is quiet again. Most people will never see the checks, the conversations, or the careful timing behind an ordinary day. That is the surprising part: a town can depend on thousands of small decisions, even when nobody stops to count them."""


def context_sections(text):
    """Keep complete sentences and paragraph context, capped at 600 characters.

    Oversized individual sentences are rejected, not silently split or rewritten.
    This is an experiment-specific alternative; production's 350 limit stays put.
    """
    result = []
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        current = ""
        for sentence in sentences(" ".join(paragraph.split())):
            if len(sentence) > 600:
                raise ValueError("Experiment sentence exceeds the 600-character bound.")
            if current and len(current) + len(sentence) + 1 > 600:
                result.append(current)
                current = ""
            current = f"{current} {sentence}".strip()
        if current:
            result.append(current)
    return result


def hashes(paths):
    return {str(p.relative_to(ROOT)): file_hash(p) for p in sorted(paths) if p.is_file()}


def waveform_metrics(a, sr):
    """Descriptive timing/level proxies, explicitly not a naturalness score."""
    import numpy as np
    import pyloudnorm as pyln
    frame = sr // 100
    frames = a[:len(a)//frame*frame].reshape(-1, frame)
    rms = np.sqrt(np.mean(frames.astype(np.float64)**2, axis=1))
    quiet = rms < 10**(-45/20)
    edges = np.diff(np.r_[False, quiet, False].astype(int))
    runs = [(int(start), int(end)) for start, end in zip(np.flatnonzero(edges == 1), np.flatnonzero(edges == -1))]
    pauses = [(s/100, e/100) for s, e in runs if e-s >= 20 and s > 0 and e < len(quiet)]
    peak = float(np.max(np.abs(a)))
    return {"duration_seconds": len(a)/sr, "sample_peak_dbfs": float(20*np.log10(peak)),
            "samples_over_full_scale": int(np.count_nonzero(np.abs(a) > 1)),
            "integrated_lufs": float(pyln.Meter(sr).integrated_loudness(a)),
            "quiet_fraction_at_minus45_dbfs": float(np.mean(quiet)),
            "internal_quiet_runs_at_least_200ms": pauses}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New directory under benchmarks/results")
    args = parser.parse_args()
    out = args.output.resolve()
    allowed = (ROOT / "benchmarks/results").resolve()
    if not out.is_relative_to(allowed) or out == allowed:
        raise ValueError("Use a new directory under benchmarks/results.")
    # No directory or audio from another run is ever reused or overwritten.
    out.mkdir(parents=True, exist_ok=False)
    settings = Settings()
    data_paths = [p for folder in ("projects", "narrators") for p in (settings.data_root/folder).rglob("*") if p.is_file()]
    production_paths = [p for folder in ("app", "frontend/src") for p in (ROOT/folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    before_data, before_code = hashes(data_paths), hashes(production_paths)
    import httpx
    try:
        response = httpx.get("http://127.0.0.1:8000/api/health", trust_env=False, timeout=4)
        health = response.json()
        if health.get("busy") or health.get("engine_loaded"):
            raise RuntimeError("The app is using the GPU. Finish/close its engine before this isolated experiment.")
    except httpx.ConnectError:
        health = {"status": "offline"}

    # Permit loopback health checks only. Block external connections in this process,
    # in addition to HF offline flags and the engine's local_files_only load.
    connect = socket.socket.connect
    def local_connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6) and address[0] not in ("127.0.0.1", "::1", "localhost"):
            raise RuntimeError("External network disabled for the experiment.")
        return connect(sock, address)
    socket.socket.connect = local_connect

    active = json.loads((settings.data_root/"narrators/current.json").read_text())
    profile = json.loads((settings.data_root/"narrators"/active["id"]/"profile.json").read_text(encoding="utf-8"))
    if profile["label"] != "Voice C" or not profile["consent"].get("rights_confirmed"):
        raise ValueError("Expected the approved Voice C reference and saved permission.")
    reference = settings.data_root/profile["reference_audio_relative_path"]
    if file_hash(reference) != profile["reference_sha256"]:
        raise ValueError("Reference checksum differs from the saved narrator.")
    if profile["engine_parameters"] != PARAMETERS:
        raise ValueError("Saved voice parameters differ from production defaults; review baseline first.")
    baseline = dict(PARAMETERS)
    expressive = {**baseline, "temperature": .9}
    configs = [
        ("A_baseline", baseline, segment_text(SCRIPT, settings.segment_chars)),
        ("B_expressive", expressive, segment_text(SCRIPT, settings.segment_chars)),
        ("C_context", expressive, context_sections(SCRIPT)),
    ]
    for _, _, sections in configs:
        assert " ".join(SCRIPT.split()) == " ".join(" ".join(sections).split())
    (out/"script.txt").write_text(SCRIPT+"\n", encoding="utf-8")
    report = {"created_utc": datetime.now(timezone.utc).isoformat(), "status": "running",
              "code_revision": CODE_REVISION, "model_repo": MODEL_REPO, "model_revision": MODEL_REVISION,
              "reference": {"id": profile["id"], "label": profile["label"], "path": profile["reference_audio_relative_path"],
                            "sha256": profile["reference_sha256"], "rights_confirmed": True},
              "script_sha256": hashlib.sha256(SCRIPT.encode()).hexdigest(),
              "script_word_count": len(SCRIPT.split()), "offline_external_tcp_blocked": True,
              "live_app_before": health, "production_source_sha256": before_code,
              "user_data_sha256_before": before_data, "configurations": []}
    def save():
        (out/"measurements.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    save()
    try:
        engine = TurboEngine(settings)
        started = time.perf_counter()
        print("Preparing native runtime...", flush=True)
        engine.prepare_runtime()
        report["runtime_prepare_seconds"] = time.perf_counter()-started
        import torch
        import numpy as np
        import librosa
        import soundfile as sf
        import chatterbox.tts_turbo as turbo
        from chatterbox.models.t3 import t3 as t3_module
        from chatterbox.models.t3.modules import cond_enc
        report["environment"] = {"python": sys.version, "torch": torch.__version__, "cuda": torch.version.cuda,
                                  "gpu": torch.cuda.get_device_name(0),
                                  "vram_bytes": torch.cuda.get_device_properties(0).total_memory}
        report["installed_source_sha256"] = {str(Path(m.__file__).relative_to(ROOT)): file_hash(m.__file__)
                                                 for m in (turbo, t3_module, cond_enc)}
        report["generate_signature"] = str(inspect.signature(turbo.ChatterboxTurboTTS.generate))
        report["reference"]["duration_seconds"] = sf.info(reference).duration
        started = time.perf_counter()
        engine.load()
        torch.cuda.synchronize()
        report["shared_model_load_seconds"] = time.perf_counter()-started
        report["turbo_emotion_conditioning_enabled"] = engine.model.t3.hp.emotion_adv
        report["text_context_positions"] = engine.model.t3.tfmr.config.n_positions
        original_inference = engine.model.t3.inference_turbo
        trace = {}
        def traced_inference(*args, **kwargs):
            trace.clear()
            trace.update({k: kwargs[k] for k in ("temperature", "top_k", "top_p", "repetition_penalty")})
            trace["input_text_tokens"] = int(kwargs["text_tokens"].shape[-1])
            result = original_inference(*args, **kwargs)
            trace["speech_tokens"] = int(result.numel())
            trace["possible_1000_token_limit"] = result.numel() >= 1000
            return result
        engine.model.t3.inference_turbo = traced_inference

        def speaker_embedding(a):
            audio16 = librosa.resample(a, orig_sr=24000, target_sr=16000)
            return engine.model.ve.embeds_from_wavs([audio16], sample_rate=16000)[0]
        def cosine(a, b):
            return float(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)))
        for name, parameters, sections in configs:
            print(f"Starting {name}: temperature={parameters['temperature']}, {len(sections)} sections", flush=True)
            folder = out/name
            folder.mkdir()
            record = {"id": name, "parameters": parameters, "sections": [], "issues": []}
            report["configurations"].append(record)
            arrays, embeddings = [], []
            run_started = time.perf_counter()
            for index, text in enumerate(sections, 1):
                print(f"  section {index}/{len(sections)} ({len(text)} characters)", flush=True)
                # Same seed for corresponding sections. No retries or cherry-picking.
                result = engine.synthesize(text, reference, parameters)
                a = validate_audio(result.samples, result.sample_rate)
                path = folder/f"section-{index:02}_raw.wav"
                info = write_raw(path, a, result.sample_rate)
                embedding = speaker_embedding(a)
                embeddings.append(embedding)
                arrays.append(a)
                token_trace = dict(trace)
                assert all(token_trace[k] == parameters[k] for k in ("temperature", "top_p", "top_k", "repetition_penalty"))
                if token_trace["possible_1000_token_limit"]:
                    record["issues"].append(f"Section {index}: possible speech-token truncation; inspect ending.")
                record["sections"].append({"index": index, "text": text, "model_normalized_text": turbo.punc_norm(text),
                    "chars": len(text), "words": len(text.split()), "file": str(path.relative_to(out)),
                    **info, **result.metrics, "inference_trace": token_trace,
                    "waveform": waveform_metrics(a, 24000),
                    "speaker_cosine_to_reference": cosine(embedding, engine.model.conds.t3.speaker_emb.detach().cpu().numpy().ravel())})
                save()
            record["generation_seconds"] = sum(s["generation_seconds"] for s in record["sections"])
            record["generation_plus_measurement_seconds"] = time.perf_counter()-run_started
            # Same assembly for all: original samples plus minimum 0.12 s boundary
            # gap. No fades, trimming, gain, or other production export processing.
            combined, inserted = combine(arrays, .12)
            raw_path = out/f"{name}_raw_1.00x.wav"
            write_raw(raw_path, combined, 24000)
            tempo_path = out/f"{name}_tempo_1.10x.wav"
            convert(raw_path, tempo_path, 1.1)
            normalized_path = out/f"{name}_listening_levelmatch_1.00x.wav"
            # Shared listening level is finalized below after seeing all three peaks.
            record.update(raw_file=raw_path.name, raw_sha256=file_hash(raw_path), tempo_file=tempo_path.name,
                          inserted_boundary_gap_seconds=inserted, waveform=waveform_metrics(combined, 24000),
                          measured_words_per_minute=60*len(SCRIPT.split())/(len(combined)/24000),
                          peak_allocated_bytes=max(s["peak_allocated_bytes"] for s in record["sections"]),
                          peak_reserved_bytes=max(s["peak_reserved_bytes"] for s in record["sections"]),
                          adjacent_section_speaker_cosines=[cosine(a,b) for a,b in zip(embeddings,embeddings[1:])])
            save()
        # Avoid a louder-is-better bias. Same integrated LUFS target for all raw
        # listening copies; lower the common target if any would exceed -1 dBFS.
        target = min(-23.0, *(r['waveform']['integrated_lufs']-1-r['waveform']['sample_peak_dbfs']
                             for r in report['configurations']))
        report["shared_listening_lufs"] = target
        for record in report['configurations']:
            a, sr = sf.read(out/record['raw_file'], dtype='float32')
            gain = target-record['waveform']['integrated_lufs']
            a = a * 10**(gain/20)
            path = out/f"{record['id']}_listening_levelmatch_1.00x.wav"
            write_raw(path, a, sr)
            record['levelmatched_listening'] = {"file": path.name, "gain_db": gain, "waveform": waveform_metrics(a,sr)}
            assert file_hash(out/record['raw_file']) == record['raw_sha256']
        report['status'] = 'completed'
    except BaseException as error:
        report['status'] = 'failed'
        report['failure'] = repr(error)
        raise
    finally:
        report['production_source_unchanged'] = hashes(production_paths) == before_code
        report['user_data_unchanged'] = hashes(data_paths) == before_data
        report['reference_unchanged'] = file_hash(reference) == profile['reference_sha256']
        save()
    assert report['production_source_unchanged'] and report['user_data_unchanged'] and report['reference_unchanged']
    print(f"Completed exactly three configurations. Results: {out}", flush=True)


if __name__ == '__main__':
    main()
