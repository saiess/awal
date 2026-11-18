# Qwen production integration

## Design and compatibility contract (recorded before data changes)

One FastAPI process, one existing background job worker, and one active Qwen3-TTS 0.6B Base engine. Run the backend in the existing `.venv-qwen3` because its pinned Transformers 4.57.3 conflicts with the legacy Chatterbox environment. Add only missing web/export dependencies there; preserve `.venv-chatterbox` for rollback and existing diagnostic tools. React, JSON project storage, and FFmpeg remain.

New projects use schema 2 and an explicit Qwen engine ID/revision. Schema-1 Chatterbox projects remain readable and exportable, including their last saved recordings; they cannot be edited/regenerated through Qwen. Creating a separate Qwen project is the deliberate migration boundary. Never update a legacy project's engine label or automatically regenerate audio. Reopening a project does not migrate its data.

Existing narrator profiles and reference WAVs stay unchanged. Store a confirmed transcript in a small `reference-transcript.json` sidecar keyed to the reference SHA-256. New project narrator snapshots include the transcript and Qwen settings, so later voice/transcript changes do not alter existing projects. Voice C's previously confirmed transcript is seeded only when its recorded reference hash matches. New references require their own transcript and existing rights confirmation.

For Qwen sections, `text` remains the immutable source section and the complete project `script` remains intact. An optional `inference_text` override is edited separately and is recorded with each generation attempt/version. No automatic number expansion or script rewriting. Complete sentences are grouped within paragraphs up to 600 characters; oversized individual sentences are rejected with a clear message, never cut mid-thought.

Raw recordings retain versioned filenames. Persist seeds and actual generation parameters/text before inference, and retain immutable version metadata on success. Failed/interrupted attempts keep previous audio accessible and do not automatically retry. Record engine identity/revision in project and version metadata. Existing serialization and one-job gate continue to protect concurrent writes and GPU use.

Export defaults remain pitch-preserving 1.10×. Qwen processed exports may explicitly trim only excessive trailing quiet, retaining 0.35 seconds after a conservative activity threshold; never touch interior pauses or raw files. Record exact cuts in the export manifest. Legacy export behavior remains available. Preview/export are available independently of model loading.

Pinned model/code/tokenizer and official default ICL settings match the validated runs. Verify code and model checksums locally, use BF16/SDPA on CUDA, cache only the current reference prompt, and check GPU headroom before model load. Runtime inference never downloads assets. No model selector, extra service, database, or orchestration layer.

## Rollback behavior

Existing project JSONs, narrator profiles, completed versions, and WAV/MP3 exports are not batch-migrated. New transcript sidecars and an optional local model-directory setting are additive; legacy code ignores them. Preserve the legacy environment, dependency lock, model cache, and pre-integration Git revision `2e25b97`.

To roll back, stop the server first. The pre-integration application is not schema-2 aware: temporarily move only newly created Qwen project directories outside `data/projects`, retaining their files intact, before running that older code against the legacy data directory. Revert code to `2e25b97` and run its `.venv-chatterbox` launcher. Do not regenerate Qwen projects with old code. To return to Qwen, restore this integration's code/environment and put those Qwen directories back at their original paths. No audio conversion or deletion is part of rollback. This document describes rollback; it does not move any user projects.

All real existing data/reference/audio hashes are captured before the integration. Automated verification uses isolated application data and preserves historical recordings. The final running-application smoke check may create one clearly labelled new Qwen verification project with Voice C; it does not modify or regenerate any pre-existing project.

## Implementation and verification

**Completed on 18 November 2026.** The running backend reports `qwen3-tts-0.6b-base`; Qwen is the only production generation implementation. Existing Chatterbox projects remain playback/export projects. All 24 pre-existing data files match their pre-integration hashes, and all 119 packages in `.venv-chatterbox` retain their previous versions. Only an additive Voice C transcript sidecar and one clearly labelled new verification project were added to the real data directory. No historical recording was deleted or regenerated.

### Main changes

| Area | Files / behavior |
| --- | --- |
| Active engine and pins | [engine.py](../app/tts/engine.py), [config.py](../app/config.py), [qwen-download.json](qwen-download.json): local model/code verification, BF16/SDPA, default English ICL, cached reference prompt, GPU guards and token-cap rejection. |
| Storage and generation | [projects.py](../app/projects.py), [jobs.py](../app/jobs.py), [models.py](../app/models.py), [api.py](../app/api.py), [main.py](../app/main.py): schema 2, transcript sidecars/snapshots, immutable source plus separate inference override, persisted attempts/seeds/version metadata, legacy generation blocking, recovery and existing audio endpoints. |
| Text boundaries | [segmentation.py](../app/segmentation.py): paragraph-aware grouping of complete sentences up to 600 characters; no mid-sentence splitting. The full source script retains exact original whitespace. |
| Export | [audio.py](../app/audio.py): explicit processed-only trailing trim, per-section cut manifest, no interior-pause edits, immutable raw recordings, matching selected-section exports; existing tempo/peak protection/volume controls retained. |
| Existing React interface | [App.tsx](../frontend/src/App.tsx), [types.ts](../frontend/src/types.ts), [styles.css](../frontend/src/styles.css): reference transcript entry, inference-text editing with original-text disclosure, trailing-silence checkbox and clear read-only legacy status. Existing layout/theme retained. |
| Run/setup/share | `start.bat`, `check.bat`, `scripts/dev.mjs`, `setup_local.py`, `check_local_setup.py`, `download_qwen.py`, `build_release.py`, runtime locks, notices and [README](../README.md). Launchers use `.venv-qwen3`; source-only packaging selects the Qwen runtime/receipts/licenses. |
| Verification tools | Updated browser/application checks and automated tests; the previous Turbo implementation/constants/segmentation live only in `scripts/legacy_turbo_engine.py` for historical benchmarks, never in the application runtime or sharing package. |

