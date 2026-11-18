"""Bounded offline repair experiment: sections 6/9, two saved seeds each.

Uses only the existing Turbo engine. No project updates, app rebuild, model
downloads, text rewrites, or replacements of source recordings.
"""
import argparse
import json
import os
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from app.audio import convert, write_raw
from app.config import Settings
from scripts.legacy_turbo_engine import CODE_REVISION, MODEL_REVISION
from app.projects import file_hash
from scripts.legacy_turbo_engine import TurboEngine
from scripts.expressive_delivery_experiment import context_sections, waveform_metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    src, out = args.run.resolve(), args.output.resolve()
    allowed = (ROOT/"benchmarks/results").resolve()
    if not src.is_relative_to(allowed) or not out.is_relative_to(allowed) or out == src:
        raise ValueError("Use distinct isolated benchmark directories.")
    if (out/"repair-measurements.json").exists():
        raise ValueError("Repair run exists; no overwriting or extra attempts.")
    out.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    old = json.loads((src/"measurements.json").read_text(encoding="utf-8"))
    original = old["configurations"][0]
    assert old["code_revision"] == CODE_REVISION and old["model_revision"] == MODEL_REVISION
    assert original["parameters"]["temperature"] == .9 and original["parameters"]["seed"] == 1234
    script = (src/"script.txt").read_text(encoding="utf-8").strip()
    assert context_sections(script) == [s["text"] for s in original["sections"]]
    reference = settings.data_root/old["reference"]["path"]
    assert file_hash(reference) == old["reference"]["sha256"]
    protected = json.loads((out/"protected-hashes.json").read_text(encoding="utf-8"))
    assert all(file_hash(ROOT/p) == h for p,h in protected.items())
    import httpx
    try:
        health = httpx.get("http://127.0.0.1:8000/api/health",trust_env=False,timeout=5).json()
        if health["busy"] or health["engine_loaded"]:
            raise RuntimeError("Production GPU is occupied; do not overlap inference.")
    except httpx.ConnectError:
        pass
    connect = socket.socket.connect
    def offline(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError("Network disabled during repair generation.")
        return connect(sock,address)
    socket.socket.connect = offline
    report = {"source_run":str(src.relative_to(ROOT)),"reference":old["reference"],
              "code_revision":CODE_REVISION,"model_revision":MODEL_REVISION,
              "planned_seeds":[1235,1236],"affected_sections":[6,9],
              "status":"running","attempts":[],"no_text_changes":True}
    def save():
        (out/"repair-measurements.json").write_text(json.dumps(report,indent=2,allow_nan=False),encoding="utf-8")
    save()
    try:
        engine = TurboEngine(settings)
        print("Preparing original Turbo engine...",flush=True)
        start = time.perf_counter();engine.prepare_runtime();engine.load()
        report["prepare_and_load_seconds"] = time.perf_counter()-start
        import torch
        trace = {}
        generate = engine.model.t3.inference_turbo
        def traced(*a, **kw):
            result = generate(*a, **kw)
            trace['speech_tokens'] = int(result.numel())
            trace['possible_limit_hit'] = result.numel() >= 1000
            return result
        engine.model.t3.inference_turbo = traced
        for index in (6,9):
            section = original['sections'][index-1]
            for seed in (1235,1236):
                path = out/f"section-{index:02}-seed-{seed}_raw.wav"
                if path.exists():
                    raise ValueError("Existing take: refusing to overwrite.")
                params = {**original['parameters'],'seed':seed}
                attempt = {"section":index,"seed":seed,"parameters":params,"text":section['text'],
                           "original_file":section['file'],"file":path.name,"status":"started"}
                report['attempts'].append(attempt);save()
                print(f"Generating only section {index}, seed {seed}",flush=True)
                try:
                    result = engine.synthesize(section['text'],reference,params)
                    info = write_raw(path,result.samples,result.sample_rate)
                    attempt.update(status='completed',**info,**result.metrics,inference_trace=dict(trace),
                                   waveform=waveform_metrics(result.samples,result.sample_rate))
                    assert not trace['possible_limit_hit']
                except Exception as error:
                    attempt.update(status='failed',error=repr(error));save()
                    raise
                save()
        report['status'] = 'completed'
    finally:
        report['protected_files_unchanged'] = all(file_hash(ROOT/p)==h for p,h in protected.items())
        save()
    assert report['protected_files_unchanged']
    print('Four bounded takes saved. Original narration and production unchanged.',flush=True)


if __name__ == '__main__':
    main()
