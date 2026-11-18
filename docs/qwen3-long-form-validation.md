# Qwen3-TTS default: final long-form validation

> **Latest comparison — Section 12, trim only:** [before transition](../benchmarks/results/CURRENT-section-12/03-transition-before.wav) · [after transition](../benchmarks/results/CURRENT-section-12/04-transition-after.wav) · [trimmed WAV](../benchmarks/results/CURRENT-section-12/02-corrected-trimmed.wav). Files are numbered in `benchmarks/results/CURRENT-section-12/`. No speech was regenerated or integrated.

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

## Original validation recommendation pending listening approval

**Technical feasibility passes; retain Qwen outside production until listening review.** The complete eight-minute narration fits this GPU and maintains strong speaker-embedding consistency without retries. No repeated passages or missing sentences were detected. That is sufficient to prepare a long-form audition, not to approve reliable wording or natural delivery automatically.

Review the **17,400**, **a/the conversation**, and **quiet/quite** clips first, then the names, both joins, and the full master for stable identity and natural phrasing. The consistent recognition flags prevent declaring wording fully cleared. If listening confirms a synthesis defect, retain these originals and decide on a narrowly scoped repair separately; no repair or tuning was performed here.

No Dessa-level delivery claim, new model, production integration, UI change, model switch, or cloud service is introduced. Chatterbox Turbo's production behavior is preserved. Stop here for long-form listening approval.

## Focused accuracy review — 18 November 2026

**Outcome:** the explicit spoken-number expansion improves section 12's transcription, but the one new full-section take introduces a long trailing quiet interval. It is **not approved as a replacement**. Sections 13 and 18 are preserved, with no regenerated audio: section 13 still needs direct listening confirmation before its conditional alternative take; section 18's cropped beam decode recovers the intended word.

This session can inspect waveforms and run local recognition but cannot directly audition WAV audio. The findings below distinguish measured audio properties and ASR evidence from human listening confirmation. A listening question was presented for sections 13/18; no answer has been assumed.

### Exactly what was generated

One new take of the **complete original section 12 paragraph**, with only this inference-text substitution:

```text
Source:     There are now 17,400 files in the night's working directory, counting the supporting records as well as the images.
Inference:  There are now seventeen thousand four hundred files in the night's working directory, counting the supporting records as well as the images.
```

The paragraph's `02:17`, all other words, punctuation, and sentence order remain unchanged. The complete original and inference paragraphs, the explicit replacement, seed, and one-take limit are saved in `benchmarks/results/qwen3-accuracy-review/2026-11-18/number/plan.json`. The original script and narrator recording were not edited. This is a single documented test substitution, **not an automatic text-normalization feature**.

Generation uses the same pinned 0.6B Base model/code/reference/transcript, English, BF16, CUDA SDPA, default ICL (`x_vector_only_mode=False`, `non_streaming_mode=False`). Seed **1234** matches the original. Saved generation settings match the long-form run exactly: sampling enabled; temperature **0.9**, top-k **50**, top-p **1.0**, repetition penalty **1.05**; subtalker sampling enabled with temperature **0.9**, top-k **50**, top-p **1.0**; max new tokens **8192**. There were no alternative seeds or retries, no added models/dependencies, and no production changes. Inference and diagnostics remain local/offline.

### Section 12: before/after evidence

| Measurement | Original | Expanded-number take |
| --- | --- | --- |
| Generation time | 49.018 s | 130.327 s |
| Raw duration | 28.64 s | 35.20 s |
| Raw integrated loudness | −19.876 LUFS | −17.142 LUFS |
| Raw sample peak | −0.818 dBFS | 0.000 dBFS |
| Quiet-frame fraction, below −45 dBFS | 20.15% | 31.39% |
| Leading / trailing quiet, 10 ms RMS measurement | 0.12 / 0.07 s | 0.21 / **5.34 s** |
| Speaker cosine to the reference | 0.9262 | 0.9318 |
| Peak allocated / reserved VRAM | 2.805 / 3.918 GiB | 2.812 / 3.490 GiB |
| Greedy / beam normalized ASR edit counts | 5 / 5 | 4 / 2 |

