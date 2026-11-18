# Qwen3-TTS versus Chatterbox Turbo

> Historical results: superseded local audio/results were removed on 18 November 2026 at the user's request. Findings below describe the earlier experiment; retired paths are shown as text. Current listening files are in `benchmarks/results/CURRENT-section-12/`; see the [latest Qwen validation report](qwen3-long-form-validation.md).

Benchmark date: 18 November 2026. This experiment does not integrate Qwen into Awal.

## Compatibility and provenance

The experiment uses the official Base model, which supports reference-based voice cloning. It does not expose the natural-language delivery instructions available on other Qwen model variants. No emotion, emphasis, or speed instructions are invented or passed through an unrelated configuration field.

| Component | Pinned revision | Declared license |
| --- | --- | --- |
| Qwen code, qwen-tts 0.1.1 | `022e286b98fbec7e1e916cb940cdf532cd9f488e` | Apache-2.0 |
| Qwen3-TTS-12Hz-0.6B-Base | `5d83992436eae1d760afd27aff78a71d676296fc` | Apache-2.0 |
| Qwen3-TTS-Tokenizer-12Hz | `7dd38ad4e9bad454aae9cd937d0cd577604fe229` | Apache-2.0 |
| Chatterbox Turbo code 0.1.7 | `5de7a54aa4e5e2baadb0182dde554908b48b85c2` | MIT |
| Chatterbox Turbo weights | `749d1c1a46eb10492095d68fbcf55691ccf137cd` | MIT |

