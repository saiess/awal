# Local YouTube TTS — Codex Implementation Plan

**Version:** 1.0  
**Research date:** 2026-11-01  
**Purpose:** Create a local, simple, high-quality English YouTube narration application using one commercially usable TTS model and one recognizable narrator voice.

## 1. Decision record (locked)

- Primary use: production of narrated YouTube Shorts, standard videos, and long-form videos; prospective monetization.
- Priorities, in order: natural human-sounding narration; narrator identity and consistency between segments/videos; fidelity and reliability; reasonable local runtime. Real-time streaming is unnecessary.
- Language in v0.1: **English**. Multilingual/cross-language cloning is a later possibility, not a v0.1 requirement.
- One saved narrator identity. Obtain only recordings you own or have explicit rights/consent to clone and publish commercially. An original AI voice is an alternative if supported. Do not train a custom model for v0.1.
- Primary workflow: paste script → auto-segment → generate → preview → edit/regenerate one section → export combined and individual WAV/MP3 files → reopen project later.
- Provide optional basic audio post-processing while retaining raw segment audio.
- Pronunciation: edit segment text and regenerate; **no pronunciation dictionary** in v0.1.
- Architecture: Python + FastAPI + vanilla HTML/CSS/JS; project folders and JSON manifest; no database, React, Docker, authentication, SaaS, cloud speech API, distributed queue, or multiple production TTS engines.
- Local hardware: NVIDIA RTX 4070 laptop, RAM 40GB; VRAM unknown until inspection. Windows native preferred if compatible; WSL2 only if justified by measured/model compatibility.
- Verify licenses of **exact weights, code dependencies, speaker samples, and reference audio** before production. Do not claim blanket legal clearance for a generated voice merely because weights are permissively licensed.

## 2. Research shortlist (NOT yet benchmarked on user's machine)

| Candidate | Official source | License shown by official model card | Role | Notes |
|---|---|---|---|---|
| Chatterbox (original English) | https://huggingface.co/ResembleAI/chatterbox | MIT | Quality/voice-cloning leading candidate | 500M-class, prompt/reference audio for zero-shot voice cloning and expressive controls. Confirm version, dependencies, actual performance on local GPU. |
| Chatterbox Turbo | https://huggingface.co/ResembleAI/chatterbox-turbo | MIT | Efficient clone-capable comparator | 350M-class, English, reduced compute. Test narration stability and style, not merely speed. |
| Kokoro 82M | https://huggingface.co/hexgrad/Kokoro-82M | Apache-2.0 | Lightweight quality/speed comparator | Preset voices, not equivalent to prompt-based unique speaker cloning. Use as baseline; uniqueness limitation must be explicit. |