The before/after speaker-embedding cosine is **0.9715**, supporting identity consistency but not proving perceived voice, accent, or delivery equivalence. The new take generated 440 codec frames without a token-cap hit, OOM, or generation exception. Runtime is one observation under current machine conditions, not evidence that spelling out a number intrinsically takes 2.7 times longer.

Both original decodes render the number as **“17 Zvar 400” / “17 Svar 400.”** Both new decodes render it as **“17,400.”** The intended number has stronger diagnostic support after expansion. Listen around **12.90–14.46 s** in the original section and **14.92–16.14 s** in the candidate. The new take's greedy decode spells “night's” as “Knights,” while beam recovers the original wording; these are homophonic and are not confirmed new spoken errors. Both retain the `02:17` versus `02.17` formatting flag. No repeated sentence, missing ending, or large addition is detected.

The substantial pacing change is measurable: the new take ends with approximately **5.34 seconds below −45 dBFS**. It would delay the unchanged opening of section 13 in a direct concatenation. That tail is preserved, not silently trimmed. The new decoder output also has four full-scale samples (longest run two samples), versus none in the original section; audible significance remains a listening question. Consequently, clearer numeral recognition alone does not establish a better full-section replacement.

### Comparison recordings

All files below are in `benchmarks/results/qwen3-accuracy-review/2026-11-18/comparison/`:

| Comparison | Before / original | After / candidate |
| --- | --- | --- |
| Complete section 12, individually level-matched to −23 LUFS | [Before](../benchmarks/results/qwen3-accuracy-review/2026-11-18/comparison/section_12_before_levelmatched.wav) | [After](../benchmarks/results/qwen3-accuracy-review/2026-11-18/comparison/section_12_after_levelmatched.wav) |
| Complete number sentence, approximate ASR word boundaries | [Before](../benchmarks/results/qwen3-accuracy-review/2026-11-18/comparison/number_sentence_before.wav) | [After](../benchmarks/results/qwen3-accuracy-review/2026-11-18/comparison/number_sentence_after.wav) |
| Four seconds of original section 11 + section 12 + four seconds of original section 13 | [Before transition](../benchmarks/results/qwen3-accuracy-review/2026-11-18/comparison/section_12_transitions_before.wav) | [After transition](../benchmarks/results/qwen3-accuracy-review/2026-11-18/comparison/section_12_transitions_after.wav) |

The full-section comparison uses independent constant gain to avoid a louder-is-better bias: −3.124076 dB before and −5.858370 dB after. Number-sentence clips retain their parent section's gain (approximately −22.18 and −22.45 LUFS); neither is locally boosted. Transition previews use the **same −4.100403 dB original-master gain** and **identical neighbor samples** on both sides. Their overall levels differ (−23.41 versus −21.39 LUFS), intentionally exposing the candidate's relative loudness in the existing narration. Judge voice quality using the level-matched full sections; judge pauses and relative levels using the transition previews.

The preview files are separate artifacts. No sentence or section has been inserted into the original eight-minute master. The untouched raw candidate is `number/qwen06_default/main/section_12.wav`; source/candidate copies, independent recognition, word timestamps, and embeddings are in `evaluation/`. `comparison.json` documents crops, gain, durations, and hashes.

### Section 13: evidence and conditional limit

Exact source sentence:

> Inside, a conversation drifts from a stubborn software message to the journey home.

The full-paragraph greedy/beam decodes both say **“the conversation.”** A separate crop of this complete original sentence, approximately **10.50–16.20 s** in section 13, again gives **“the conversation”** in both decodes. The suspected article is near **10.92–11.14 s** section-relative, or **05:29.48–05:29.70** in the original master.

