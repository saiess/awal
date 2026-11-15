# Configuration C: long-form validation

**Decision: do not integrate yet.** Technical generation passed, but word fidelity is not cleared. A repeated phrase is consistently detected in section 6; section 9 has pronunciation/word-recognition flags. Human listening must settle these and audible identity stability. Production is unchanged.

## Listening samples

- [Original 1.00x, 6:48](../benchmarks/results/expressive-delivery/C-long-form-2026-11-15/C_long_form_raw_1.00x.wav): untouched float master; peaks can exceed full scale.
- [Safe listening 1.00x, 6:48](../benchmarks/results/expressive-delivery/C-long-form-2026-11-15/C_long_form_listening_levelmatch_1.00x.wav): static gain only, -23.774 LUFS, no tempo or pause changes.
- [YouTube listening 1.10x, 6:11](../benchmarks/results/expressive-delivery/C-long-form-2026-11-15/C_long_form_tempo_1.10x.wav): pitch-preserving FFmpeg `atempo=1.1`, then -2.149 dB static attenuation for a -1 dBFS sample-peak ceiling; no compression, fades, or pause trimming.

**The Hidden Life of a City Library:** 1,118 source words, 97 sentences. [Script](../benchmarks/results/expressive-delivery/C-long-form-2026-11-15/script.txt), [time cues](../benchmarks/results/expressive-delivery/C-long-form-2026-11-15/listening-cues.csv), [measurements](../benchmarks/results/expressive-delivery/C-long-form-2026-11-15/measurements.json), and all 16 emitted sections are retained locally.

## Exact settings and measurements

Chatterbox Turbo `0.1.7`, code commit `5de7a54aa4e5e2baadb0182dde554908b48b85c2`, weights revision `749d1c1a46eb10492095d68fbcf55691ccf137cd`. Temperature **0.9**, top-p **0.95**, top-k **1000**, repetition penalty **1.2**, seed **1234 reset per section**, reference normalization **true**. CFG/exaggeration remain inactive at zero; no prosody tags or generated-reference chaining. Existing authorized Voice C reference SHA256: `fc03ae6e7225642e8cf83e5160aff1d7f0b3cf17e23045c006d945bdc8b93931`.

Grouping retains C's 600-character cap; actual paragraphs are 373-432 characters. All 97 complete sentences occur exactly once, in order, in model input. Assembly preserves emitted samples, adding only the existing minimum 0.12-second boundary gap. Input coverage does not prove spoken-word correctness.

| Measurement | Result |
| --- | --- |
| Raw / 1.10x duration | 408.160 s / 371.067 s |
| Generation, summed over 16 sections | 371.641 s; generation/audio ratio 0.910 |
| Runtime preparation / model load | 13.143 s / 12.000 s, separate from generation |
| GPU | NVIDIA RTX 4070 Laptop, 8 GiB; PyTorch 2.6.0+cu124 |
| Peak PyTorch allocated / reserved | 3.55 / 4.68 GiB; excludes driver/context memory |
| Generation failures / OOM / detected token-limit hits | 0 / 0 / 0 |
| Maximum speech-token count | 753, below the internal 1000-step limit |
| Reference-voice cosine range | 0.858-0.906 |
| Early / late four-section mean cosine | 0.883 / 0.887; no downward proxy trend |
| Cosine to first section, remaining sections | 0.968-0.981 |

Similarity proxies cannot establish perceived identity or pronunciation. Raw peaks reach +1.153 dBFS (214 samples above full scale); use the safe listening copy. Original master/section hashes remain unchanged after processing and transcription.

## Word and delivery checks

Unprompted local **Whisper small.en** found **13 normalized word edits / 1,120 normalized words (1.16%)**. Normalization changes the word count. Greedy and beam decoding agreed on the main flags; focused short-window decoding checked for chunk-overlap artifacts. ASR may mishear or hallucinate, so this is not a certified speech error rate.

| Passage | Observation and listening action |
| --- | --- |
| Section 6, raw 2:02-2:32; tempo about 1:51-2:19 | Both full-section and focused decoding detect an extra **“Sometimes the promising result leads nowhere”** after the intended sentence. This is a repetition concern, not a token-limit issue. [Focused clip](../benchmarks/results/expressive-delivery/C-long-form-2026-11-15/review-section-06-possible-repeated-phrase.wav). |
| Section 9 | “Consider the shelves themselves” is recognized as “Consider the chefs”; “through constant attention” and “cart” are also unstable. Exact pronunciation/word fidelity is unresolved. [Opening clip](../benchmarks/results/expressive-delivery/C-long-form-2026-11-15/review-section-09-shelves-and-through.wav), [later clip](../benchmarks/results/expressive-delivery/C-long-form-2026-11-15/review-section-09-cart-pronunciation.wav). |
| Sections 3 and 12 | Possible article substitutions: “a display” / “the display,” and “a class” / “the class.” Check exact wording. |
| Section 4 | Whole-section ASR heard “disc”; focused decoding recovered the expected “desk.” Treat this as uncertain recognition, not a confirmed speech error. |

Full [transcripts/alignments](../benchmarks/results/expressive-delivery/C-long-form-2026-11-15/word-coverage.json) and [focused checks](../benchmarks/results/expressive-delivery/C-long-form-2026-11-15/word-coverage-focused.json) are preserved. All 16 endings have no last-five-word mismatch; internal errors remain. No script prompt or narration regeneration concealed flags.

**Acceptance:** duration, no OOM, sentence input boundaries, and raw preservation pass. Repetitions/omissions and pronunciation are **not cleared**. Audible identity drift, pacing, transitions, and artifacts remain **pending listening**. No proxy deterioration or internal quiet run over 0.90 seconds was detected; neither establishes naturalness.

## Preservation and reproducibility

Production source and saved project/reference hashes remain unchanged. No UI, defaults, validators, export behavior, or dependency locks changed. Both app ports respond, and all **55 tests pass**. Integration remains blocked pending review.

Validation-only Whisper weights are pinned to `e8727524f962ee844a7319d92be39ac1bd25655a` in ignored `model-cache/validation-asr/`, with a checksum manifest. The [checkpoint](https://huggingface.co/openai/whisper-small.en) declares Apache-2.0; [upstream](https://github.com/openai/whisper/blob/main/LICENSE) uses MIT. Existing Transformers required no package installs. Inference was local/offline; nothing was uploaded. The one-time 6.6-minute weight download is excluded from generation timing.

```powershell
.\.venv-chatterbox\Scripts\python.exe -B -u scripts\expressive_delivery_experiment.py --long-form-script benchmarks\scripts\C-long-form-library.txt --output benchmarks\results\expressive-delivery\new-long-form-run
.\.venv-chatterbox\Scripts\python.exe -B -u scripts\validate_long_form_words.py --run benchmarks\results\expressive-delivery\new-long-form-run
```

Commands refuse existing outputs. One script/seed cannot establish general reliability. **Stop for listening review; no integration.**