**Excluded from main benchmark:** Standard official F5-TTS pretrained weights are CC-BY-NC, despite MIT-licensed code (https://github.com/SWivid/F5-TTS). Fish Speech licensing is version-specific and more conditional; do not treat it as a blanket permissive option (https://github.com/fishaudio/fish-speech/blob/main/LICENSE).

**Important:** Model cards are evidence of declared licenses, not a guarantee about all training material, voice rights, or future license changes. Codex must log the exact revision, license files, and checks performed. The 3 candidates have **not** been tested on this user's machine. Chatterbox is a provisional preference, not a confirmed winner.

## 3. Success criteria and non-goals

### Definition of success

A user can install and launch locally, choose a single saved narrator, generate natural English audio from a 5–15-minute script, preview/edit/regenerate a single section without modifying unrelated section files, preserve a project across restarts, and export a clean master WAV, MP3, and selected/individual WAV files. Shorts and 20–60+ minute scripts should be processed through the same segmentation workflow; lengthy scripts need not be real-time.

### Non-goals in v0.1

Full audio editor, timeline, speech-to-text verification service, phoneme dictionary, batch channels, multilingual UI, cross-lingual cloning, custom voice model training, cloud deployment, login, database, multi-user use, background daemon, Docker, REST streaming, emotional scene editor, and general voice marketplace.

## 4. Phases and Codex tasks

### Phase 0 — Inspect the environment and pin a baseline

**Tasks**
1. Run `nvidia-smi`; log GPU name, driver, VRAM total/free, CUDA availability. Do not assume 8GB despite typical laptop configuration.
2. Record OS, Python, available disk space, FFmpeg binary, GPU PyTorch test, and compatible `torchaudio` version. Use a supported Python minor version determined by model packages (do not guess dependency compatibility).
3. Set up virtual environment, `requirements`/lock with pinned versions. Avoid global environment changes. Create `scripts/check_environment.py` with JSON/text output.
4. Test a 2-second simple inference smoke check before downloading all candidates. Cache models outside the git repository; document download size and location. No download scripts from untrusted mirrors.
5. If native Windows fails for a technical reason, document the error and try WSL2; don't introduce Docker automatically.

**Acceptance:** script reports platform, VRAM, CUDA, FFmpeg, Python; logs include actual errors, setup is reproducible; GPU inference demonstrably works or reports a specific blocker.

### Phase 1 — Lightweight 3-model benchmark / selection gate

**Tasks**
1. Create a tiny `benchmarks/` runner, separate from final app, with isolated candidate adapters/scripts as needed. Installation can use separate virtualenvs if dependency versions conflict.
2. For each candidate, record official model repository, exact revision/hash, LICENSE text/link for code and weights, dependency restrictions, reference-audio provenance, commercial-use note, model size, install instructions. **Stop and flag any unclear commercial rights** rather than silently choosing it.
3. Prepare the **same** test scripts for all candidates: (a) ~45-second neutral explainer; (b) ~45-second engaging documentary with dialogue/punctuation; (c) numbers, acronyms and difficult proper nouns; (d) 5–10-minute narration; (e) repeated generation in a newly started process/session. Use the same target narration voice when possible; document preset-vs-clone comparison as not strictly apples-to-apples.
4. For cloning-capable models, use one clean 10–30-second consented voice reference (or follow model's official recommended range). Record reference identity and consent status. Where supported, test voice-generation methods with minimal effort; do **not** implement model training.
5. Log GPU peak VRAM, inference wall time, generated audio duration, real-time factor = generation_seconds/audio_seconds, failures/NaNs, and output sample rate. Capture outputs in `benchmarks/results/<model>/<case>.wav`.
6. Listen blind where possible and rate each 1–5 for naturalness, pronunciation, stability across segments, similarity to reference, and objectionable artifacts. Evaluate voice identity again after process restart. Speed is tie-breaker after quality/reliability.
7. Select a **single** final engine and save the rationale to `docs/model-decision.md`. If none meets acceptable quality or GPU constraints, stop and report the evidence instead of proceeding with poor audio.

**Suggested qualitative gate:** average naturalness >=4/5; narrator identity >=4/5 across separately produced segments; no frequent dropped/repeated words or major artifacts; 5–10-minute script completes without crash. These are project acceptance targets, not claims about a model.

**Acceptance:** 3 (or fewer if a hard eligibility constraint excludes one) reproducible candidate reports; comparative audio files; exact license/revision records; choice and reasons; no production UI code before the gate.

### Phase 2 — Minimal backend and one-engine implementation

**Tasks**
1. Implement single selected engine in `app/tts/engine.py` using an interface: `load()`, `synthesize(text, narrator_reference, options) -> AudioResult`. Only one production implementation. Support lazy model initialization and singleton reuse for local requests.
2. Build FastAPI app binding by default to `127.0.0.1` only; enable Swagger docs in local mode. One generation at a time with explicit `busy` status (a single in-process worker is sufficient). Use `run_in_threadpool` or similar so API doesn't freeze; don't pretend synchronous GPU generation is cancelable when it isn't.
3. Save one narrator profile containing `id`, `label`, `reference_audio_relative_path` (nullable), `engine_id`, `engine_revision`, `engine_parameters`, `created_at`. If using a preset, record voice identifier instead. Keep the narrator profile immutable for already generated project files unless the user explicitly changes it.
4. Segment input text using paragraphs + sentence-aware splitting with configurable maximum characters. Preserve punctuation and text order; avoid breaking abbreviation, decimal, or quoted sentence unnecessarily. Prefer conservative chunks: model constraints override any guessed size.
5. Provide project folder and manifest JSON. Generate sections one by one; record `pending | generating | ready | failed`, raw audio path, edited text, parameter snapshot, audio duration, error, and generation timestamp. Write manifests atomically (temp file then replace).
6. Enable regenerating an individual segment. Use stable segment IDs, only replace target segment files after successful generation. Previous good audio remains intact on failure. Export always uses current selected ready segment versions.
7. Normalize all working files to a consistent PCM WAV format for concatenation; use chosen sample rate, channel count, and validated audio durations. Export combined WAV and MP3 via a local FFmpeg process; provide combined plus individual segments. Insert small configurable pauses at boundaries, avoiding accidental double-silence. Avoid altering model output beyond simple conservative optional processing.
8. Implement output normalization/peak limiting as optional export-only path. Never destroy original raw WAV. Use bounded peak control and loudness target with sanity checks (do not hard-code aggressive compression); document actual FFmpeg filter behavior.
9. Protect local filenames and access: strict IDs or UUIDs, safe-path resolution inside project root, no arbitrary file reads, size/text length caps, sanitized upload filenames, `Content-Type` restrictions and audio decode validation for reference clips. Only allow upload of permitted reference audio.

**Acceptance:** API passes mocked TTS tests without downloading models; single-model integration smoke succeeds; modified segment doesn't alter other segment audio hashes; process restart/reopen preserves project; failed regeneration doesn't lose valid existing audio; exports are decodable and duration approximately equals sum of segments + intended gaps; raw WAV remains unmodified.

### Phase 3 — Minimal browser UI

**Tasks**
1. FastAPI serves static assets and a single HTML page at `/`. Vanilla JS fetch API; no React or bundler.
2. Page: project title, large script textarea, narrator selector (one saved profile), Generate button, progress/current section, list of sections showing text/preview/edit/regenerate, master preview, Export WAV / Export MP3 / Export segments, Open existing project.
3. On Generate: segment/preview script first; explicit confirmation before overwriting existing project content. Show failure per segment and allow retry. Display GPU initialization errors intelligibly.
4. Ensure user can change one sentence in the section editor and regenerate that section. Do not auto-regenerate the whole video. Show when a section's audio is stale relative to edited text.
5. Provide clear UI state: idle/loading/generating/ready/failed. Simple layout, keyboard accessible buttons/labels, responsive enough for a laptop browser.

**Acceptance:** complete 5–15-minute demo script flows from paste to export locally; one segment can be regenerated from browser; reload/reopen project retains all settings and rendered segments; no cloud requests are necessary after model dependencies are installed/cached.

### Phase 4 — Quality, packaging, and release v0.1

**Tasks**
1. End-to-end test using at least a 5-minute script and optionally a 20–30-minute stress test. Record narrator similarity and visible defects. Spot-check first, middle and last sections, repeated across app restarts.
2. Add commands `start.bat` (Windows) or `start.sh` (WSL2) and a README with first-run downloads, GPU check, reference-audio instructions, local URL, troubleshooting, sample exports, and disk/cache paths.
3. Ensure safe shutdown while a segment is processing: completed segments remain usable; interrupted section is marked pending/failed on restart. No full re-render needed.
4. Test Windows-native and WSL2 only if one was chosen; avoid asserting cross-platform support not actually tested.
5. Record license verification in `THIRD_PARTY_NOTICES.md` including exact downloaded weight revision, licenses and any attribution obligations, plus a voice-reference consent reminder. Confirm commercial permissibility again immediately before monetized publishing.
6. Freeze dependencies at known compatible versions. Document production model choice and fallback **decision** (not a second engine implementation).

**Acceptance:** single command startup after initial setup; successful E2E demo; no external TTS service; stable single narrator; restart/resume; WAV/MP3 exports work; licensing file and manual QA checklist present.

## 5. Simple architecture

```text
Local browser (HTML/CSS/JS)
     |
     | localhost HTTP / REST
     v
FastAPI (one Python process)
  ├── Projects (manifest JSON + script text)
  ├── Segmentation / single generation worker
  ├── Chosen TTS engine (model loaded once on NVIDIA GPU)
  ├── Segment WAV storage (raw + versioned)
  └── FFmpeg exporter (combined WAV/MP3 + optional enhancement)

Local filesystem:
  data/
    narrators/<id>/profile.json
    narrators/<id>/reference.wav             # only if licensed/consented
    projects/<project_id>/project.json
    projects/<project_id>/segments/<segment_id>/v001_raw.wav
    projects/<project_id>/segments/<segment_id>/v002_raw.wav
    projects/<project_id>/exports/master.wav
    projects/<project_id>/exports/master.mp3
```

**No database**: manifests are atomic JSON. **No general task queue**: only one in-process TTS job at once. For large inputs, generation is asynchronous from the browser's perspective through job polling; not a distributed/streaming architecture.

## 6. Proposed API contract (v0.1)

All endpoints local-only. Response data shown here is **proposed application design**, not an existing library API. Use JSON with documented validation/error responses. Prefer stable UUID identifiers. Audio download routes use file responses.

| Method | Path | Input | Output / behavior |
|---|---|---|---|
| GET | `/api/health` | — | `{status, engine_loaded, gpu_available, active_job}` |
| GET | `/api/narrators` | — | `[{id, label, mode, engine_id}]` |
| POST | `/api/narrators` | multipart: `label`, `reference_audio?`, `preset_voice_id?` | Creates one saved narrator. One of `reference_audio` or `preset_voice_id`, based on chosen engine. Require self-attested rights flag for uploads. |
| GET | `/api/projects` | — | Array of `{id, title, updated_at, segment_count}` |
| POST | `/api/projects` | `{title, script, narrator_id}` | Creates project and automatically segments script; returns project JSON. |
| GET | `/api/projects/{project_id}` | — | Project + ordered segment metadata. |
| PATCH | `/api/projects/{project_id}/segments/{segment_id}` | `{text}` | Updates only section's text, marks audio stale. |
| POST | `/api/projects/{project_id}/generate` | `{only_missing_or_stale: true}` | Enqueues one local generation job; returns `{job_id, status:"queued"}` or `409` if busy. |
| POST | `/api/projects/{project_id}/segments/{segment_id}/regenerate` | `{}` | Same worker, just target section; returns job ID. Never lose previous good file on failure. |
| GET | `/api/jobs/{job_id}` | — | `{id, status, done_segments, total_segments, active_segment_id, error?}` |
| GET | `/api/projects/{project_id}/segments/{segment_id}/audio` | — | Current section WAV bytes, or 404 if none. |
| POST | `/api/projects/{project_id}/exports` | `{format:"wav"|"mp3", enhance:false, include_segments:false}` | Validates complete current segments; creates export; returns export ID/path. |
| GET | `/api/projects/{project_id}/exports/{export_id}/download` | — | Audio/ZIP file response, validated path. |

**Sample project manifest (illustrative)**

```json
{
  "schema_version": 1,
  "id": "6a91c8bf-3b99-45f0-ac4a-689d77e2e802",
  "title": "Volcano documentary episode",
  "language": "en",
  "narrator_id": "narrator-main",
  "engine_id": "selected-engine",
  "engine_revision": "verified-pinned-revision",
  "script": "Imagine a city built beside a sleeping volcano...",
  "segments": [
    {
      "id": "segment-001",
      "order": 0,
      "text": "Imagine a city built beside a sleeping volcano...",
      "status": "ready",
      "stale": false,
      "audio_path": "segments/segment-001/v001_raw.wav",
      "duration_seconds": 3.6,
      "generation_parameters": {}
    }
  ]
}
```

Suggested errors: `400` invalid request, `404` unknown IDs, `409` worker busy or incomplete export, `413` oversized script/reference, `422` validation, `500` internal failure with sanitized user-facing detail and local diagnostic log. Ensure project state consistency on errors.

## 7. Test plan

### Automated unit tests (pytest)

- Script segmentation keeps order and punctuation; doesn't produce empty segments; handles blank lines, quotes, abbreviations, decimals, Unicode and very long sentences.
- Validation rejects empty/oversized scripts, unknown narrator, unsupported audio format, traversal (`../`), invalid UUIDs, and corrupt reference samples.
- Manifest write atomicity and schema round-trip; restart recovery resets a stale `generating` state safely.
- Segment edit marks audio stale; regeneration changes only the target file reference; failed generation preserves last valid WAV and reports staleness.
- Mocked engine test catches errors, audio sample-rate mismatch, silent/NaN results and memory/initialization failure.
- Export order correct and durations within reasonable tolerance; MP3 decodable; unprocessed originals retained; safe filename/path routing.
- Job state transitions accurate; second simultaneous generation returns `409` and does not corrupt output.

### Local integration and manual QA

- First-time setup on actual machine; GPU recognized and model loaded once.
- 45-second narration with names/numbers/acronyms; listen for errors.
- 5–10-minute multiple-paragraph test; narrator remains recognizable and no skipped/duplicated paragraphs.
- Restart process and generate another clip; repeatability check.
- Modify a middle section, regenerate, and compare SHA256 hashes of other sections before/after (identical).
- Complete master WAV/MP3 preview in common video editor; no harsh concatenation clicks or obviously inconsistent loudness.
- Optional 20–30-minute smoke/stress run; recover failed sections without restarting whole project.
- Disconnect network after model download: generation and export still function locally.

## 8. Minimal repository layout

```text
local-youtube-tts/
  README.md
  THIRD_PARTY_NOTICES.md
  requirements.txt                  # pinned after selection
  scripts/
    check_environment.py
    start.bat                       # or start.sh if WSL chosen
  benchmarks/
    README.md
    scripts/                       # short + long test text
    evaluate.py
    results/                       # gitignored
  docs/
    model-decision.md
    acceptance-checklist.md
  app/
    main.py
    api.py
    config.py
    models.py                        # Pydantic schemas
    projects.py                      # file/manifest service
    segmentation.py
    jobs.py                          # one-process worker
    tts/
      engine.py                      # only selected engine
    audio.py                         # WAV stitching + export
    static/
      index.html
      styles.css
      app.js
  tests/
    test_segmentation.py
    test_projects.py
    test_api.py
    test_audio.py
    test_jobs.py
  data/                               # gitignored
  .gitignore
```

## 9. Codex execution instructions — copy/paste

```text
You are implementing a LOCAL, SINGLE-USER YouTube narration TTS tool.
Read local_youtube_tts_codex_plan.md in full and follow its phases IN ORDER.
Do not overengineer: no Docker, database, React, cloud API, auth, background distributed queue, or multiple production engines.

STOP AFTER PHASE 1 before implementing the production application. Your first assignment:
1. Inspect the actual laptop GPU/VRAM/OS/CUDA/Python/FFmpeg capabilities.
2. Verify current upstream licenses of exact code AND weight revisions for Chatterbox original English, Chatterbox Turbo, and Kokoro 82M.
3. Create a reproducible small benchmark with identical narration tests and a consented voice reference where cloning is available.
4. Record VRAM, speed, failures, and produce WAV samples to listen to.
5. Write docs/model-decision.md with a comparison and proposed winner. Ask for human listening judgment if necessary; do not silently declare a subjective quality winner.
6. Report blockers, exact commands, outputs, and next actions.

After the model is approved, implement Phases 2–4. Use FastAPI + vanilla JS, local JSON files, one TTS engine, per-segment retry, raw WAV preservation, optional enhanced WAV/MP3 export, unit/integration tests, and a one-command local launcher.
Demonstrate each acceptance gate with actual test results; do not claim GPU tests or audio listening happened unless they really happened.
```

## 10. Risk register and mitigations

| Risk | Mitigation |
|---|---|
| Reference voice is not unique/rights unclear | Use own authorized recording or an officially licensed preset. Log provenance and consent; do not imitate an identifiable person without authorization. |
| Narrator shifts tone across chunks | Pin reference, engine revision and generation params; use conservative chunk size; listen across first/middle/last segments; selective regenerate. |
| GPU VRAM insufficient or dependency collisions | Inspect first; isolate candidate environments; use vendor-documented memory options; switch to WSL2 only for a confirmed reason. |
| Single short clip sounds good but 10-minute narration fails | Long-form and restart consistency are mandatory benchmark gates. |
| TTS skips, repeats, or misreads words | Compare script and audio manually during benchmark, retain source text, allow selective regeneration; no promise of flawless output. |
| Editing segment loses previously good output | Write audio to versioned temp file; validate then update manifest atomically. |
| Audio assembled with inconsistent format/loudness | Normalize sample format before concatenation; conservative optional loudness processing; retain original files. |
| Weights or components have noncommercial terms | Verify exact checkpoint + dependencies and maintain THIRD_PARTY_NOTICES; stop on unresolved conflict. |
| Monetization policies change | Review current YouTube synthetic-content and originality rules before publishing; permissive speech licenses do not guarantee monetization eligibility. |

## 11. Decisions intentionally deferred

- Which model wins (requires local listening/VRAM tests).
- Narrator cloned reference vs selected preset vs supported original voice creation (choose simplest effective approach during benchmark).
- Exact segment character limit, sample rate, loudness target, Python version, package versions, and Windows vs WSL2 (set from tested engine/docs, not guesses).
- Multilingual voice preservation, voice design, SSML, custom emotion editing, pronunciation dictionary, and additional providers (out of v0.1 scope).

## 12. Source links and verification record

Official primary sources consulted 2026-11-01:

1. Resemble Chatterbox repository and model family: https://github.com/resemble-ai/chatterbox
2. Original Chatterbox official model card (MIT): https://huggingface.co/ResembleAI/chatterbox
3. Chatterbox Turbo official model card (MIT): https://huggingface.co/ResembleAI/chatterbox-turbo
4. Kokoro 82M official model card (Apache-2.0): https://huggingface.co/hexgrad/Kokoro-82M
5. F5-TTS upstream code vs pretrained weights licensing: https://github.com/SWivid/F5-TTS
6. Fish Speech license version details (not selected): https://github.com/fishaudio/fish-speech/blob/main/LICENSE

The license statements above represent published source claims as of the review date; revisit them for the exact downloads before commercial use. No real user-device inference tests have been run as part of this research document.
