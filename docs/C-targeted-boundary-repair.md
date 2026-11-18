# Configuration C: targeted sentence-boundary repair

> Historical results: superseded local audio/results were removed on 18 November 2026 at the user's request. Findings below describe the earlier experiment; retired paths are shown as text. Current listening files are in `benchmarks/results/CURRENT-section-12/`; see the [latest Qwen validation report](qwen3-long-form-validation.md).

**Result: partial improvement, not a cleared repair.** Isolating the sentences removes section 6's repeated clause and recovers several section 9 words. However, article/word substitutions remain, and the assembled section 9 opening is recognition-sensitive. No further regeneration was attempted. **Do not integrate a segmentation change on this evidence.**

## Before/after listening

| Section | Original | Targeted sentence-boundary version |
| --- | --- | --- |
| 6 | Before (retired local result: `../benchmarks/results/expressive-delivery/C-boundary-repair-2026-11-15/section-06-before_listening_1.00x.wav`) | After (retired local result: `../benchmarks/results/expressive-delivery/C-boundary-repair-2026-11-15/section-06-after_listening_1.00x.wav`) |
| 9 | Before (retired local result: `../benchmarks/results/expressive-delivery/C-boundary-repair-2026-11-15/section-09-before_listening_1.00x.wav`) | After (retired local result: `../benchmarks/results/expressive-delivery/C-boundary-repair-2026-11-15/section-09-after_listening_1.00x.wav`) |

These are **1.00x**, matched by static gain to **-24.249 LUFS**, with sample peaks at or below -1 dBFS. No per-passage loudness correction, fades, compression, tempo changes, or pause trimming hides the new joins. Every generated sentence and assembled section also has an untouched `_raw.wav` file in the run directory (retired local result: `../benchmarks/results/expressive-delivery/C-boundary-repair-2026-11-15/`).

## Exact changes

Only **six complete sentences** were synthesized, once each, using **seed 1234** to match the original and isolate boundaries. No retries or additional seeds. Same pinned Turbo code/model as [the long-form validation](C-long-form-validation.md), temperature **0.9**, top-p **0.95**, top-k **1000**, repetition penalty **1.2**, reference normalization **true**, inactive CFG/exaggeration **0.0**, and the unchanged authorized Voice C reference. No words, punctuation, sentence order, or source script were edited.

- **Section 6:** retain original sentences 1-3 as exact samples **0-17.1125 s**. Generate sentence 4, “Sometimes the first promising result leads nowhere.”, and sentence 5, “Sometimes a casual detail, almost left out of the story, opens the right door.”, as separate calls.
- **Section 9:** generate sentences **1, 2, 4, and 6** separately. Retain sentence 3 as original samples **5.9025-11.6825 s**, and sentence 5 as **16.9725-18.8500 s**. The source remains “catalogue” and “a shelf”; no spelling or article rewrite was made.

Retained-audio cut points lie inside measured quiet intervals at sentence boundaries. Text reconstruction is asserted identical to each original section; retained decoded samples are bit-identical. These manually reviewed experimental coordinates are not an automatic audio editor or production feature.

## Accuracy results

The **existing cached local Whisper recognizer**, with no expected-text prompt, checked every generated sentence and both assembled sections using greedy and beam-five decoding.

| Passage | Result |
| --- | --- |
| Section 6 sentence 4 | **No repetition**, zero normalized word differences in both decodes |
| Section 6 sentence 5 | Both decodes hear **“the casual detail”** instead of **“a casual detail”** |
| Complete section 6 | Repetition remains absent; **one article substitution** remains, versus six extra recognized words originally |
| Section 9 sentences 1 and 2 | Isolated checks recover **“shelves themselves”** and **“through”** with zero word differences |
| Section 9 sentence 4 | Both decodes still hear **“card”** instead of **“cart”** |
| Section 9 sentence 6 | Zero normalized differences: **“catalogue/catalog”** and **“a shelf”** are recovered |
| Complete section 9 | **Three** recognized differences: “Consider the” becomes “Considered as,” plus cart/card |

The assembled opening contains the **exact same samples** as its isolated sentence. Different recognition results therefore do not establish that joining changed the word: ASR context sensitivity remains an uncertainty. Pronunciation and weak consonants need human listening. No recognizer score is treated as certified word accuracy or a naturalness rating. Transcripts, timestamps, and differences (retired local result: `../benchmarks/results/expressive-delivery/C-boundary-repair-2026-11-15/boundary-comparison.json`).

## Joins, identity, and limits

| Check | Section 6 | Section 9 |
| --- | --- | --- |
| Original / repaired duration | 30.240 / 25.993 s | 23.040 / 23.738 s |
| Internal joins to review, after-version seconds | 17.113, 20.353 | 2.120, 6.280, 12.060, 17.220, 19.098 |
| Quiet interval spanning each join | 0.446, 0.337 s | 0.376, 0.377, 0.223, 0.235, 0.137 s |
| Assembled speaker cosine to original section | 0.993 | 0.989 |

No overlapping speech or extra inserted gap was needed. The quiet intervals are bounded, but this does **not** establish natural flow. Section 9's passage loudness spans approximately **-26.1 to -20.9 LUFS**, with a largest adjacent change around **4.7 dB**. Listen for a level/emphasis reset, particularly around **17.22 s**. Overall identity proxies are high, but the very short first sentence has an unreliable shorter-context embedding; audible voice changes remain pending review. No per-part normalization was added to conceal this tradeoff.

Generation took **8.798 seconds** excluding preparation/loading, peaking at **2.80 GiB allocated GPU memory**. All six calls completed, with no OOM, generation failure, or token-limit hit. Exact cuts, seeds, metrics, and preservation hashes (retired local result: `../benchmarks/results/expressive-delivery/C-boundary-repair-2026-11-15/boundary-measurements.json`).

**Recommendation:** shorter whole-sentence calls are promising for this repeated-clause failure, but they have not cleared either entire section without other concerns. Retain paragraph grouping in production. If later listening approves this approach, the smallest candidate would be a **targeted sentence-boundary retry for a flagged passage**, leaving unaffected context and text intact—not a global switch to one sentence per call. That is a proposal for future approved validation, not an implemented feature.

All originals, previous experiments, production source, project data, and the other fourteen narration sections are unchanged. No rebuild, dependency install, model download, additional model, script rewrite, or full-narration replacement occurred. **Stop here for listening approval; no unlimited retries.**
