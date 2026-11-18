# Local Narration (Awal)

Local Windows narration with React/TypeScript/Vite, FastAPI, **Qwen3-TTS 0.6B Base**, PyTorch/CUDA, and FFmpeg. One local backend, no hosting or login. Existing Chatterbox projects and recordings remain available for playback and export.

## Run

```powershell
.\start.bat
```

Open **http://127.0.0.1:8000** and keep the terminal open. For development, run `.\dev` from the project root and open **http://127.0.0.1:3000**. The root `npm.cmd run dev` does the same thing. Stop an older running backend before starting the Qwen version. Ctrl+C finishes the active section and leaves remaining sections resumable.

Requirements: 64-bit Windows, Python 3.12, NVIDIA CUDA GPU; validated on RTX 4070 Laptop, 8 GB. The model is lazy-loaded and requires at least 6 GiB free GPU memory before loading. This release does not support Intel/AMD graphics, CPU-only generation, Macs, or phones.

## Setup

`setup.bat` installs the pinned runtime into **`.venv-qwen3`** and verifies/downloads the pinned model. Initial setup needs internet; normal inference and export are local/offline. The existing `.venv-chatterbox` is preserved, not upgraded or used for Qwen generation. On this development machine the already-validated Qwen snapshot is reused through `.local-config.json`.

For a fresh source checkout, build the interface first (Node.js 22.12+):

```powershell
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.\setup.bat
```

Run `check.bat` for read-only dependency, CUDA, FFmpeg, model/code checksum diagnostics. Runtime versions are pinned in `requirements.txt` and `requirements-qwen.lock.txt`; legacy requirements remain in `requirements-chatterbox.txt` and `requirements-runtime.lock.txt` for rollback.

## Narration and references

Upload a clean authorized 10?30-second reference and enter its **exact spoken transcript**. Existing saved references can receive a transcript without replacing their WAV/profile. This installation keeps Voice C and its previously confirmed transcript. Each new project snapshots its reference hash, transcript, engine revision, and generation settings, so later changes do not change that project's narrator.

Paste an English script, preview complete-sentence paragraph-aware sections, and create/generate. Sections group complete sentences up to 600 characters. An oversized individual sentence is rejected rather than split mid-thought. The original project script and section text are preserved.

In Review, edit **inference text** to correct pronunciation, such as `17,400` ? `seventeen thousand four hundred`, then save and deliberately regenerate that section. Original script text stays separate; there is no automatic rewriting. Every attempt records its input, parameters, seed, and result. Successful raw WAV versions and their metadata remain immutable; failed regeneration keeps previous audio. Closing the browser does not stop the server.

Old Chatterbox projects cannot silently regenerate with Qwen. Their previews and exports use the existing recordings, including the last saved take if old edits are stale. Create a **new Qwen project** from the desired script to generate new narration. There is no model selector or automatic project migration.

## Export and pacing

Processed exports default to **1.10? pitch-preserving tempo**. Qwen's optional trailing-silence control is enabled for new projects: only tails quieter than ?45 dBFS for at least 0.8 seconds are shortened, retaining 0.35 seconds after the last above-threshold sample. All internal pauses and retained speech samples stay unchanged during trimming. The exact per-section cuts are recorded in export metadata. No raw WAV is modified.

Turn off trailing-silence trimming to keep the full generated tail. Turn off processing for original-speed audio. WAV, MP3, and selected-section ZIP exports remain available. Processed audio receives attenuation-only sample-peak protection; optional conservative volume adjustment remains available. Legacy Chatterbox processed exports retain their previous edge processing. Saved exports are snapshots; creating another never overwrites them.

## Storage, compatibility, and rollback

- `data/projects/`: project JSON, immutable raw versions, and saved exports.
- `data/narrators/`: profiles, reference WAVs/uploads, and reference-hash-bound transcript sidecars.
- `data/logs/app.log`: local application log.
- `.local-config.json`: persistent `cache_root` and optional absolute `qwen_model_dir`.
- `docs/qwen-download.json`: approved model and code fingerprints.
- `docs/licenses/` and `THIRD_PARTY_NOTICES.txt`: retained third-party notices.

`TTS_DATA_DIR` selects an isolated data directory before startup. `HF_HOME` controls the hub cache; `AWAL_QWEN_MODEL` can select the approved local model folder, still subject to checksum validation. `TTS_FFMPEG` selects an FFmpeg executable. Startup/inference never silently downloads another model.

New projects are schema 2 with the Qwen engine identity; old projects are not batch-rewritten. See [integration design, rollback, tests, and limitations](docs/qwen-production-integration.md). Stop the server before rollback. Preserve new Qwen project directories outside the old application's project list before using pre-integration code `2e25b97` with `.venv-chatterbox`; old code is not Qwen-schema aware. Existing Chatterbox files do not need conversion. No historical recording is deleted by integration.

## Verification and optional packaging

```powershell
.\.venv-qwen3\Scripts\python.exe -m pip install --no-deps -r requirements-dev.txt
.\.venv-qwen3\Scripts\python.exe -m pytest -q
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run build
```

Real CUDA/browser verification requires an authorized reference, its confirmed transcript, Chrome, and the existing Playwright tooling. It creates isolated test projects, not replacements for user projects. Evidence and commands are in the integration report.

To build a source-only sharing ZIP after the frontend build:

```powershell
.\.venv-qwen3\Scripts\python.exe scripts/build_release.py
```

It excludes personal references/projects, installed environments, model caches, and benchmark audio. Setup downloads pinned assets; binaries carry their own distribution conditions. No sharing archive is created merely by normal startup.

## Troubleshooting

- **502 on port 3000:** run `.\dev` and wait for readiness; keep the terminal open.
- **Older backend on port 8000:** stop its terminal and restart with the Qwen launcher.
- **Missing transcript:** enter the exact recording words in the saved reference form; existing projects keep their prior snapshot.
- **CUDA or memory error:** close other GPU workloads and run `check.bat`. Existing audio stays intact; retry deliberately.
- **Missing or changed assets/code:** run `setup.bat`; do not upgrade individual production packages.
- **Interrupted generation:** reopen the project and generate missing/changed sections. Completed audio and last attempt seeds are retained.
- **Port/data lock in use:** run one backend process per data directory. Do not enable Uvicorn reload or multiple workers.
