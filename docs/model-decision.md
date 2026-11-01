# Model decision — measured comparison complete; listening gate open

**Proposed engine for review: Chatterbox Turbo, conditional on human quality scores.** It clones the supplied, consented recording, completes long narration on this GPU, and repeats the seeded neutral clip exactly after restart. Its measured long-case RTF is 0.297 versus original Chatterbox's 0.613, with similar memory use. This is a technical proposal, **not a claim that Turbo sounds better**. Quality has priority: select original Chatterbox instead if listening shows better naturalness, pronunciation, or voice identity. Speed only breaks a quality tie. No production engine is approved yet, and no Phase 2–4 application code has been built.

All three candidates now have actual CUDA speech benchmarks on this laptop, with the same source texts/chunks, short and long WAVs, separate-process repeats, and saved numerical evidence. Reference consent is no longer a blocker. Human naturalness, pronunciation, similarity, and artifact scores remain unassigned.

Start with the [randomized listening comparison](listening-review.md) before reading `listening-key.json` if you want to avoid knowing the model labels. The full measured data is in [benchmark-results.json](benchmark-results.json); exact commands are in [the benchmark README](../benchmarks/README.md).

## Actual environment and reproduction

- Windows 11 build 26300; Python 3.12.2, native Windows, isolated Kokoro and Chatterbox virtualenvs. Both pass `pip check`.
- NVIDIA GeForce RTX 4070 Laptop GPU: **8,188 MiB total VRAM**, 7,948 MiB free at the initial detailed probe; driver 560.81. No other TTS model was run concurrently during speech generation.
- Driver-reported CUDA compatibility is 12.6; tested PyTorch/torchaudio are **2.6.0+cu124**, with bundled CUDA runtime 12.4. CUDA matrix multiplication returned finite results in both environments.
- Physical RAM measured: 42,676,903,936 bytes (~39.75 GiB). Initial free disk ~214 GiB; probe JSONs retain measured disk values after setup.
- FFmpeg was initially absent from PATH; virtualenv-local FFmpeg 7.1 is available via imageio-ffmpeg. No global driver/PATH changes, WSL2 installation, Docker, or production server were introduced.
- A **2.175-second CUDA TTS smoke** passed before larger candidate weight downloads. The complete benchmark runs with Hugging Face/Transformers offline mode enabled; no cloud speech service is used.

Environment and setup evidence: `environment-initial.json`, `environment-cuda.json`, `environment-final.json`, `environment-chatterbox.json`, `setup-notes.md`, pinned locks and installation reports. Candidate TTS/preset assets total **6,507,117,219 bytes**, cached outside the repository at `%TEMP%\local-youtube-tts-cache`. Download receipts retain per-file SHA256s; all eight LFS weight/preset hashes match the archived official hashes.

| Candidate | Exact weight revision | Downloaded assets | Tested code |
|---|---|---:|---|
| Original English Chatterbox, ~500M | `5bb1f6ee58e50c3b8d408bc82a6d3740c2db6e18` | 3,191,859,618 bytes | Chatterbox 0.1.7, official commit `5de7a54aa4e5e2baadb0182dde554908b48b85c2` |
| Chatterbox Turbo, ~350M | `749d1c1a46eb10492095d68fbcf55691ccf137cd` | 2,987,519,599 bytes | Same pinned Chatterbox code, separate adapter |
| Kokoro 82M v1.0 | `f3ff3571791e39611d31c381e3a41a3af07b4987` | 327,738,002 bytes | PyPI Kokoro 0.9.4; wheel URL/hash and bundled license archived |

Original English uses the original `t3_cfg` checkpoint, not the multilingual checkpoints that share its repository. Perth is pinned to official commit `ff1c8ac55a976971245cdd53c18d6131ca00d993`; upstream watermarking is retained. No model training, voice-design feature, or additional engine was added.

## Shared voice and method

The user supplied `record-sample.ogg` and expressly confirmed: “Yes, it’s my voice and I permit cloning and commercial publication.” The recording is mono, 48 kHz, **19.1135 seconds**. It was decoded to float WAV without trimming, gain changes, or denoising. Both cloning engines use the same converted file, SHA256 `fc03ae6e7225642e8cf83e5160aff1d7f0b3cf17e23045c006d945bdc8b93931`. Provenance, original hash, measurements, exact confirmation, and timestamp are in `reference-inspection.json`; runtime WAV and consent JSON are in gitignored `benchmarks/results/reference/`.

Kokoro uses its official `af_heart` preset at speed 1. **It does not clone or match the supplied narrator**, so its reference-similarity score is N/A. This preset-versus-clone comparison is not strictly apples-to-apples. It remains useful as a lightweight naturalness/speed baseline, but it does not establish a unique narrator identity.

Every candidate receives the same authored scripts and sentence chunks (~350 characters for this corpus). The long script is 913 words / 19 chunks. Seed is 1234. Chatterbox adapters use pinned upstream defaults; actual parameters are saved in each report. All output is native **24 kHz mono float WAV**, preserving raw values without processing, inserted pauses, loudness matching, or music. Individual chunks and concatenated clips are retained.

## Local long-form result

RTF = generation seconds / audio seconds; lower is faster. Generation includes text/reference preparation and synchronized inference; model load and WAV file writing are separately recorded. Each entry is one observed run, not a statistical estimate.