### Exact runtime

| Component | Version / revision |
| --- | --- |
| Model | `Qwen/Qwen3-TTS-12Hz-0.6B-Base` / `5d83992436eae1d760afd27aff78a71d676296fc` |
| Qwen code | `qwen-tts==0.1.1` / `022e286b98fbec7e1e916cb940cdf532cd9f488e` |
| Bundled tokenizer provenance | `Qwen3-TTS-Tokenizer-12Hz` / `7dd38ad4e9bad454aae9cd937d0cd577604fe229` |
| Python | 3.12.2 |
| PyTorch / torchaudio | 2.6.0+cu124 / 2.6.0+cu124 |
| Transformers / Accelerate | 4.57.3 / 1.12.0 |
| FastAPI / Uvicorn | 0.164.0 / 0.54.0 |
| Starlette / Pydantic | 1.10.0 / 2.14.3 |
| NumPy / pyloudnorm / imageio-ffmpeg | 1.26.4 / 0.2.0 / 0.6.0 |
| Frontend | Existing React/React DOM 19.3.1, TypeScript 7.0.2, Vite 8.3.7; lock unchanged |

All 92 runtime distributions are pinned in [requirements-qwen.lock.txt](../requirements-qwen.lock.txt). Only pyloudnorm and imageio-ffmpeg were missing from the existing Qwen environment; pytest and its two missing helpers were added for verification. Production dependency and bundled native-library notices are in [the installed inventory](licenses/qwen-production-installed/inventory.json) and [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.txt). Qwen code/model/tokenizer declare Apache-2.0; native libraries and FFmpeg retain their own terms. The legacy environment was not upgraded.

Sampling matches the approved defaults: temperature 0.9, top-k 50, top-p 1.0, repetition penalty 1.05, sampling enabled; subtalker sampling enabled, temperature 0.9, top-k 50, top-p 1.0; max new tokens 8192; `non_streaming_mode=False`, `x_vector_only_mode=False`, language English. Initial section seed is 1234; deliberate regeneration chooses and saves a different seed before inference. Exact reference text and actual inference text are recorded with the attempts/versions. Runtime model loading is local-only; code and model checksums must match before generation.

The approved Voice C reference remains byte-identical, SHA-256 `fc03ae6e7225642e8cf83e5160aff1d7f0b3cf17e23045c006d945bdc8b93931`. This saved reference is 48 kHz; Qwen handles reference conditioning as in the benchmarks and returns 24 kHz narration. New uploads retain their original source file and use the application's existing mono/24 kHz decoding pipeline. The confirmed transcript is stored separately from the original profile and snapshotted into new projects.

### Tests and results

Evidence root: `benchmarks/results/qwen-integration/2026-11-18/`.

