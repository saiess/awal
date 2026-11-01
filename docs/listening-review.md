# Listen before selecting the production voice

All samples below are unchanged copies of raw benchmark WAVs under randomized labels. Do not open `listening-key.json` until after rating if you want to avoid knowing the model names. This is only partially blind: one candidate uses a preset, while two clone your recording, so their voice identities can reveal that distinction.

| Test | A | B | C |
|---|---|---|---|
| Neutral explainer | [Listen](../benchmarks/results/listening/A-neutral.wav) | [Listen](../benchmarks/results/listening/B-neutral.wav) | [Listen](../benchmarks/results/listening/C-neutral.wav) |
| Documentary/dialogue | [Listen](../benchmarks/results/listening/A-documentary.wav) | [Listen](../benchmarks/results/listening/B-documentary.wav) | [Listen](../benchmarks/results/listening/C-documentary.wav) |
| Numbers/names/acronyms | [Listen](../benchmarks/results/listening/A-pronunciation.wav) | [Listen](../benchmarks/results/listening/B-pronunciation.wav) | [Listen](../benchmarks/results/listening/C-pronunciation.wav) |
| Long narration | [Listen](../benchmarks/results/listening/A-long.wav) | [Listen](../benchmarks/results/listening/B-long.wav) | [Listen](../benchmarks/results/listening/C-long.wav) |
| New-process neutral repeat | [Listen](../benchmarks/results/listening/A-restart.wav) | [Listen](../benchmarks/results/listening/B-restart.wav) | [Listen](../benchmarks/results/listening/C-restart.wav) |

Compare with [your reference](../benchmarks/results/reference/reference.wav). Rate naturalness separately from resemblance to your voice. Use the same playback device and a comfortable volume. The recordings have no loudness matching or enhancement, so raw volume differences are not evidence of better quality.

Fill [the score sheet](../benchmarks/results/listening/scores.csv), with 1=poor and 5=excellent. Rate naturalness, pronunciation, voice consistency between segments, reference similarity (N/A for the preset), and freedom from objectionable artifacts. Note missing/repeated words, mispronunciations, hiss/buzz, or unnatural breaks. The [source scripts](../benchmarks/scripts/) are available for comparison.

Listen to the beginning, middle, and end of each long clip, and compare its voice with the short cases. Compare neutral with restart for identity after a new process. Matching PCM in a seeded repeat establishes numerical repeatability; it does not replace these listening judgments.

The proposed acceptance gate is average naturalness >=4/5, narrator consistency >=4/5, no frequent missing/repeated words or major artifacts, and successful 5–10-minute execution. No subjective scores have been assigned by Codex. The application remains unbuilt until you review the results and approve an engine.