| Candidate | Audio length | Generation | RTF | Peak allocated / reserved during long case |
|---|---:|---:|---:|---:|
| Original English Chatterbox | **5:16.680** | **193.992 s** | **0.6126** | **3.548 / 4.473 GiB** |
| Chatterbox Turbo | **6:20.600** | **113.126 s** | **0.2972** | **3.298 / 4.564 GiB** |
| Kokoro, preset | **6:00.475** | **6.024 s** | **0.0167** | **0.956 / 1.523 GiB** |

All three completed a 5–10-minute output without a crash or GPU OOM. Differences in spoken duration are observed model behavior and may reflect speaking rate or other content differences requiring listening; no word-accuracy inference is made from duration alone. Turbo generated this same input in about 58% of original Chatterbox's generation time and had about half its RTF. This supports a runtime comparison, not a quality ranking.

Model load within these benchmark processes took 11.544 s for original Chatterbox, 11.106 s for Turbo, and 4.379 s for Kokoro. Python/PyTorch startup occurs before this timer. The earlier original load-only check took 34.050 s, illustrating why cold/cache conditions must not be ignored. Long-case wall times including file writing were 194.209 s, 113.392 s, and 6.290 s respectively; full precision is retained in JSON.

Across all measured speech cases, maximum allocated/reserved peaks were approximately **3.700 / 4.473 GiB** for original Chatterbox, **3.763 / 4.564 GiB** for Turbo, and **1.053 / 1.523 GiB** for Kokoro. Turbo is not shown to have lower peak inference memory across every case. These are **PyTorch CUDA allocator** statistics, excluding driver/context and non-PyTorch allocations; reserved memory can carry over between cases. They are not whole-device VRAM high-water measurements.

## Short cases and restart

Each cell gives **audio seconds / generation seconds / RTF**. The neutral case is the first generation after loading; later cases reuse the model. First-call and cache overheads are not normalized away.

| Case | Original Chatterbox | Turbo | Kokoro preset |
|---|---|---|---|
| Neutral explainer | 35.240 / 34.974 / 0.9924 | 43.600 / 14.743 / 0.3381 | 41.400 / 1.255 / 0.0303 |
| Documentary/dialogue | 33.400 / 20.381 / 0.6102 | 46.160 / 14.435 / 0.3127 | 38.575 / 0.650 / 0.0169 |
| Numbers/names/acronyms | 43.080 / 26.896 / 0.6243 | 58.800 / 18.672 / 0.3175 | 54.225 / 0.941 / 0.0174 |
| Neutral in new process | 35.240 / 24.074 / 0.6832 | 43.600 / 14.427 / 0.3309 | 41.400 / 1.365 / 0.0330 |

All three seeded neutral repeats have **exactly identical decoded PCM** to their corresponding first neutral sample, produced in separately recorded process IDs. This is numerical repeatability for the same seed/text/reference. It is not a naturalness rating or proof of identity consistency across different texts or arbitrary seeds. WAV container hashes can differ independently of decoded PCM; PCM hashes are used for restart comparison.

## Validation and artifacts

All **15 main-case WAVs** (five cases per model) passed decoding, sample-rate, duration, finite-sample, file-hash, and summed-segment-duration checks. Shared source-text hashes, chunk sequences, and the two cloning references match. No synthesis exception, NaN/Inf, empty output, entirely silent clip, or OOM occurred. `validation-summary.txt` and `benchmark-results.json` preserve the evidence.

No listening or speech-to-text word verification is claimed. Wrong or missing words, repeats, unnatural pauses, speaker drift, and audible artifacts still need human review. The reference has eight slightly over-full-scale decoded samples (peak 1.0063); upstream original Chatterbox logged a normalized-range warning after resampling. Float conversion preserved the reference rather than clipping it. This warning is recorded, not scored as an audible defect.

Raw model outputs: `benchmarks/results/{chatterbox,turbo,kokoro}/{neutral,documentary,pronunciation,long,restart}.wav`, with separate raw segment directories and per-case JSONs. The [listening review](listening-review.md) links 15 unchanged raw copies under randomized A/B/C labels, with an empty score sheet; the mapping is in `listening-key.json` for use after rating. Candidate identity is only partly concealed because the preset and cloned voices differ.

## License decision and remaining gate

The exact official model cards declare **MIT** for both Chatterbox variants and **Apache-2.0** for Kokoro. Exact code license texts, weight declarations, revisions, dependency license files, binary/auxiliary checkpoint hashes, and restrictions are archived in [the license review](license-review.md). GPL/LGPL dependencies and FFmpeg binary obligations are recorded separately; the whole stack is not described as MIT/Apache-only. User reference rights are expressly attested. No blanket clearance of all training data, voice rights beyond that attestation, or monetized publication is claimed.

**Conditional proposal: review Turbo for the single production engine.** It satisfies the measured local cloning, runtime, numerical repeatability, and long-form execution requirements. Original Chatterbox remains a viable alternative if it wins on sound. Kokoro is a strong measured performance baseline and a possible preset option only if the narrator-uniqueness requirement is relaxed; it is not a cloning fallback implemented in an application.

The final gate remains open: human average naturalness >=4/5, narrator identity consistency >=4/5 across different segments, no frequent omissions/repeats or major artifacts, and your review of the candidate. Fill the randomized or model-named listening score sheet and report the preferred voice. **Do not interpret this technical proposal as a passed subjective-quality gate or authorization to implement Phases 2–4.** No production UI, backend, project manager, export workflow, or launcher has been built.
