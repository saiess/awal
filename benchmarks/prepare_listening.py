"""Copy raw comparison samples under randomized labels for human listening."""
import csv
import json
import random
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
results = root / "benchmarks/results"
models = ["chatterbox", "turbo", "kokoro"]
random.SystemRandom().shuffle(models)
key = dict(zip(("A", "B", "C"), models))
cases = ("neutral", "documentary", "pronunciation", "long", "restart")
# Check the whole comparison before creating the listening set.
for model in models:
    for case in cases:
        report = json.loads((results / model / (case + ".json")).read_text(encoding="utf-8"))
        if report.get("status") != "ok":
            raise RuntimeError(f"Incomplete benchmark: {model}/{case}")
out = results / "listening"
out.mkdir(exist_ok=True)
for label, model in key.items():
    for case in cases:
        shutil.copyfile(results / model / (case + ".wav"), out / f"{label}-{case}.wav")
(root / "docs/listening-key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
with (out / "scores.csv").open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["label", "case", "naturalness_1_to_5", "pronunciation_1_to_5", "identity_consistency_1_to_5", "reference_similarity_1_to_5_or_NA", "artifact_freedom_1_to_5", "notes"])
    for label in key:
        for case in cases:
            writer.writerow([label, case, "", "", "", "", "", ""])
(out / "README.txt").write_text(
    "Listen to A, B, and C for each case, then fill scores.csv. Higher scores are better.\n"
    "Compare neutral/restart and first/middle/last parts of long narration for identity.\n"
    "Compare with ../reference/reference.wav for similarity; a preset is not expected to match.\n"
    "Mark wrong, missing or repeated words and objectionable artifacts in notes.\n"
    "These are unchanged raw WAV copies. No subjective ratings have been assigned.\n"
    "Do not open docs/listening-key.json until after scoring if you want a blind comparison.\n",
    encoding="utf-8")
print(f"Prepared {len(models) * len(cases)} raw WAV copies and an unscored listening sheet in {out}")
