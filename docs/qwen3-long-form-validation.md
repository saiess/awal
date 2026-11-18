# Qwen3-TTS default: final long-form validation

Date: 18 November 2026. Validation only; Chatterbox remains Awal's production engine.

## Frozen test

- Model: `Qwen/Qwen3-TTS-12Hz-0.6B-Base`, revision `5d83992436eae1d760afd27aff78a71d676296fc`.
- Official Qwen code: `022e286b98fbec7e1e916cb940cdf532cd9f488e`, package `qwen-tts==0.1.1`.
- Bundled 12 Hz speech tokenizer; separately recorded tokenizer revision `7dd38ad4e9bad454aae9cd937d0cd577604fe229`.
- Existing `.venv-qwen3`: Python 3.12.2, PyTorch/torchaudio 2.6.0+cu124, Transformers 4.57.3, Accelerate 1.12.0, NumPy 1.26.4. All 90 installed package versions match the previous benchmark inventory. No dependencies, models, or services were installed.
- Qwen code/model/tokenizer remain Apache-2.0. Commercial-use and dependency findings are unchanged; see [the benchmark license audit](qwen3-vs-chatterbox-evaluation.md#installed-dependency-licenses) and [exact inventory](licenses/qwen3-benchmark-installed/inventory.json).
- Voice C: the same authorized 19.1135-second reference, SHA-256 `fc03ae6e7225642e8cf83e5160aff1d7f0b3cf17e23045c006d945bdc8b93931`. The previously confirmed reference transcript is preserved in the frozen plan and passed unchanged to ICL cloning. No narrator profile changes.

The new [original script](../benchmarks/scripts/observatory-night-shift.txt), **The observatory after sunset**, contains 1,201 whitespace-delimited words in 18 paragraphs. It is a fictional documentary-style story: the observatory and staff are illustrative, not a claimed historical account. Challenges include Leila Haddad, Mateusz Nowak, Saoirse O'Neill, Ananya Srinivasan, `21:45`, `02:17`, `0.03 percent`, `1998`, and `17,400`, plus a long sentence about telescope tracking. The script was frozen before generation and is not rewritten in response to errors.

Each complete paragraph is one generation call (366–434 characters). The existing experimental sentence/paragraph boundary helper reproduces all 18 original paragraphs exactly; it does not split any sentence. Exact text and script hash are recorded in `plan.json` and the saved measurements.

Evidence directory: `benchmarks/results/qwen3-long-form/2026-11-18/`.

## Generation and processing

The existing isolated benchmark runner loads the pinned local snapshot using BF16, CUDA, and PyTorch SDPA. English; ICL enabled through reference audio plus transcript; `x_vector_only_mode=False`; `non_streaming_mode=False`. One reference prompt is prepared and reused throughout the run.

Official saved sampling defaults are used without overrides: sampling enabled, temperature **0.9**, top-k **50**, top-p **1.0**, repetition penalty **1.05**; subtalker sampling enabled, temperature **0.9**, top-k **50**, top-p **1.0**. The saved official **8192** new-token limit is retained, replacing the earlier short benchmark's explicitly reduced 1024 limit. Seed **1234** is reset per paragraph. One take per paragraph; no automatic retries, extra seeds, or best-take selection.

Inference and verification use offline/local-files flags and a Python socket-connect guard. Cached Qwen and Whisper file hashes were verified locally. Only an existing localhost health check precedes inference. The application must be idle and at least 6 GiB GPU memory free before generation starts.

All original section WAVs use mono 24 kHz FLOAT storage. The raw master concatenates those exact samples with the existing minimum 0.12-second quiet-edge-aware boundary gap; it applies no trimming, fades, normalization, or denoising. Separate listening copies use constant gain. The separate 1.10× export uses FFmpeg `atempo=1.1`, which changes tempo while preserving pitch; it is not evidence of improved generated prosody. Original section files and the raw master remain unchanged.

## Results and listening review

**Technical generation completed:** 18 of 18 first takes, **487.12 seconds (8:07.12)** at 1.00× and **442.833 seconds (7:22.83)** at 1.10×. No out-of-memory exception, Python generation exception, invalid waveform, or token-cap hit. Wording, pronunciation, and perceptual delivery approval remain pending the listening checks below.

### Listening files

- [Full level-matched 1.00× listening master](../benchmarks/results/qwen3-long-form/2026-11-18/listening/qwen06_default__raw_1.00x_levelmatched.wav).
- [Full level-matched 1.10× YouTube listening version](../benchmarks/results/qwen3-long-form/2026-11-18/listening/qwen06_default_tempo_1.10x_levelmatched.wav).
- [Preserved raw 1.00× master](../benchmarks/results/qwen3-long-form/2026-11-18/qwen06_default/raw_1.00x.wav).
- [Separate unnormalized 1.10× export](../benchmarks/results/qwen3-long-form/2026-11-18/qwen06_default/tempo_1.10x.wav).

The absolute listening folder is `C:\Users\saide\Desktop\awal\benchmarks\results\qwen3-long-form\2026-11-18\listening`. Individual raw sections are in `qwen06_default/main/section_01.wav` through `section_18.wav`. Focused clips are in `flagged-clips/` and linked in the review table.

Both full listening masters measure **−23.00 LUFS**. The 1.00× master uses **−4.100403 dB** constant gain; the separate tempo listening file uses **−4.081449 dB**. The individual section copies target the same level, with a maximum measured deviation of 0.019 LU from loudness gating. All have at least 1 dB sample-peak headroom. Focused clips retain the full 1.00× master's gain, rather than being independently boosted. Clip endpoints are diagnostic cuts; judge the interior, not a cut at the start or end.

No extra boundary padding was needed: the raw master is **sample-identical to the concatenation of all 18 original takes**. No original recording was trimmed or replaced.

### Performance and memory

Hardware: RTX 4070 Laptop GPU, 8188 MiB reported VRAM, compute capability 8.9, NVIDIA driver 560.81, native Windows CUDA. Models run sequentially; Whisper starts after Qwen exits.

| Measurement | Result |
| --- | --- |
| Generation calls | 18, one take each |
| Sum of generation times | **855.581 s / 14:15.58** |
| Individual generation time | 42.461–52.797 s |
| Model/runtime loading measurement | 6.473 s |
| Reference prompt preparation | 1.507 s |
| Generation seconds per raw audio second | 1.756 |
| Peak PyTorch allocated VRAM | **2.812 GiB** |
| Peak PyTorch reserved VRAM | **4.143 GiB** |
| Generated codec frames per paragraph | 298–374, versus official 8192-token bound |
| Unprompted ASR decode time, both passes combined | 47.475 s |

Generation times exclude writing audio, evaluation, and exports. Loading measurement starts after Torch import/CUDA initialization, so it is not complete cold-process startup time. VRAM numbers are allocator peaks across calls, not total driver/device memory. Complete per-call timing, settings, hashes, and memory results are in `qwen06_default/main/measurements.json`; `qwen-environment.json` records exact installed versions and hardware.

The known optional FlashAttention and SoX-executable warnings persist. Native SDPA/12 Hz inference completes without installing either. PowerShell wrapped the absent-SoX stderr warning as `NativeCommandError` and reported a nonzero launcher status; the saved generation manifest is `completed`, all 18 calls returned and saved valid audio, and no Python traceback or failed take occurred. This launcher warning remains visible in `generation.log` rather than being hidden. The existing slightly over-full-scale reference also produces the same conditioning warning documented in the earlier benchmark; its bytes remain unchanged.

### Word fidelity: diagnostic results

The existing local `openai/whisper-small.en` checkpoint, revision `e8727524f962ee844a7319d92be39ac1bd25655a`, is unchanged and hash-verified. Greedy recognition supplies approximate word timestamps; a separate five-beam decode checks recognition stability. Neither receives the expected script as a decoder prompt.

The source has **1,210 normalized verification tokens**, versus 1,201 whitespace-delimited script words. Greedy recognition has **19 token edits (1.57%)**; beam recognition has **17 (1.40%)**. Nine paragraphs have at least one flag in either pass. These are recognition/edit diagnostics, **not confirmed TTS error rates**: proper-name spelling, clock formatting, and homophones inflate the counts.

All timestamps below refer to the **1.00× raw/listening master**, with approximate ASR word boundaries. Deleted words have neighboring-word review windows. The tempo file has a different timeline. Full source text, both complete transcripts, every normalized alignment edit, and section-relative/master-relative timestamps remain in `diagnostics.json`.

| Section | Raw master timestamp | Exact source → recognition | Assessment and focused clip |
| --- | --- | --- | --- |
| 1 | 00:04.82–00:05.24 | “beginning” → greedy “picking in”; beam “beginning” | Recognition instability; [review](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_01_issue_01.wav). |
| 1 | 00:17.24–00:17.64 | “too faint” → “to faint” in both | Homophone/orthography flag; not proof of an audible substitution. [Clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_01_issue_02.wav). |
| 2 | 00:26.74–00:27.48 | “Haddad” → greedy “Haddad”; beam “Hadad” | Name-spelling instability; [clip also includes the opening join](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_02_issue_01.wav). |
| 4 | 01:16.16–01:17.58 | “Mateusz” → “Mathias” in both | Name pronunciation needs listening; [clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_04_issue_01.wav). |
| 4 | 01:19.46–01:20.74 | “Saoirse O'Neill” → “Saorshe Onil” in both | May be phonetic name transcription; do not infer omission from spelling alignment alone. [Same clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_04_issue_01.wav). |
| 5 | 01:42.14–01:43.62 | `21:45` → `21.45` in both | Clock-format mismatch; check spoken time before treating it as a number error. [Clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_05_issue_01.wav). |
| 10 | 03:57.04–03:57.36 | “Saoirse” → “Sarsje” / “Sarsja” | Name transcription/pronunciation review; [clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_10_issue_01.wav). |
| 11 | 04:26.94–04:27.16 | “Mateusz” → “Matias” / “Matthias” | Name pronunciation review; [clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_11_issue_01.wav). |
| 11 | 04:31.92–04:32.24 | “Leila” → greedy “Lela”; beam “Leila” | Recognition instability; [clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_11_issue_02.wav). |
| 12 | 04:50.30–04:51.98 | `02:17` → `02.17` in both | Clock-format mismatch; [clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_12_issue_01.wav). |
| **12** | **05:02.82–05:04.38** | **`17,400` → “17 Zvar 400” / “17 Svar 400”** | **Priority:** verify “seventeen thousand four hundred,” especially the middle word. Neither decode clears it. [Clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_12_issue_02.wav). |
| **13** | **05:29.48–05:29.70** | **“a conversation” → “the conversation” in both** | **Priority:** suspected article substitution, not yet a confirmed synthesis defect. [Clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_13_issue_01.wav). |
| **18** | **07:45.44–07:46.08** | **“quiet again” → “quite again” in both** | **Priority:** check whether “quiet” has its intended pronunciation. [Clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_18_issue_01.wav). |

The verifier normalizes the “O” in O'Neill to numeric `0`; the low-level alignment therefore has an artificial zero token. It is **not evidence that the narrator spoke “zero.”** Similarly, colon-versus-period clock rendering produces deletion/substitution counts without proving missing spoken words. The source script is unchanged.

No complete sentence, paragraph, or ending is missing from either transcript. No repeated phrase or large unexplained addition was detected. The opening “picking in” flag clears in beam decoding; the numeral's “Zvar/Svar” rendering and article/pronunciation flags remain unresolved. Ananya Srinivasan, `0.03 percent`, `1998`, `14`, and `90 seconds` have no normalized word mismatch in either pass. This does not independently certify their pronunciation.

### Narrator consistency and delivery

The existing pinned Chatterbox voice encoder supplies the same diagnostic embedding path as the earlier comparison, with 16 kHz resampling. No evaluation model was added. Across the 18 paragraphs, cosine similarity to the reference ranges **0.9126–0.9483**, mean **0.9328**. Adjacent-paragraph similarity ranges **0.9509–0.9800**.

| Listening anchor | Reference similarity | Similarity to opening paragraph | Sample |
| --- | --- | --- | --- |
| Beginning, section 1, 00:00.00 | 0.9399 | 1.0000 | [Listen](../benchmarks/results/qwen3-long-form/2026-11-18/listening/qwen06_default__main__section_01_levelmatched.wav) |
| Middle, section 10, 03:54.24 | 0.9325 | 0.9591 | [Listen](../benchmarks/results/qwen3-long-form/2026-11-18/listening/qwen06_default__main__section_10_levelmatched.wav) |
| End, section 18, 07:37.20 | 0.9483 | 0.9810 | [Listen](../benchmarks/results/qwen3-long-form/2026-11-18/listening/qwen06_default__main__section_18_levelmatched.wav) |

These measurements support stable identity in this run, including its end, but do not replace checks of accent, tone, phrasing, or perceived speaker identity. There is no validated perceptual acceptance threshold for these scores here.

Paragraph durations range **23.84–29.92 s**. Quiet 10 ms frames below −45 dBFS make up **17.40%** of the raw master. Those descriptors do not establish meaningful pauses, emphasis, or human-like intonation. Listen at 1.00× first, especially to the questions in sections 6, 7, and 14 and the long tracking sentence in section 5. Then judge whether 1.10× preserves an unhurried, clear delivery. Acceleration is not expressive generation.

Each paragraph is generated independently with the same reference prompt; previous paragraphs are not carried as conversational context. Listen for a mechanical restart or change in accent at joins. The measured quiet intervals span **0.12–1.10 s**. Two conservative review flags exceed 0.8 s:

- Section 1 → 2, boundary **00:25.20**, approximately **1.00 s** quiet: [review clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_02_issue_01.wav).
- Section 13 → 14, boundary **05:45.84**, approximately **1.10 s** quiet: [review clip](../benchmarks/results/qwen3-long-form/2026-11-18/flagged-clips/section_14_issue_01.wav).

Either pause may be appropriate for a paragraph transition; neither was shortened automatically. No audible-join judgment is claimed without listening.

Qwen's existing decoder clamps internally to ±1. The run contains **20 samples at full scale**, with a longest consecutive run of **six samples (0.25 ms)**. No returned sample exceeds full scale. These short saturation points merit attention if roughness is heard, but are not proof of audible distortion. Constant-gain listening copies cannot reverse internal clamping. Original FLOAT audio remains intact.

### Preservation and evidence

`preservation-and-audio-checks.json` verifies **175 protected files unchanged**, including production code, UI files, project/narrator data, and earlier benchmark WAVs. All **119 production package versions** are unchanged. Only the application's held runtime mutex, `data/.app.lock`, is excluded from readable-file hashing. Both existing localhost endpoints still return HTTP 200.

All 18 raw take hashes, exact script text, raw-master concatenation, 20 listening-copy gain transformations, 13 focused clips, and tempo duration were verified. The 1.10× duration differs from raw duration divided by 1.1 by only about 3 ms. `assets-verified.json` records local model verification; `diagnostics.json` retains transcripts, word timestamps, voice vectors, quiet/peak descriptors, joins, and clip ranges. The two existing benchmark helpers were extended for a supplied frozen run directory and long-form diagnostics; no application module or dependency was changed.

## Recommendation pending listening approval

**Technical feasibility passes; retain Qwen outside production until listening review.** The complete eight-minute narration fits this GPU and maintains strong speaker-embedding consistency without retries. No repeated passages or missing sentences were detected. That is sufficient to prepare a long-form audition, not to approve reliable wording or natural delivery automatically.

Review the **17,400**, **a/the conversation**, and **quiet/quite** clips first, then the names, both joins, and the full master for stable identity and natural phrasing. The consistent recognition flags prevent declaring wording fully cleared. If listening confirms a synthesis defect, retain these originals and decide on a narrowly scoped repair separately; no repair or tuning was performed here.

No Dessa-level delivery claim, new model, production integration, UI change, model switch, or cloud service is introduced. Chatterbox Turbo's production behavior is preserved. Stop here for long-form listening approval.
