# Local YouTube TTS: environment and model selection only

This workspace implements Phase 0 and the Phase 1 benchmark from `local_youtube_tts_codex_plan.md`. There is no production application. Reference consent is recorded; the production model selection gate remains open for human listening review and user approval.

- Results and proposed decision: [docs/model-decision.md](docs/model-decision.md)
- Reproduction commands: [benchmarks/README.md](benchmarks/README.md)
- License evidence and remaining limits: [docs/license-review.md](docs/license-review.md)
- Hardware probe: `scripts/check_environment.py` (JSON on stdout; optional `--output PATH`)

Windows native, Python 3.12.2, isolated virtual environments, no global Python or driver changes. Model cache: `%TEMP%\local-youtube-tts-cache`, outside this repository. It is a temporary-directory cache and may be removed by Windows cleanup; downloading again uses the recorded revisions. Audio and per-case reports are in gitignored `benchmarks/results/`; compact measured reports are retained in `docs/benchmark-results.json`.
