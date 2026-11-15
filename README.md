# Local Narration

A local Windows narration app using **React + TypeScript + Vite**, **Python/FastAPI**, **Chatterbox Turbo**, PyTorch/CUDA, and FFmpeg. No hosting or login.

## Run

```powershell
.\start.bat
```

Open **http://127.0.0.1:8000** and keep the terminal open. Run `check.bat` for diagnostics. Press **Ctrl+C** and let an active generation finish before closing the terminal.

Requirements: 64-bit Windows, Python 3.12, and an NVIDIA CUDA GPU. The verified baseline is an RTX 4070 Laptop with approximately 8 GB VRAM. Intel/AMD graphics, CPU-only inference, Macs, and phones are not supported by this release.

## First setup

Install Python 3.12, Git for Windows, and an appropriate NVIDIA driver, then run `setup.bat`. Setup downloads pinned dependencies/model files and verifies them. Initial setup needs internet and several GB of downloads; allow roughly 20 GB plus room for audio. Interrupted setup can be retried. Normal use is offline after a successful setup.

A sharing package includes the built interface, so normal users need no Node.js. Developers using a fresh source checkout build the frontend before setup:

```powershell
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
.\setup.bat
```

Python versions are pinned in `requirements.txt` and `requirements-runtime.lock.txt`. Do not upgrade individual packages without checking compatibility.

## Use

1. Upload your own authorized, clear 10-30-second WAV, OGG/Opus, FLAC, MP3, or M4A reference (up to 15 MB), and confirm the voice rights statement. Existing projects retain their saved narrator when the active reference changes.
2. Enter an English script/title, preview sections, then generate. Edit, save, and regenerate individual sections. Each retry uses a fresh random seed to produce another take; its exact seed is saved with the section. Failed attempts preserve prior good audio; missing/changed generation resumes unfinished sections.
3. Preview raw sections or export a master WAV, MP3, or selected-section ZIP. Master previews are saved export snapshots; create a new export after editing/regeneration.

Raw audio stays at original speed as 24 kHz mono float WAV. Processed exports default to adjustable, pitch-preserving **1.10x** tempo (0.50x to 2.00x). Original-speed exports ignore the tempo field. Existing quiet counts toward the default 0.12-second minimum boundary gap. Original uploads and successful raw versions remain intact.

Processed masters conservatively shorten internal section-edge silence only when it stays below -55 dBFS for at least 0.5 seconds, retaining 0.15 seconds on each affected side. Interior pauses and the recording's outer edges are retained; entirely quiet sections are not trimmed. Tiny 3 ms fades soften internal joins without overlapping speech. Selected-section files keep their original pauses. Processed exports also apply attenuation when needed for a -1 dBFS sample-peak ceiling, including a decoded MP3 check and re-encoding if needed. This is sample-peak protection, not guaranteed true-peak mastering. Optional volume adjustment remains off by default and uses bounded static gain. Turning off export processing bypasses join cleanup and peak attenuation.

## Develop

Start both FastAPI and the frontend dev server with one command:

```powershell
.\dev
```

Open **http://127.0.0.1:3000** once the terminal says ready. The root `npm.cmd run dev` command does the same thing. It starts FastAPI on port 8000 if needed and waits for readiness before starting Vite. Existing servers are reused. Keep this terminal open; Ctrl+C gracefully stops servers started by this command. Servers started separately remain running. Vite proxies API/audio requests to FastAPI and preserves same-origin write protection. Developers need Node.js 22.12+ (verified: 24.14).

```powershell
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run build
# With FastAPI running and port 3000 free:
npm.cmd --prefix frontend run check:dev
```

Edit `frontend/src/`. Builds generate `app/static/ui/` and the `app/static/index.html` entry. Generated frontend files include the required dependency notices. Normal use needs only `start.bat` on port 8000.

## Data and configuration

- `data/projects/`: scripts, sections, raw versions, and exports.
- `data/narrators/`: saved reference profiles, decoded reference WAVs, and original uploads.
- `data/logs/app.log`: current application log.
- `model-cache/` and `.local-config.json`: this installation's model cache/configuration.
- `docs/turbo-download.json`: required pinned model-file hashes.
- `docs/licenses/`: required current third-party terms and dependency notice inventory.

An explicit `HF_HOME` overrides the configured model cache. Guided setup defaults to persistent `%LOCALAPPDATA%\LocalNarration\huggingface`; an existing local configuration is retained. `TTS_DATA_DIR` selects another workspace before startup; `TTS_FFMPEG` selects an explicit FFmpeg executable. Startup never silently downloads a different model.

No historical archives or benchmark material are kept in this project. User projects, saved narrators, and their normal export files remain application data. The supplied source/package has no default personal voice; new installations upload their own reference.

## Verify and optionally package

```powershell
.\.venv-chatterbox\Scripts\python.exe -m pip install --no-deps -r requirements-dev.txt
.\.venv-chatterbox\Scripts\python.exe -m pytest -q
```

An optional real Chrome/CUDA workflow check requires installed Chrome, the pinned Playwright dependency, and an explicitly authorized reference:

```powershell
.\.venv-chatterbox\Scripts\python.exe scripts/react_browser_check.py --reference "path\to\authorized-reference.wav"
```

The current suite also tests packaging and rejects stale frontend source/modified bundles. To create a sharing ZIP only when you need one:

```powershell
npm.cmd --prefix frontend run build
.\.venv-chatterbox\Scripts\python.exe scripts/build_release.py
```

The output is `dist/LocalNarration-Windows.zip`. It includes selected source, compiled frontend assets, locks, and notices; it excludes private data, model caches, installed environments, and `node_modules`. No sharing ZIP is retained as part of this cleanup. A second physical PC and a full empty-cache model download have not been verified.

## Troubleshooting

- **502 on port 3000:** the frontend cannot reach FastAPI. Run `.\dev` from the project root and wait for the ready message. This starts the missing backend; keep that terminal open.
- **CUDA unavailable:** run `check.bat`; verify NVIDIA hardware/driver and the pinned Python environment.
- **Missing model/checksum mismatch:** check the cache configuration, then run `.\.venv-chatterbox\Scripts\python.exe scripts/download_turbo.py` with internet access.
- **Missing interface:** build `frontend/` from source, or re-extract a complete application package.
- **Generation/export failure:** read `data/logs/app.log`, correct the cause, and retry affected sections. Old successful audio remains intact.
- **Port/data lock in use:** close the existing server first. Run one local process; do not enable Uvicorn reload or multiple workers.

Required model, Python/native dependency, and frontend terms are retained in [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt) and `docs/licenses/`. They are part of the current software, not optional historical documentation. Installed dependency directories are kept intact.
