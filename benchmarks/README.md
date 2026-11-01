# Phase 0/1 benchmark

Run PowerShell commands from the repository root. Python 3.12 is supported by the inspected package metadata (`docs/licenses/*pyproject.toml`); this machine has 3.12.2. Chatterbox upstream reports testing on Python 3.11/Debian; Windows is being checked locally. No WSL installation is needed for Kokoro.

## Environments

The recorded CUDA wheel pair is torch/torchaudio 2.6.0+cu124. The NVIDIA driver reports CUDA compatibility 12.6; this is distinct from PyTorch's bundled 12.4 runtime. Do not install CPU torch wheels over this pair.

```powershell
python -m venv .venv-kokoro
.\.venv-kokoro\Scripts\python.exe -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
.\.venv-kokoro\Scripts\python.exe -m pip install -r benchmarks/requirements-kokoro.in
.\.venv-kokoro\Scripts\python.exe scripts/check_environment.py --output docs/environment-final.json
```

For the exact installed dependency versions, replace the `.in` installation with:

```powershell
.\.venv-kokoro\Scripts\python.exe -m pip install --no-deps -r benchmarks/requirements-kokoro.lock.txt --extra-index-url https://download.pytorch.org/whl/cu124
.\.venv-kokoro\Scripts\python.exe -m pip check
```

The lock includes the official spaCy English model URL. Pip installation reports in `docs/*install.json` contain download URLs/hashes. `docs/licenses/kokoro-installed/` archives installed package license declarations and bundled license texts. The FFmpeg binary is virtualenv-local via imageio-ffmpeg; no PATH changes are required. Benchmark output uses soundfile directly.

Chatterbox and Turbo share a separate environment because upstream requires Transformers 5.2.0 while the tested Kokoro environment uses 4.51.3:

```powershell
python -m venv .venv-chatterbox
.\.venv-chatterbox\Scripts\python.exe -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
.\.venv-chatterbox\Scripts\python.exe -m pip install -r benchmarks/requirements-chatterbox.in
.\.venv-chatterbox\Scripts\python.exe -m pip install --no-deps git+https://github.com/resemble-ai/chatterbox.git@5de7a54aa4e5e2baadb0182dde554908b48b85c2
```

The `.in` follows the archived upstream dependency list, replacing mutable Perth `master` with reviewed commit `ff1c8ac55a976971245cdd53c18d6131ca00d993`. Gradio/FastAPI are upstream package dependencies; no application or server is built or launched. Use the recorded Chatterbox lock with `--no-deps` for exact reproduction, then `pip check`; this preserves the explicit Perth pin instead of resolving upstream's mutable URL again.

## Downloads and execution

`download_models.py` uses only official Hugging Face repositories and exact revisions in `docs/licenses/revisions.json`. It saves byte counts and file SHA256s to `docs/<model>-download.json`. It excludes Chatterbox's bundled speaker conditionals; those are unnecessary when supplying an authorized reference. Kokoro's three assets total 327,738,002 bytes. Larger candidates' actual downloaded sizes are recorded separately.

```powershell
.\.venv-kokoro\Scripts\python.exe benchmarks/download_models.py kokoro
.\.venv-kokoro\Scripts\python.exe benchmarks/evaluate.py --model kokoro --cases smoke
# Run this before downloading all larger candidates; it produced 2.175 seconds of speech locally.
.\.venv-kokoro\Scripts\python.exe benchmarks/evaluate.py --model kokoro --cases neutral documentary pronunciation long
.\.venv-kokoro\Scripts\python.exe benchmarks/evaluate.py --model kokoro --cases restart
.\.venv-kokoro\Scripts\python.exe benchmarks/download_models.py chatterbox
.\.venv-kokoro\Scripts\python.exe benchmarks/download_models.py turbo
.\.venv-chatterbox\Scripts\python.exe benchmarks/evaluate.py --model chatterbox --load-only
.\.venv-chatterbox\Scripts\python.exe benchmarks/evaluate.py --model turbo --load-only
```

