# Configuration C: sections 6 and 9 review

> Historical results: superseded local audio/results were removed on 18 November 2026 at the user's request. Findings below describe the earlier experiment; retired paths are shown as text. Current listening files are in `benchmarks/results/CURRENT-section-12/`; see the [latest Qwen validation report](qwen3-long-form-validation.md).

**Result: the two-seed repair limit is exhausted; no replacement is cleared.** Section 6 still repeats a phrase in both takes. Section 9 seed 1236 improves the flagged words but introduces an article change at the end. No full narration, project, production setting, or original recording was replaced. Stop for listening review.

## Source versus original audio

**Section 6:** the exact saved script contains **“Sometimes the first promising result leads nowhere.” once**, followed by **“Sometimes a casual detail, almost left out of the story, opens the right door.”** Repeating the word “Sometimes” across these two sentences is intentional; repeating the first clause is not in the source.

Separate, non-overlapping audio windows decode as:

- Section-relative **17.44-21.16 s**: “Sometimes the first promising result leads nowhere.” First phrase (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/s06-before-first_review.wav`).
- **21.16-24.60 s**: the additional “Sometimes the promising result leads nowhere.” Extra phrase (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/s06-before-extra_review.wav`).

This localizes the unwanted repeat in the synthesized recording, independently of long-audio recognizer chunk merging. It is **not a repeated source passage**. In the original raw full narration, the extra phrase is approximately **2:23.40-2:26.84**. The text was not rewritten.

**Section 9:** exact source opening: “Consider the shelves themselves.” Its ending uses **“A catalogue can describe a collection, but it cannot straighten a shelf.”** “Catalog” in a transcript is the accepted spelling counterpart of “catalogue,” not a missing word or a demonstrated pronunciation defect.

| Source words / check | Section-relative original time | Original raw full narration | Observation |
| --- | --- | --- | --- |
| “shelves themselves” | 0.74-1.40 s; inspect the full opening at 0-1.40 s | 3:23.06-3:23.72 | Recognized as “chefs,” with the intended phrase collapsed/absent in the transcript |
| “through” | 4.12-4.58 s | 3:26.44-3:26.90 | Recognized as “due” or “to” |
| “cart” | 15.70-15.92 s | 3:38.02-3:38.24 | Recognized as “car” or “card” |
| “catalogue” | 19.24-19.52 s | 3:41.56-3:41.84 | Recognized as “catalog”; **no correction warranted on this evidence** |

Times are word-alignment estimates from the existing local recognizer, not manually certified phoneme boundaries. Listen with surrounding context; ASR may mishear accent or weak consonants. Original timestamp trace (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/original-word-timestamps.json`).

## Before/after listening

All table files are **1.00x**, statically matched to **-24.266 LUFS** with sample peaks no higher than -1 dBFS. No tempo, trimming, fades, or compression obscures the comparison. Untouched alternative raw WAVs are retained alongside them.

| Section | Original seed 1234 | Alternative seed 1235 | Alternative seed 1236 |
| --- | --- | --- | --- |
| 6 | Before (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/section-06-before_listening_1.00x.wav`) | After 1235 (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/section-06-seed-1235_listening_1.00x.wav`) | After 1236 (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/section-06-seed-1236_listening_1.00x.wav`) |
| 9 | Before (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/section-09-before_listening_1.00x.wav`) | After 1235 (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/section-09-seed-1235_listening_1.00x.wav`) | After 1236 (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/section-09-seed-1236_listening_1.00x.wav`) |

| Take | Duration | Full-section normalized ASR edits, greedy / beam | Finding |
| --- | --- | --- | --- |
| 6 / 1235 | 25.48 s | 6 / 6 | Extra “Sometimes the promising result leads nowhere” remains at **17.92-20.74 s** |
| 6 / 1236 | 27.64 s | 7 / 7 | Full first clause repeats at **19.10-22.52 s** |
| 9 / 1235 | 23.84 s | 3 / 1 | Beam decode recovers the opening and “through,” but “cart” becomes “card”; greedy opening is also unstable |
| 9 / 1236 | 25.68 s | 1 / 1 | “Shelves themselves,” “through,” “cart,” and “catalogue/catalog” are recovered; the ending becomes “straighten **the** shelf” instead of “straighten **a** shelf” |

Independent short-window decodes retain both section 6 repeats and section 9 seed 1236's changed ending. Isolated clip evidence (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/isolated-phrase-checks.json`), ending clip (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/s09-seed-1236-ending_review.wav`), complete transcripts/differences (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/comparisons.json`).

These checks do **not** clear either section as defect-free. They show that changing seeds alone did not remove the repeated phrase, and the strongest section 9 candidate still has a new word-fidelity concern. Naturalness, audible artifacts, accent, and narrator identity require human approval; no claim of “no new problems” is justified.

## Configuration and preservation

Exactly four calls: two per affected section, seeds **1235 and 1236**. Same pinned Turbo model/code, temperature **0.9**, top-p **0.95**, top-k **1000**, repetition penalty **1.2**, reference normalization **true**, Voice C reference hash, and complete original section text/grouping. Seeds were saved before inference. No punctuation edits, reference replacement, additional synthesis model, package install, or application rebuild occurred. The existing cached Whisper recognizer and Turbo voice encoder were reused locally.

Four takes generated in **91.974 s**, with peak allocated GPU memory **3.44 GiB**, no generation errors or token-limit hits. Speaker cosine to each corresponding original section is **0.975-0.986**, a similarity proxy rather than listening approval. Original/project/production hashes are unchanged; all other fourteen narration sections remain untouched. No failed take was hidden and no third seed was attempted.

Generation/seed manifest (retired local result: `../benchmarks/results/expressive-delivery/C-section-repair-2026-11-15/repair-measurements.json`). Reproducer: `scripts/repair_long_form_sections.py`; existing repair directories are not overwritten. **Keep the original narration in place. Review these candidates; do not integrate or claim a fully corrected narration.**