- **64 automated tests passed**, including source/inference separation, immutable raw versions and parameters, legacy generation/regeneration rejection, legacy stale-take export, transcript snapshots, invalid uploads/paths/origins, one-job concurrency, failed generation, interrupted-state recovery, exact trailing-only cuts, processed/unprocessed WAV/MP3/ZIP exports, checksum failures, low-VRAM rejection, setup guards, and source-only package privacy/integrity checks. Command: `.venv-qwen3\Scripts\python.exe -m pytest -q`; output: `tests.log`.
- **Frontend typecheck and production build passed.** The new inference/legacy states retain the existing layout. Headless Chrome also checked narrow-screen overflow and page errors.
- **Readiness passed**: `pip check`, approved source checksums, all model asset hashes, CUDA computation on RTX 4070 Laptop 8 GB, and FFmpeg 7.1 availability. Output: `readiness.log`.
- **Real Chrome + CUDA workflow passed** against isolated data: reference upload/transcript, project creation, all three sections generated, active-job reload/reattachment, actual audio playback during polling, individual section regeneration, old/unrelated raw preservation, original-script preservation, WAV and MP3 exports at 1.10×, selected ZIP export, unprocessed export, volume adjustment, settings reopening, and reference changes affecting only future projects. No browser external requests or page errors. Report: `test-results/react-migration/8011fde7d7/report.json`; screenshots retained there. Verification-only server code blocked external Python sockets; inference used no network.
- **Restart/recovery passed**: the same isolated project reopened after restarting the server, with its narrator transcript, recordings, and exports intact. A simulated interrupted manifest retained its last seed and previous audio, became pending/stale, and did not regenerate automatically. Graceful between-section interruption is covered separately by automated tests. This is not a physical power-loss or hard-kill-during-CUDA test.
- **Real legacy recording compatibility passed** using an isolated copy of a saved Chatterbox project: browser playback and original-speed export produce identical decoded samples, neither loads a model, and generation/regeneration return 409. `legacy-compatibility.json` and `legacy-ui-verification.json` record the checks. The running legacy UI has read-only generation text, disabled generation controls, and enabled export controls.
- **Actual generated words checked locally** with the existing pinned Whisper pipeline, without expected-text prompting. Both decoders report zero word differences in the three-section browser narration and in the final exact-reference live sample below. ASR remains diagnostic; this does not certify every future word or subjective naturalness.
- **Preservation passed**: all 24 pre-existing data files and all 119 legacy environment versions are unchanged. The running frontend returns HTTP 200 and the backend health identifies Qwen, idle after verification. `final-verification.json` records these results.

The old test harness's secondary-thread Uvicorn shutdown needed cleanup after the browser phase. The harness now uses the same main-thread server pattern as production; its subsequent restart/recovery and shutdown completed. Windows may log a connection-reset callback when Chrome cancels audio requests; this did not corrupt recordings or fail the workflow.

### New live verification project and samples

A new project named **Qwen integration verification**, ID `b9297d78-d035-4b1b-be98-8000718f4bed`, is available in the running application. It uses the existing, unconverted Voice C reference and the confirmed transcript. Original source:

> The archive contains 17,400 files. Each observation is checked carefully, and every original recording remains safely stored.

An explicit inference override replaces only `17,400` with `seventeen thousand four hundred`. The original script/section remains unchanged; no automatic rewriting occurs. One first take, seed 1234, was generated through the real `/api/projects` → section override → generation job → export workflow. It produced **11.280 s** of raw narration in **56.800 s**, peaking at **2.754 GiB allocated / 3.207 GiB reserved** GPU memory, with 141 codec frames and no token-cap/OOM failure.

| Actual application artifact | Listening file |
| --- | --- |
| Original 1.00× recording | [Raw WAV](../benchmarks/results/qwen-integration/2026-11-18/voice-c-live_raw_1.00x.wav) |
| Processed 1.10× export, 10.265 s | [WAV](../benchmarks/results/qwen-integration/2026-11-18/voice-c-live_1.10x.wav) |
| Processed 1.10× export, 10.265 s | [MP3](../benchmarks/results/qwen-integration/2026-11-18/voice-c-live_1.10x.mp3) |

Both unprompted Whisper decoders recover the intended wording, including `17,400`, with **zero normalized word differences**. No excessive tail was detected in this particular take, so its enabled trim option recorded zero removed samples; synthetic/API tests verify the long-tail branch and preserve interior pauses. Exported files were decoded and checked, with original raw hashes intact. `live-project-verification.json` records the actual job, parameters, reference hash, version, and exports. The separate browser workflow produced approximately 20.659 s WAV/MP3 masters from its three sections.

### Run and remaining limits

The updated app is already running at **http://127.0.0.1:3000**, with FastAPI on **http://127.0.0.1:8000**. To start it yourself later, run `.\dev`; for the built interface run `start.bat` and use port 8000. Keep the launcher terminal open. Stop an older backend before switching code/environments. The current development launcher logs and PID are saved under the evidence root; existing servers are reused by `.\dev`.

Known limits:

- Narration can still mispronounce names/numbers or substitute words. Use explicit inference overrides, deliberate regeneration, and listening review. No Dessa-level or universal word-accuracy claim is made.
- Trailing-silence detection is a conservative threshold heuristic on processed copies, not semantic pause detection. It never edits an internal pause or raw WAV; disable it when a quiet ending should be retained. Qwen's internal decoder clamping remains upstream behavior, not repaired by export attenuation.
- The validated target remains native Windows with NVIDIA CUDA/8 GB VRAM. Memory guards and OOM handling preserve prior recordings; they cannot prevent other GPU applications from consuming memory mid-generation.
- Optional upstream FlashAttention/SoX warnings remain benign for the tested SDPA/12 Hz path. The pinned FastAPI test client emits an httpx deprecation warning; no dependency upgrade was introduced to suppress it.
- Source-only package integrity/extraction was tested; a full empty-cache installation and another physical PC were not tested in this integration.

No multi-model UI, new service, database, cloud API, automatic script rewriting, or emotion controls were added. Qwen is approved and active for new narration; existing Chatterbox projects remain intact and never silently switch generation identity.
