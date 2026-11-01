# Phase 0/1 acceptance record

Phase 0:

- [x] Actual GPU/VRAM/driver, OS, Python, disk, RAM inspected.
- [x] CUDA torch matrix operation and matching torchaudio import pass.
- [x] Isolated candidate environments; pinned resolved dependency locks and official source commits.
- [x] JSON/text environment probe and actual setup issues recorded.
- [x] ~2-second CUDA speech smoke passed before larger weight downloads.
- [x] Outside-repository model cache, sizes, revisions, and SHA256 records.
- [x] Windows native evaluated; no unresolved platform failure requires WSL2.

Phase 1:

- [x] Tiny benchmark runner and common authored scripts; no application/UI.
- [x] Three official weight/code license/revision records and resolved dependency inventories.
- [x] Native CUDA load checks for all three candidates.
- [x] Kokoro short/numbers/6-minute/restart raw WAVs and numerical metrics.
- [x] Consented target reference, identity, and rights confirmation supplied.
- [x] Original Chatterbox speech/long/restart benchmark and comparable WAVs.
- [x] Turbo speech/long/restart benchmark and comparable WAVs.
- [x] All 15 main-case WAVs validated; identical source texts/chunks and shared cloning reference verified.
- [x] All three seeded neutral repeats produce identical decoded PCM in separate processes.
- [x] Randomized raw listening copies and an unscored listening sheet prepared.
- [ ] Human listening scores and voice/artifact checks, blind where possible.
- [x] Decision report accurately separates observed evidence from pending gates.
- [ ] Single production engine selected and reviewed by user.

The computational Phase 1 comparison is complete. The selection gate remains **open for human listening scores and user review**. Chatterbox Turbo is the conditional technical proposal, not an approved quality winner. Phase 2–4 work has not started.