Downloads need network access. `evaluate.py` forces Hugging Face/Transformers offline mode and uses local pinned snapshots. Each invocation is a new process. In Windows PowerShell 5, native stderr warnings can cause an apparent nonzero shell status when redirecting; use `; exit $LASTEXITCODE` after a redirected command to retain the Python process exit code. The saved JSON `status` and validation results are the evidence of inference success.

For the cloning cases, supply the same clean 10–30-second recording to both models, with provenance JSON outside the repository:

```json
{"identity":"Recording owner or authorized speaker and recording description", "rights_confirmed":true, "scope":"Permission to clone this voice and publish the generated narration commercially"}
```

Do not create this attestation without the rights holder's confirmation. Once available:

```powershell
.\.venv-chatterbox\Scripts\python.exe benchmarks/evaluate.py --model chatterbox --reference C:\path\reference.wav --consent-record C:\path\consent.json --cases neutral documentary pronunciation long
.\.venv-chatterbox\Scripts\python.exe benchmarks/evaluate.py --model chatterbox --reference C:\path\reference.wav --consent-record C:\path\consent.json --cases restart
# Repeat both commands with --model turbo, using the identical reference and consent record.
.\.venv-kokoro\Scripts\python.exe scripts/summarize_results.py
```

## Method and listening gate

All candidates receive identical authored text files and conservative sentence chunks (~350 characters maximum for this corpus). The long case is 913 words. Actual durations vary by model: the observed Kokoro short clips are 41.4 and 38.575 seconds, and long narration is 360.475 seconds. Original chunks, per-segment WAVs, and combined WAVs are saved. No normalization, music, or inserted pauses. WAVs are mono 32-bit float to retain raw output and expose any overrange peaks. No MP3/export application is implemented.

The runner logs load time separately, synchronized generation time including text/reference processing, total case wall time, output duration/sample rate, RTF, failures, and PyTorch peak allocated/reserved GPU bytes. Allocator statistics exclude driver/context and non-PyTorch memory. A single run per case establishes a local observation, not statistical confidence. First generation is cold; later cases reuse the model. Repeated cases overwrite their same-named files; archive results first if preserving another run.

Kokoro uses the official `af_heart` preset at speed 1. It is not a unique cloned narrator, and its similarity-to-reference score is N/A. Chatterbox adapters use upstream defaults and retain watermarking. The original model consumes up to 6 seconds for speech conditioning/10 seconds for its decoder; Turbo uses up to 15/10 seconds and internally normalizes the reference. No training or separate voice-design feature has been added.

Fill `listening-scores.csv` after listening. Naturalness/pronunciation/stability/artifact freedom: 1=poor, 5=excellent; similarity: 1=unrecognizable, 5=very close. Compare raw segments as well as combined clips; inspect first/middle/last long sections and compare `neutral.wav` with `restart.wav`. Record missing/repeated words and major artifacts in notes. Randomize candidate labels through another listener where possible once comparative files exist. No listening scores have been invented.

Gate: average naturalness >=4/5, identity consistency >=4/5, no frequent omissions/repetitions/major artifacts, and a successful 5–10-minute run. Human ratings are mandatory before selecting a production engine. Stop before Phase 2.

## Completed consented comparison

The user has supplied `record-sample.ogg` and expressly permitted cloning and commercial publication. `docs/reference-inspection.json` records provenance and hashes. The unchanged decoded float WAV and runtime consent record are in gitignored `benchmarks/results/reference/`. All cloning commands above were executed with these local paths instead of the example `C:\path\...` placeholders, with logs in `docs/chatterbox-benchmark.log`, `docs/chatterbox-restart.log`, `docs/turbo-benchmark.log`, and `docs/turbo-restart.log`.

Both cloned-voice long cases and all restart cases now pass numerical validation. `scripts/summarize_results.py` also verifies shared text hashes, chunk order, and cloning-reference hashes across candidates. The model decision remains subject to human listening and user review.

`prepare_listening.py` has already copied all 15 main-case WAVs to `benchmarks/results/listening/` under randomized A/B/C labels and created an empty `scores.csv`. See `docs/listening-review.md` for links and scoring instructions. `docs/listening-key.json` preserves the mapping. Do not rerun the preparation script after scoring: it randomizes labels again and replaces the score-sheet template. These files are comparison artifacts only; no application UI or playback server is built.