Primary sources: [official Qwen repository](https://github.com/QwenLM/Qwen3-TTS/tree/022e286b98fbec7e1e916cb940cdf532cd9f488e), [Base model card](https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base/tree/5d83992436eae1d760afd27aff78a71d676296fc), [tokenizer card](https://huggingface.co/Qwen/Qwen3-TTS-Tokenizer-12Hz/tree/7dd38ad4e9bad454aae9cd937d0cd577604fe229), [code license](https://github.com/QwenLM/Qwen3-TTS/blob/022e286b98fbec7e1e916cb940cdf532cd9f488e/LICENSE), and [pinned inference implementation](https://github.com/QwenLM/Qwen3-TTS/blob/022e286b98fbec7e1e916cb940cdf532cd9f488e/qwen_tts/inference/qwen3_tts_model.py).

Apache-2.0 and MIT permit commercial use subject to their notice, attribution, and applicable redistribution conditions. The narrator recording has existing explicit cloning/commercial-publication consent. These findings concern the inspected artifacts, rather than a blanket clearance for arbitrary reference recordings or redistributed software bundles.

The Base snapshot includes its speech tokenizer weights and configuration in `speech_tokenizer/`, plus its text tokenizer vocabulary and merges. The standalone tokenizer revision is recorded separately for provenance. Local inference must load the complete snapshot, rather than just the main safetensors file. Weight hashes are checked against the repository's LFS SHA-256 values.

Qwen is isolated in `.venv-qwen3` because its official code pins Transformers **4.57.3** and Accelerate **1.12.0**, while Awal's existing environment uses Transformers **5.2.0**. Both environments use Python 3.12 and PyTorch/torchaudio 2.6.0+cu124. The benchmark selects BF16 and PyTorch SDPA, avoiding a Windows FlashAttention build. Native Windows compatibility and GPU fit are determined by the actual run below, rather than assumed from these dependencies.

### Installed dependency licenses

The exact 90-package environment and its declarations are archived in [the installed inventory](licenses/qwen3-benchmark-installed/inventory.json), with 120 bundled distribution license/notice texts and supplemental native-library notices. No installed distribution lacks a license declaration. The complete resolved versions are in `qwen-freeze.txt`; `qwen-install.json` and `torch-install.json` retain package-source receipts. `pip check` reports no broken requirements.

| Runtime dependency | Exact version | License finding |
| --- | --- | --- |
| Transformers / Accelerate | 4.57.3 / 1.12.0 | Apache-2.0 |
| PyTorch / torchaudio | 2.6.0+cu124 / 2.6.0+cu124 | PyTorch BSD-3-Clause; torchaudio's bundled LICENSE is BSD-2-Clause. Bundled third-party/NVIDIA runtime terms also apply. |
| NumPy / SciPy | 1.26.4 / 1.17.1 | BSD-3-Clause plus bundled numerical-library notices |
| librosa | 0.11.0 | ISC |
| soundfile | 0.14.0 | BSD-3-Clause; bundled libsndfile has LGPL-2.1 terms |
| soxr | 1.1.0 | LGPL-2.1-or-later |
| Python sox wrapper | 1.5.0 | BSD-3-Clause; separate from a SoX executable, which is not installed for this benchmark |
| ONNX Runtime / einops | 1.32.0 / 0.8.2 | MIT |
| tokenizers / safetensors / Hugging Face Hub | 0.22.2 / 0.8.0 / 0.36.2 | Apache-2.0 |
| Gradio / Gradio client | 6.17.3 / 2.5.0 | Apache-2.0; official package dependencies only, with no second frontend or running service |

Remaining dependencies are covered individually in the inventory, including MPL-2.0 components such as certifi, orjson, and tqdm; LLVM-exception notices for llvmlite; and Python/CNRI notices. No noncommercial-only model or dependency declaration was identified. Copyleft and NVIDIA runtime terms still matter when distributing binaries: this local experiment does not produce a redistribution bundle. Soundfile's separate libsndfile COPYING and ONNX Runtime's LICENSE/ThirdPartyNotices are archived because a dist-info-only scan would miss them. See [Soundfile's upstream licensing documentation](https://python-soundfile.readthedocs.io/en/latest/) and [the CUDA 12.4 EULA](https://docs.nvidia.com/cuda/archive/12.4.1/pdf/EULA.pdf).

## Controlled comparison

Evidence root: `benchmarks/results/qwen3-vs-chatterbox/2026-11-18/`.

- The frozen `plan.json` and `scripts.txt` retain the exact harbor paragraph and original library sections 6 and 9. These total 205 normalized script words. Paragraphs contain complete sentences; no text is rewritten and the long harbor opening sentence remains intact.
- All configurations use the same 19.1135-second Voice C WAV, SHA-256 `fc03ae6e7225642e8cf83e5160aff1d7f0b3cf17e23045c006d945bdc8b93931`.
- The user confirmed Qwen's reference transcript: “Every day, small discoveries change the way we understand the world. Sometimes, the most interesting story begins with a simple question. Today, let's explore what happened, why it matters, and what we can learn from it.”
- Seed **1234** is reset for each passage. Equal seeds do not make different architectures sample equivalent outputs. One fresh-process repeat of library section 9 per configuration checks restart stability. There is no seed search or selection of a preferred take.
- Inference uses cached local assets with offline flags and a socket-connect guard. No cloud inference or audio upload occurs.

| Configuration | Actual settings and intended change |
| --- | --- |
| `chatterbox_C` | Temperature 0.9, top-p 0.95, top-k 1000, repetition penalty 1.2, reference loudness normalization enabled. CFG 0 and exaggeration 0 are retained in the call for parity; Turbo does not apply them as delivery controls. Paragraph-aware experimental boundaries; production remains unchanged. |
| `qwen06_default` | English, reference audio plus confirmed transcript, `x_vector_only_mode=False` (ICL cloning), `non_streaming_mode=False`. Official sampling defaults: temperature 0.9, top-k 50, top-p 1.0, repetition penalty 1.05, sampling enabled; subtalker sampling enabled, temperature 0.9, top-k 50, top-p 1.0. |
| `qwen06_fulltext` | Identical Qwen parameters and reference; only `non_streaming_mode=True` changes. The inspected implementation makes the full target text available in its ICL prompt layout. This is a justified context experiment, not an emotion parameter or a different model. |

Both Qwen modes return complete WAVs: the default flag describes the text-conditioning layout, not a benchmark of an audio streaming server. Qwen's saved default limit is 8192 new tokens; this short-passage benchmark explicitly caps it at **1024** to bound runaway generation. All other sampling defaults are unchanged. Generated codec-frame counts and any cap hits are recorded. The Chatterbox implementation has its existing 1000-step bound.

Raw WAVs are FLOAT and preserve the returned samples. Listening copies use a single constant-gain LUFS target with at least 1 dB sample-peak headroom across the comparison. They use no compression, tempo acceleration, silence removal, denoising, or pitch alteration. Combined masters use the same existing minimum 0.12-second boundary-gap method for all configurations. Individual files expose transitions within each paragraph without assembly effects.

## Results

**Completed:** all nine main passage takes and all three restart repeats generated successfully. No out-of-memory exception, generation exception, non-finite waveform, or Qwen token-cap hit occurred. All output is mono 24 kHz. No retries or alternative seeds were used.

### Listening files

Start with the three **level-matched 1.00× masters**, in this order within each file: harbor, library section 6, library section 9.

| Configuration | Listening master | Original 1.00× master |
| --- | --- | --- |
| Chatterbox C | Listen (retired local result: `../benchmarks/results/qwen3-vs-chatterbox/2026-11-18/listening/chatterbox_C__raw_1.00x_levelmatched.wav`) | Raw (retired local result: `../benchmarks/results/qwen3-vs-chatterbox/2026-11-18/chatterbox_C/raw_1.00x.wav`) |
| Qwen recommended ICL/default layout | Listen (retired local result: `../benchmarks/results/qwen3-vs-chatterbox/2026-11-18/listening/qwen06_default__raw_1.00x_levelmatched.wav`) | Raw (retired local result: `../benchmarks/results/qwen3-vs-chatterbox/2026-11-18/qwen06_default/raw_1.00x.wav`) |
| Qwen full-text layout | Listen (retired local result: `../benchmarks/results/qwen3-vs-chatterbox/2026-11-18/listening/qwen06_fulltext__raw_1.00x_levelmatched.wav`) | Raw (retired local result: `../benchmarks/results/qwen3-vs-chatterbox/2026-11-18/qwen06_fulltext/raw_1.00x.wav`) |

For focused review:

| Passage | Chatterbox C | Qwen default | Qwen full-text |
| --- | --- | --- | --- |
| Section 6 | Listen (retired local result: `../benchmarks/results/qwen3-vs-chatterbox/2026-11-18/listening/chatterbox_C__main__library_06_levelmatched.wav`) | Listen (retired local result: `../benchmarks/results/qwen3-vs-chatterbox/2026-11-18/listening/qwen06_default__main__library_06_levelmatched.wav`) | Listen (retired local result: `../benchmarks/results/qwen3-vs-chatterbox/2026-11-18/listening/qwen06_fulltext__main__library_06_levelmatched.wav`) |
| Section 9 | Listen (retired local result: `../benchmarks/results/qwen3-vs-chatterbox/2026-11-18/listening/chatterbox_C__main__library_09_levelmatched.wav`) | Listen (retired local result: `../benchmarks/results/qwen3-vs-chatterbox/2026-11-18/listening/qwen06_default__main__library_09_levelmatched.wav`) | Listen (retired local result: `../benchmarks/results/qwen3-vs-chatterbox/2026-11-18/listening/qwen06_fulltext__main__library_09_levelmatched.wav`) |

All paths above are relative to the project. The absolute listening directory is `C:\Users\saide\Desktop\awal\benchmarks\results\qwen3-vs-chatterbox\2026-11-18\listening`.

Individual original takes are `<configuration>/main/<passage>.wav`; the preserved fresh-process repeats are `<configuration>/restart/library_09.wav`. Level-matched restart copies are in `listening/`, with `__restart__library_09` in their names. `scripts.txt` contains the exact source paragraphs.

The common listening target is **−23.953606 LUFS**, chosen using the most restrictive individual passage's peak headroom. Every listening copy was checked to be the original samples multiplied by its documented constant gain, within FLOAT storage precision. Measured loudness is within 0.01 LU of target and sample peaks remain at or below −1 dBFS. No 1.10× acceleration is included in this comparison.

### Word fidelity diagnostics

The existing local `openai/whisper-small.en` validation checkpoint, revision `e8727524f962ee844a7319d92be39ac1bd25655a`, produced independent greedy and five-beam decodes without supplying the expected text as a decoder prompt. Normalization accepts spelling variants such as harbor/harbour and catalogue/catalog. Punctuation is excluded from word-edit counts, so these counts cannot validate sentence intonation or pause placement.

| Main passage | Normalized source words | Chatterbox C edits, greedy/beam | Qwen default | Qwen full-text |
| --- | --- | --- | --- | --- |
| Harbor | 69 | 0 / 0 | 0 / 0 | 0 / 0 |
| Library 6 | 69 | 6 / 6 | 1 / 1 | 1 / 1 |
| Library 9 | 67 | 4 / 4 | 0 / 0 | 0 / 0 |
| **Total** | **205** | **10 / 10 (4.88%)** | **1 / 1 (0.49%)** | **1 / 1 (0.49%)** |

These are **ASR edit rates**, not verified speech-error rates or overall quality scores. Restart repeats are excluded from the totals to avoid counting the same passage twice.

- Chatterbox section 6 again contains the diagnostic extra phrase “Sometimes the promising result leads nowhere.” The corresponding source phrase occurs once, with “first”; there is no source-text repetition to remove. Both Qwen transcripts contain the intended promising-result sentence once, with no extra phrase detected.
- Chatterbox section 9 is recognized as “Consider the chefs,” “maintained due,” and “a car nearby,” against “Consider the shelves themselves,” “maintained through,” and “a cart nearby.” Both Qwen modes transcribe the original wording, including “catalogue” and the final “a shelf,” with zero normalized word edits. This baseline does not reproduce the article substitution from the earlier alternative-seed experiments; their recordings remain untouched.
- **Both Qwen modes retain a review flag:** the opening of section 6 is recognized as “one of the **least** visible skills,” versus source “one of the **less** visible skills.” Both decoders agree. Listen to the first four seconds of the individual section 6 files. This could be synthesis substitution or shared ASR language-model bias; it is not cleared automatically and no additional generation was attempted.
- Neither Qwen transcript contains leaked reference narration, a missing ending, or a repeated passage. This is positive diagnostic evidence on these three paragraphs, rather than proof of perfect pronunciation or long-form reliability.

Full transcripts, every aligned mismatch, timing/level descriptors, and speaker vectors are retained in `diagnostics.json`.

### Natural delivery and narrator identity

No human listening winner is declared. The following measurements describe the samples; they do not establish expressive or Dessa-level delivery.

| Measure | Chatterbox C | Qwen default | Qwen full-text |
| --- | --- | --- | --- |
| Main master duration | 80.76 s | 80.16 s | 83.76 s |
| Harbor / section 6 / section 9 | 27.48 / 30.24 / 23.04 s | 25.76 / 27.76 / 26.64 s | 28.64 / 26.56 / 28.56 s |
| Quiet 10 ms frames below −45 dBFS | 20.49% | 15.58% | 18.95% |
| Speaker cosine to reference, harbor | 0.8633 | 0.9170 | 0.9518 |
| Speaker cosine to reference, section 6 | 0.8403 | 0.9377 | 0.9375 |
| Speaker cosine to reference, section 9 | 0.8484 | 0.9339 | 0.9257 |
| Section 9 restart | Sample-identical | Sample-identical | Sample-identical |

The speaker diagnostic reuses the existing Chatterbox voice encoder and its pinned `ve.safetensors`; no additional evaluation model was installed. Reference and generated audio are compared through the same 16 kHz embedding path. These values favor Qwen in this test, but the encoder is not an independent perceptual identity test, and scores have no established acceptance threshold here. The identical restart waveforms demonstrate repeatability on this machine for one passage per configuration, not across all hardware or arbitrary scripts.

Full-text conditioning changes timing despite identical sampling parameters. Its greater quiet-frame proportion than Qwen default could sound more deliberate or more hesitant; only listening establishes which. Chatterbox's repeated words also confound comparisons based on total duration. Quiet-frame totals do not distinguish meaningful pauses from distracting hesitations.

Listen specifically for:

1. Whether both Qwen modes still sound like the saved Voice C narrator, including accent, articulation, and tone across the three different paragraphs.
2. Whether the harbor opening has a coherent thought and an appropriate boundary between “opened their eyes” and “From the waterfront.” Both Qwen ASR transcripts attach that phrase to the preceding clause; this is a listening question, since ASR punctuation is not acoustic proof of a boundary error.
3. Whether “less,” “shelves themselves,” “through,” “cart,” “catalogue,” and “a shelf” are actually spoken accurately. Check emphasis on the two contrasting “Sometimes” sentences as well as the absence of repetition.
4. Whether full-text conditioning improves sentence continuity and varied cadence over default ICL, without sounding list-like, overemphasized, breathless, or hesitant. Check the transitions between the three assembled paragraphs and compare the restart copies.

### Performance and GPU fit

Hardware: **RTX 4070 Laptop GPU, 8188 MiB reported VRAM, compute capability 8.9, NVIDIA driver 560.81**. Windows, Python **3.12.2**, CUDA runtime **12.4** through the pinned PyTorch wheels. Models run sequentially.

| Main-run measurement | Chatterbox C | Qwen default | Qwen full-text |
| --- | --- | --- | --- |
| Load/runtime preparation | 14.84 s | 6.41 s | 6.38 s |
| Separate reference prompt preparation | Included in each generation | 10.72 s | 1.44 s |
| Three-passage generation total | 28.56 s | 140.47 s | 147.82 s |
| Generation seconds / output seconds | 0.354 | 1.752 | 1.765 |
| Peak PyTorch allocated VRAM | 3.550 GiB | 2.780 GiB | 2.805 GiB |
| Peak PyTorch reserved VRAM | 4.434 GiB | 3.482 GiB | 3.484 GiB |

Load timing starts after the common Torch import/CUDA initialization; it is not complete cold-process launch time. Chatterbox's load path includes its existing model checksum checks. Qwen prepares and reuses one clone prompt per process, while Chatterbox reprocesses the reference per passage. The first Qwen prompt preparation includes cold library/kernel work, making its 10.72 s versus the later 1.44 s unsuitable as a conditioning-mode speed comparison. No inference-speed change is proposed from these timings. Peak allocated/reserved numbers are PyTorch allocator measurements, not total driver/process VRAM.

The exact per-passage and restart measurements are in each `<configuration>/<main|restart>/measurements.json`. The fresh-process section 9 repeats are sample-identical to the corresponding main take in all configurations. Actual Qwen main-run codec lengths are 322/347/333 frames for default and 358/332/357 for full-text, well below the 1024-frame bound.

**1.7B practicality:** metadata only was inspected for `Qwen/Qwen3-TTS-12Hz-1.7B-Base`, revision `fd4b254389122332181a7c3db7f27e918eec64e3` (Apache-2.0). Its main model plus tokenizer weights total **4.228 GiB**, versus **2.339 GiB** for the 0.6B snapshot. The additional 1.889 GiB suggests roughly 4.7 GiB allocated / 5.4 GiB reserved if other costs stayed equal to this experiment. That is a rough feasibility estimate, **not a measured requirement**: larger KV caches and activations can increase it. A short-passage BF16/SDPA run appears plausible on an otherwise idle 8 GB GPU, but long-form fit and speed remain unverified. No 1.7B weights were downloaded. The 0.6B results justify listening first, rather than automatically expanding this benchmark.

### Technical issues and artifact checks

- Native Windows CUDA inference succeeded with SDPA and no FlashAttention installation. The official import emits an absent-FlashAttention warning; actual generation still completes.
- The Python sox package emits an absent-SoX-executable warning. The tested 12 Hz path generates successfully without that executable; none was installed.
- The existing reference contains eight FLOAT samples slightly above full scale, peak 1.006312 (about +0.055 dBFS). Qwen reports a reference-conditioning/resampling maximum of 1.007829. The reference bytes were preserved; no automatic normalization or narrator-profile modification was performed.
- Chatterbox's raw masters contain six samples above full scale, peak +0.344 dBFS. FLOAT originals retain them without integer clipping. The listening copies apply only constant attenuation.
- **Qwen's pinned 12 Hz decoder internally applies `clamp(-1, 1)`** ([implementation](https://github.com/QwenLM/Qwen3-TTS/blob/022e286b98fbec7e1e916cb940cdf532cd9f488e/qwen_tts/core/tokenizer_12hz/modeling_qwen3_tts_tokenizer_v2.py)). The default outputs contain 34 samples at full scale (6 harbor, 28 section 6), with at most nine consecutive samples; full-text has four full-scale samples in harbor and none in sections 6/9. These are short possible saturation artifacts, not proof of audible distortion. Constant-gain listening copies cannot undo internal clamping. `peak-diagnostics.json` retains locations; inspect default section 6 near **4.52–4.54 s** and full-text harbor near **26.59 s** if clicks or roughness are heard. No model-code repair or regeneration was attempted.
- Package downloading initially timed out, and the first model transfer stalled. The same pinned assets were resumed from the official endpoint and hash-verified. These setup issues are separate from inference reliability; raw audio was never sent externally.

### Preservation and reproducibility

`preservation-and-audio-checks.json` confirms all **61 protected production/data files** match their pre-benchmark hashes, all **119 production package versions** are unchanged, all **12 original passage WAVs** match their saved hashes, and all **15 listening copies** have only the documented gain transformation and sufficient headroom. Both existing localhost endpoints (FastAPI health on 8000 and the frontend on 3000) return HTTP 200. Existing projects, narrator profiles, raw recordings, production temperature/segmentation, and the user's pending UI edits are preserved.

The isolated runners are `scripts/qwen3_benchmark.py` and `scripts/evaluate_qwen3_benchmark.py`; they use existing Turbo loading, audio assembly, waveform measurement, word alignment, dependency auditing, cached ASR, and voice-encoder infrastructure. They are not imported by the application. Original output directories are exclusive, preventing accidental overwrites. `qwen-source-sha256.json` fingerprints the pinned source files. `model-cache/qwen3-benchmark/assets.json` records local model paths, exact revisions, and verified file hashes; all inference runs use local snapshots and offline guards.

## Recommendation pending listening approval

**Keep Chatterbox in production. Propose Qwen3-TTS 0.6B Base with the recommended ICL/default layout as the first candidate to audition**, using the saved Voice C reference and confirmed transcript. It has substantially fewer diagnostic word mismatches, higher speaker-similarity measurements on all three paragraphs, repeatable output, and a measured fit within this GPU's memory. It is about five times slower than Chatterbox in this bounded run, which does not disqualify it under the stated quality-first objective.

Keep the full-text variant alongside it for the listening decision. It has identical word-fidelity counts, a different pause/timing pattern, and fewer full-scale samples here, but no demonstrated perceptual delivery advantage. Prefer it only if listening establishes more natural continuity and emphasis. **Neither Qwen mode is a declared naturalness winner.** The remaining less/least flag, possible peak artifacts, and harbor sentence boundary all require review.

If listening does not clearly favor Qwen on delivery **and** narrator identity, retain Chatterbox. These approximately 80-second comparisons do not establish long-form reliability or Dessa-level speech. No Qwen integration, production setting change, UI control, extra service, or 1.7B expansion was performed. Stop here for listening approval.