[Listen to the preserved original sentence](../benchmarks/results/qwen3-accuracy-review/2026-11-18/comparison/section_13_original_sentence.wav). Four consistent recognition outputs strengthen the suspicion, but they are not independent human confirmation of what the waveform says. **No alternative was generated because the user's “if confirmed” condition remains unverified by listening.** The complete source wording and original audio are preserved; no seed search occurred. One alternative complete-sentence take can proceed after that confirmation, without regenerating the surrounding section.

### Section 18: retain the original

Exact source sentence:

> Behind her, the observatory looks quiet again.

Full-paragraph decodes give “quite again.” On the isolated original sentence (approximately **5.56–9.96 s** section-relative), greedy still gives “quite,” but beam gives **“quiet again” with zero normalized edits**. This demonstrates recognition instability rather than establishing a genuine pronunciation failure. [Listen to the preserved original sentence](../benchmarks/results/qwen3-accuracy-review/2026-11-18/comparison/section_18_original_sentence.wav). The target word is around **8.24–8.88 s** section-relative, or **07:45.44–07:46.08** in the original master.

**Section 18 was not regenerated.** No pronunciation defect has been confirmed by listening, and there is positive diagnostic support for the intended word.

### Decision and preservation

Do not integrate or replace the original sections from this evidence alone. The explicit number expansion is promising for word fidelity, but its one full-paragraph take introduces a clear transition/pacing concern. Section 13 remains a high-priority listening check, and section 18 should remain untouched unless an actual pronunciation defect is heard. No extra attempts were made to conceal those limitations.

`benchmarks/results/qwen3-accuracy-review/2026-11-18/preservation-and-audio-checks.json` verifies **239 protected files unchanged**, including the original script, every original long-form artifact and WAV, earlier narration WAVs, application/UI code, projects, and reference profiles. All **119 production package versions** are unchanged. All eight comparison files and the identical original neighbor samples in both transition previews were verified; both existing localhost endpoints return HTTP 200. The held runtime mutex `data/.app.lock` is excluded from file hashing.

The only benchmark-helper change adds word-timestamp diagnostics without generating unrelated tempo exports; it is not imported by the application. Exactly one new TTS take was generated (section 12), with zero for sections 13 and 18. Chatterbox remains production, with no application rebuild, model switch, automatic script rewriting, or project-data modification.

## Trim-only Section 12 transition review — 18 November 2026

The user listened and confirmed that the expanded-number take correctly pronounces **“seventeen thousand four hundred.”** This follow-up addresses only its excessive trailing quiet. It does not regenerate speech, change model settings, alter the source script, replace a project recording, or integrate Qwen.

### Files to review

