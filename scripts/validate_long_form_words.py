"""Offline ASR cross-check for an isolated narration run; no app changes.

Requires an already downloaded validation-only Whisper snapshot. Never supplies
the expected script as a decoder prompt and never regenerates narration.
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
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"


def alignment(expected, actual):
    """Minimum-edit word alignment, retaining every mismatch for review."""
    n, m = len(expected), len(actual)
    cost = [[0]*(m+1) for _ in range(n+1)]
    for i in range(n+1):
        cost[i][0] = i
    for j in range(m+1):
        cost[0][j] = j
    for i in range(1, n+1):
        for j in range(1, m+1):
            cost[i][j] = min(cost[i-1][j]+1, cost[i][j-1]+1,
                             cost[i-1][j-1]+(expected[i-1] != actual[j-1]))
    changes = []
    i, j = n, m
    while i or j:
        if i and j and cost[i][j] == cost[i-1][j-1]+(expected[i-1] != actual[j-1]):
            if expected[i-1] != actual[j-1]:
                changes.append({"operation": "substitution", "expected_index": i-1,
                                "expected": expected[i-1], "recognized": actual[j-1]})
            i -= 1
            j -= 1
        elif i and cost[i][j] == cost[i-1][j]+1:
            changes.append({"operation": "deletion", "expected_index": i-1,
                            "expected": expected[i-1], "recognized": ""})
            i -= 1
        else:
            changes.append({"operation": "insertion", "expected_index": i,
                            "expected": "", "recognized": actual[j-1]})
            j -= 1
    return {"expected_words": n, "recognized_words": m, "edit_count": cost[n][m],
            "word_error_rate": cost[n][m]/max(1,n), "differences": list(reversed(changes))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    if not run.is_relative_to((ROOT/"benchmarks/results").resolve()):
        raise ValueError("Expected an isolated benchmark run.")
    output = run/"word-coverage.json"
    if output.exists():
        raise ValueError("Word-coverage report already exists; preserve the first check.")
    source = json.loads((run/"measurements.json").read_text(encoding="utf-8"))
    if source['status'] != 'completed' or len(source['configurations']) != 1:
        raise ValueError("Expected one completed long-form configuration.")
    manifest = json.loads((ROOT/"model-cache/validation-asr/download.json").read_text(encoding="utf-8"))
    snapshot = Path(manifest['snapshot'])
    from app.projects import file_hash
    for item in manifest['files']:
        if file_hash(snapshot/item['name']) != item['sha256']:
            raise ValueError("Validation model checksum mismatch.")
    connect = socket.socket.connect
    def offline(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError("Network disabled during transcription.")
        return connect(sock, address)
    socket.socket.connect = offline
    import torch
    import librosa
    import soundfile as sf
    from transformers import WhisperProcessor, WhisperForConditionalGeneration, pipeline
    from transformers.models.whisper.english_normalizer import EnglishTextNormalizer
    print("Loading local validation-only Whisper...", flush=True)
    started = time.perf_counter()
    processor = WhisperProcessor.from_pretrained(snapshot, local_files_only=True)
    model = WhisperForConditionalGeneration.from_pretrained(snapshot, local_files_only=True,
                torch_dtype=torch.float16, attn_implementation="eager").to("cuda").eval()
    normalizer = EnglishTextNormalizer(processor.tokenizer.english_spelling_normalizer)
    recognizer = pipeline("automatic-speech-recognition", model=model, tokenizer=processor.tokenizer,
                         feature_extractor=processor.feature_extractor, device=0,
                         chunk_length_s=30, stride_length_s=(4,4), torch_dtype=torch.float16)
    report = {"status": "running", "model_repo": manifest['repo'], "model_revision": manifest['revision'],
              "model_license": manifest['license'], "snapshot_files": manifest['files'],
              "model_load_seconds": time.perf_counter()-started, "offline": True,
              "expected_text_not_supplied_as_prompt": True, "sections": [],
              "limitation": "ASR differences flag review; recognition is not proof of pronunciation, naturalness, or identity."}
    def save():
        output.write_text(json.dumps(report,indent=2),encoding="utf-8")
    save()
    total_words = total_edits = 0
    for s in source['configurations'][0]['sections']:
        path = run/s['file']
        assert file_hash(path) == s['sha256']
        audio, sr = sf.read(path, dtype="float32")
        audio = librosa.resample(audio,orig_sr=sr,target_sr=16000)
        torch.cuda.reset_peak_memory_stats()
        tick = time.perf_counter()
        prediction = recognizer({"array": audio,"sampling_rate":16000},generate_kwargs={"do_sample":False,"num_beams":1,"max_new_tokens":440})['text']
        expected, actual = normalizer(s['text']).split(), normalizer(prediction).split()
        diff = alignment(expected,actual)
        entry = {"index": s['index'], "file": s['file'], "expected_text": s['text'], "transcript": prediction,
                 "greedy": diff, "asr_seconds":time.perf_counter()-tick,
                 "peak_allocated_bytes":torch.cuda.max_memory_allocated()}
        if diff['edit_count']:
            # A second unprompted decode distinguishes unstable recognition from
            # consistently detected mismatches; neither automatically proves a TTS error.
            beam = recognizer({"array":audio,"sampling_rate":16000},generate_kwargs={"do_sample":False,"num_beams":5,"max_new_tokens":440})['text']
            entry['beam_transcript'] = beam
            entry['beam'] = alignment(expected,normalizer(beam).split())
        total_words += diff['expected_words']
        total_edits += diff['edit_count']
        report['sections'].append(entry)
        print(f"Section {s['index']}: {diff['edit_count']} ASR word differences out of {diff['expected_words']}",flush=True)
        save()
    report.update(status="completed",expected_words=total_words,greedy_word_edits=total_edits,
                  greedy_word_error_rate=total_edits/total_words,
                  flagged_sections=[s['index'] for s in report['sections'] if s['greedy']['edit_count']],
                  elapsed_seconds=time.perf_counter()-started)
    save()
    print(f"Completed offline word check: {total_edits}/{total_words} greedy ASR edits. Review all flagged sections.",flush=True)


if __name__ == "__main__":
    main()