Open `C:\Users\saide\Desktop\awal\benchmarks\results\CURRENT-section-12\`:

| File | Purpose |
| --- | --- |
| [01-corrected-untrimmed.wav](../benchmarks/results/CURRENT-section-12/01-corrected-untrimmed.wav) | Byte-identical copy of the existing 35.20 s corrected raw take. |
| [02-corrected-trimmed.wav](../benchmarks/results/CURRENT-section-12/02-corrected-trimmed.wav) | New raw comparison: the same retained samples, with the excessive suffix removed. |
| [03-transition-before.wav](../benchmarks/results/CURRENT-section-12/03-transition-before.wav) | Final speech plus the original long end pause, followed by the first eight seconds of original Section 13. |
| [04-transition-after.wav](../benchmarks/results/CURRENT-section-12/04-transition-after.wav) | The exact same speech and Section 13 opening, with only the shorter end pause. |

The original long-form Section 12 and its first corrected take remain at their existing paths. These new files are separate review artifacts. `trim-details.json` records the sample cut, gains, measurements, source hashes, and output hashes.

### Exact trim and speech preservation

| Property | Value |
| --- | --- |
| Format | Mono, 24,000 Hz, FLOAT WAV |
| Original corrected length | 844,800 samples / 35.200000 s |
| Last sample at or above −45 dBFS | Zero-based index **716,950**; activity end at **29.872958 s** |
| Quiet retained after that activity boundary | **8,400 samples / 0.350000 s** |
| Cut index, exclusive | **725,351** |
| Trimmed length | **30.222958 s** |
| Suffix removed | **119,449 samples / 4.977042 s** |
| Removed suffix peak / RMS | **−53.043 / −77.530 dBFS** |
| End quiet using the previous 10 ms, −45 dBFS RMS measure | Before **5.34 s**; after **0.36 s** |

The operation is exactly `trimmed = corrected[:725351]`. Every retained sample compares equal after saving and reloading. There is no fade, gain change, filtering, resampling, time stretching, or speech regeneration in file 02. The discarded suffix is entirely below the activity threshold, and the retained 0.35 s includes the low-level decay after stronger speech ends. The last retained sample has amplitude 0.000713 (approximately −62.9 dBFS); no fade or invented replacement silence was applied.

The untouched corrected take's SHA-256 remains `90b203197f0fb0a3177880c0da33eee668b7b7ed6050b3b71961a09511933b8d`. The trimmed copy's SHA-256 is `35218916545ac51b8b04c629870f059ee292042f1d69498f755848fe5e75aa7f`. Identity, pronunciation, and rhythm within the retained speech cannot change through this sample-preserving prefix operation.

### Pacing and loudness at the join

The previews start at **24.872958 s** in the corrected take, five seconds before its measured activity end. They then append the same eight seconds of original Section 13, without fades or extra gap insertion. The join occurs at **10.327042 s** in the before preview and **5.350000 s** in the after preview. Preview lengths are **18.327042 s** and **13.350000 s**.

Section 13 contributes approximately **0.24 s** of its own leading quiet. The total measured quiet interval around the join falls from approximately **5.58 s to 0.60 s**. That is consistent with a paragraph pause; its perceived naturalness still needs the user's listening approval. Section 13's wording, voice, and samples are unchanged.

The raw trimmed WAV preserves the corrected take's original level. For the separate listening previews, fixed gains derived from each complete untrimmed section align Section 12 and Section 13 to **−23 LUFS**: **−5.858370 dB** and **−3.476223 dB**, respectively. Both previews use those identical gains. This compensates for the corrected take being about **2.38 LU louder** than original Section 13, without modifying either raw recording. Before/after preview loudness is **−22.959 / −22.924 LUFS**, a difference of only **0.034 LU**. Every retained Section 12 sample and every Section 13 sample is identical between the two previews after the shared gain operations; only the quiet suffix is absent from the after version.

**Recommendation:** audition file 04 for the Section 12 → 13 pacing decision. The measured pause and loudness are suitable for review, and the already approved number pronunciation is preserved. No new model inference or ASR pass is needed to validate the unchanged speech samples. This does not resolve the separately pending Section 13 article check or constitute production integration approval.

### Results cleanup

At the user's request, superseded local results were deleted, not archived:

- The older Chatterbox expressive-delivery experiment tree: 99 files.
- Superseded Qwen-versus-Chatterbox listening/raw WAVs: 30 files. Its settings, license/source receipts, measurements, and other metadata remain.

Total removed: **129 files / 406.19 MiB**. Older reports mark retired paths as historical text rather than offering dead audio links. The full Qwen long-form validation, all its original sections/masters, the current corrected number take, the focused accuracy comparisons, model caches, narrator profiles, project data, and dependency environments are retained. No archive copies were created. `CURRENT-section-12/cleanup-manifest.json` records exactly which older files were removed; the numbered current folder provides the new listening entry point.

`CURRENT-section-12/verification.json` confirms **164 protected current files unchanged**, all **119 production package versions unchanged**, the exact raw prefix and untouched corrected-copy hashes, identical retained speech/Section 13 samples in the two previews, sufficient preview peak headroom, and all document links resolving. Both existing localhost endpoints return HTTP 200. No model or ASR inference was run for this trim-only follow-up. Production remains unchanged, and transition acceptance awaits listening approval.
