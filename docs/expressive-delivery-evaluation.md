# Awal: expressive speech delivery evaluation

Experiment date: 2026-11-15. **Listening approval pending. Nothing is integrated into production.**

**Segmentation-only follow-up:** reviewers preferred C's sentence continuity, but its temperature change was a confound. One additional configuration, D, now tests A's exact baseline sampling with C's exact segmentation. D removes the same boundary without higher temperature; it also has a longer pause that needs listening review. **Review D next and prefer it if delivery is at least as good as C; production remains on A.** See [the A/D/C control comparison](#segmentation-only-control-adc) below. The original A/B/C experiment and audio are preserved.

## Initial three-way result and decision

Exactly three configurations use the same authorized Voice C reference and the same 174-word documentary script. A is the current generation baseline; B tests a modest sampling change; C adds complete-sentence, paragraph-aware context to B. These names describe hypotheses, not quality rankings.

**Keep production on A until listening review.** C is the candidate to assess first for a later integration because it removes an observed mid-sentence boundary, not because acoustic metrics establish that it sounds better. Approve it only if its flow improves while word accuracy, voice identity, and artifacts are at least as good as A. If B sounds better than C, prefer B; if neither is clearly better, retain A. No Dessa-equivalence claim is made.

The run, independent raw sections, exact text, settings, hashes, traces, and measurements are in [the experiment directory](../benchmarks/results/expressive-delivery/2026-11-15/). Audio stays local and is ignored by Git. The previous benchmark framework was removed during the requested cleanup; this experiment uses one isolated script and the existing engine/audio helpers rather than rebuilding a framework.

## Start listening here

Use headphones and a fixed volume. First compare these **1.00x, statically level-matched** copies to avoid mistaking louder or faster speech for better expression:

| Sample | Listen |
| --- | --- |
| A: baseline | [A at 1.00x](../benchmarks/results/expressive-delivery/2026-11-15/A_baseline_listening_levelmatch_1.00x.wav) |
| B: sampling hypothesis | [B at 1.00x](../benchmarks/results/expressive-delivery/2026-11-15/B_expressive_listening_levelmatch_1.00x.wav) |
| C: context hypothesis | [C at 1.00x](../benchmarks/results/expressive-delivery/2026-11-15/C_context_listening_levelmatch_1.00x.wav) |

Then check the preserved **unprocessed masters**:

- [A raw](../benchmarks/results/expressive-delivery/2026-11-15/A_baseline_raw_1.00x.wav)
- [B raw](../benchmarks/results/expressive-delivery/2026-11-15/B_expressive_raw_1.00x.wav)
- [C raw](../benchmarks/results/expressive-delivery/2026-11-15/C_context_raw_1.00x.wav)

Optional, identically processed tempo comparisons: [A 1.10x](../benchmarks/results/expressive-delivery/2026-11-15/A_baseline_tempo_1.10x.wav), [B 1.10x](../benchmarks/results/expressive-delivery/2026-11-15/B_expressive_tempo_1.10x.wav), [C 1.10x](../benchmarks/results/expressive-delivery/2026-11-15/C_context_tempo_1.10x.wav). These use only FFmpeg `atempo=1.1`; tempo acceleration is **not** evidence of improved generation.

Every emitted section is also retained under `A_baseline/`, `B_expressive/`, and `C_context/` as `section-NN_raw.wav`. These are 24 kHz mono float WAVs, including the model's normal PerTh watermark. Masters concatenate the untouched sections and use the same existing minimum 0.12-second boundary gap rule. No edge trimming, fades, compression, gain normalization, or peak attenuation touches the raw masters. The separate level-matched copies apply static gain only; no changes to rhythm or pauses. No best-of selection or regeneration was used.

## Exact configurations

All configurations use code `0.1.7` at commit `5de7a54aa4e5e2baadb0182dde554908b48b85c2`, model `ResembleAI/chatterbox-turbo` at revision `749d1c1a46eb10492095d68fbcf55691ccf137cd`, and the same reference file:

`data/narrators/c6b8beb1-f01e-49ff-a91c-96ac751b5b71/reference.wav`

Reference duration: 19.1135 seconds. SHA256: `fc03ae6e7225642e8cf83e5160aff1d7f0b3cf17e23045c006d945bdc8b93931`. Saved permission explicitly covers cloning and commercial publication. No reference was cropped, replaced, or generated from previous output.

| Setting | A baseline | B expressive hypothesis | C context hypothesis |
| --- | --- | --- | --- |
| Seed, reset on each section | 1234 | 1234 | 1234 |
| Temperature | 0.8 | 0.9 | 0.9 |
| Top-p | 0.95 | 0.95 | 0.95 |
| Top-k | 1000 | 1000 | 1000 |
| Repetition penalty | 1.2 | 1.2 | 1.2 |
| `norm_loudness` on reference | true | true | true |
| `cfg_weight`, `exaggeration` | 0.0, 0.0 (ignored) | 0.0, 0.0 (ignored) | 0.0, 0.0 (ignored) |
| `min_p` | model default 0.0 (ignored) | same | same |
| Text grouping | existing 350-character segmentation | identical to A | complete sentences, paragraph boundaries, maximum 600 characters |
| Actual section lengths | 348, 72, 339, 260 | identical to A | 421, 339, 260 |

B changes **only temperature**, modestly widening the speech-token sampling distribution. It is not an emotion-strength setting, and more randomness can also worsen diction or stability. Repetition penalty is held fixed to avoid confounding this test. C retains B's settings as the provisional candidate and changes only grouping; B was not declared a perceptual winner before generating C.

The full script is [script.txt](../benchmarks/results/expressive-delivery/2026-11-15/script.txt). Its generation-text SHA256 is `07faa361303a886766e7fe8a209266ed43f38f2ec41bcb43626a720665553a2a` (without the file's final newline). Whitespace-normalized text identity across all three sets of sections is asserted. The long opening sentence deliberately tests the current boundary limit; this is a focused stress test, not a broad narration corpus.

## What the pinned implementation actually supports

This assessment follows the installed Turbo path, not configuration names or generic tips for other Chatterbox models. Sources: pinned [Turbo implementation](https://github.com/resemble-ai/chatterbox/blob/5de7a54aa4e5e2baadb0182dde554908b48b85c2/src/chatterbox/tts_turbo.py), [T3 sampling implementation](https://github.com/resemble-ai/chatterbox/blob/5de7a54aa4e5e2baadb0182dde554908b48b85c2/src/chatterbox/models/t3/t3.py), and installed conditioning encoder. Their local source hashes and the actual generation signature are in the measurement manifest.

- **Temperature, top-k, top-p, repetition penalty:** actually passed to `inference_turbo` and used as logits processors before stochastic token sampling. The run records the effective forwarded values for every section. They affect token choices, not explicit semantic stress labels or a prosody curve.
- **CFG, exaggeration, min-p:** accepted by the public function but explicitly ignored by Turbo. Its emotion-conditioning branch is disabled and CFG is fixed to zero in the Turbo inference path. Increasing these would not be a valid experiment. The commonly cited CFG/exaggeration tips belong to original Chatterbox, not this Turbo path.
- **Reference conditioning:** a reference longer than five seconds is required internally. Optional reference loudness normalization targets -27 LUFS. The acoustic reference uses the first 10 seconds, T3 prompt tokens use up to the first 15 seconds (375 tokens), and speaker embedding uses the loaded reference. A longer recording does not provide unlimited style context. All three use the same full 19.1135-second recording and normalization.
- **Text boundaries:** punctuation normalization collapses whitespace, maps a colon to a comma and ellipsis to a comma, normalizes quotes/dashes, and appends ending punctuation if absent. Blank lines inside one call are not an explicit pause command. Separate paragraphs remain separate calls here. C provides more uninterrupted text/speech history within its opening call; it does not carry conversation state between calls.
- **Seed:** the production wrapper seeds PyTorch inside a saved RNG context. Fixed seeds make this comparison controlled; production retries still use fresh recorded seeds. Changing a seed offers another take, not a guarantee of better expression or cross-platform bitwise reproducibility. A changed text boundary also changes the sampling trajectory.
- **No direct public controls** for pitch contour, stress on a particular word, semantic emphasis, speaking rate, SSML, or a generic emotional/style instruction. The model card documents nonverbal tags, but injecting laughs/coughs would change this documentary's content and is not a substitute for natural narration; none were added.
- **Length/reliability:** the internal speech-token loop has a 1000-step limit; public `generate` does not expose `max_gen_len`. Longer calls can increase truncation risk. Token counts and potential-limit flags are recorded. C is bounded and never silently chops an oversized sentence.

The five application files were also reviewed. `jobs.py` keeps the saved reference consistent, records retry seeds, and preserves successful raw versions. `audio.py` already handles export tempo, conservative join cleanup, and sample peaks. Those operations can polish timing or levels but cannot create semantic emphasis, fix pronunciation, or establish human-like prosody. They remain unchanged and are bypassed for this raw-generation comparison.

## Measurements and technical observations

Hardware: NVIDIA GeForce RTX 4070 Laptop GPU, 8.00 GiB VRAM; PyTorch 2.6.0+cu124, CUDA 12.4. Shared native-runtime preparation: 16.90 s; one shared verified model load: 17.77 s.

| Configuration | Sections | Raw duration (s) | Generation (s) | Generation / audio time | Peak allocated / reserved (GiB) | Script-implied WPM | Quiet runs >=200 ms | Quiet frames |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | 4 | 65.16 | 52.39 | 0.804 | 3.24 / 3.78 | 160.2 | 20 | 21.9% |
| B | 4 | 64.56 | 48.70 | 0.754 | 3.27 / 4.12 | 161.7 | 15 | 19.4% |
| C | 3 | 64.48 | 45.41 | 0.704 | 3.43 / 4.54 | 161.9 | 14 | 19.4% |

The three level-matched copies share **-24.455 LUFS**. Static gains for A/B/C are -1.20 dB, -2.20 dB, -2.54 dB. All remain at or below -1 dBFS sample peak. Raw durations are essentially unchanged: B is 0.60 s shorter than A and C is 0.68 s shorter; this is not evidence of more expressive delivery.

Technical checks passed for all 11 emitted sections and all nine comparison masters. There were no generation failures, nonfinite outputs, or possible speech-token-limit hits. Maximum observed speech-token counts for A/B/C were 555, 580, 684. The ordinary dependency warning about `LoRACompatibleLinear` deprecation appeared; no dependency was upgraded.

The raw A master peaks at **+0.195 dBFS** (three float samples above full scale); B and C peak at **-0.004 dBFS**. These float masters are preserved exactly, but full-scale playback or integer conversion can clip A. Use the safe level-matched copies first; the optional tempo-only copies deliberately do not add peak limiting.

Reference speaker-embedding cosine ranges: A 0.869-0.899; B 0.875-0.903; C 0.875-0.897. Adjacent-section cosine ranges: A 0.930-0.971; B 0.926-0.971; C 0.968-0.971. Different section lengths confound comparisons; do not interpret these ranges as proof of better identity preservation.

The two paragraphs whose text, settings, and seed are unchanged between B and C have **bit-identical decoded float samples** in this run. Their WAV container hashes differ, so this was checked by decoding and comparing every sample rather than comparing file hashes. The B/C delivery difference is localized to the first paragraph and its removed split, making that passage the most informative listening comparison. All saved project/narrator files and production source hashes were rechecked unchanged.

Numbers describe performance, timing, and similarity proxies; they are **not naturalness scores**. Script-implied WPM divides the fixed script word count by duration; no recognizer has verified that every word was spoken. Pause detection uses 10 ms RMS frames below -45 dBFS and counts internal quiet runs of at least 200 ms. Quiet is not synonymous with a meaningful pause. Speaker cosine uses the already-loaded voice encoder, not an independent identity test; higher similarity does not establish more natural delivery.

One short script and one seed per section cannot establish long-recording identity stability, general pronunciation accuracy, or reliability across seeds. GPU reserved memory includes allocator cache carried between configurations; allocated peaks include the resident model. They exclude driver/context memory. Generation timing includes reference conditioning but excludes the shared model load and separate measurement work. One model was loaded once, configurations ran A then B then C, and A includes first-generation warm-up effects. Do not rank speed from these single passes.

The measurable segmentation change is one fewer generation boundary (4 sections to 3), eliminating a mid-sentence cut after **“most residents”**. Baseline normalizes that incomplete chunk with a period before **“have opened their eyes.”** C keeps those words in the same utterance. This is a verifiable structural improvement, not proof of a perceptual win.

## Human listening worksheet

Listen in an order such as B, A, C, then C, B, A; avoid assuming the “expressive” label means better. Record timestamps and exact words for any problem. Suggested notes:

| Criterion | A | B | C |
| --- | --- | --- | --- |
| Natural conversational flow, without sounding acted | Pending | Pending | Pending |
| Rhythm varies appropriately rather than randomly | Pending | Pending | Pending |
| Pauses help meaning, without rushed joins or awkward stops | Pending | Pending | Pending |
| Question intonation and emphasis fit the script | Pending | Pending | Pending |
| No omitted, added, repeated, or mispronounced words | Pending | Pending | Pending |
| No clicks, buzzing, breath artifacts, warble, or rough endings | Pending | Pending | Pending |
| Same Voice C identity and accent across sections | Pending | Pending | Pending |

Pay particular attention to:

1. The opening sentence: does C sustain natural breath groups, or does the longer context make it rush? Does A/B sound as though the thought ends at “most residents”?
2. “But what happens when the weather changes?” Does the question sound conversational, with a sensible transition into the warning?
3. “The right person,” “the right question,” and “one small detail”: is emphasis meaningful rather than uniformly stressed?
4. “That is the surprising part”: is the contrast clear without melodrama? Is the final sentence complete?
5. “Harbor,” “breakwater,” “coordinated,” and every word around section boundaries: check pronunciation and exact wording against the script. Check pitch/accent changes at the two paragraph joins.

No human ratings or word-accuracy claims have been invented. Automatic checks cannot settle these questions. Approval should require a noticeable delivery improvement with no regression in identity, words, or artifacts, not simply a faster or more varied waveform. A later approved trial on a genuinely long script would still be needed.

## Local operation, licensing, and reproducibility

The experiment uses only installed, pinned Turbo weights and existing approved dependencies. HF/Transformers offline flags are set, external TCP connections are blocked inside the generation process, and model loading uses the app's existing local-only, checksum-verified path. Public upstream documentation was consulted separately; no voice, text, or audio was sent to an inference service. No cloud API or new model was introduced.

The pinned [Chatterbox code license](https://github.com/resemble-ai/chatterbox/blob/5de7a54aa4e5e2baadb0182dde554908b48b85c2/LICENSE) is MIT, as is the model declaration in the retained pinned `docs/licenses/turbo-README.txt`; the [official model card](https://huggingface.co/ResembleAI/chatterbox-turbo) also declares MIT. Existing dependency notices and commercial-use compatibility are retained. The web viewer could not retrieve the historical Hugging Face card URL; the pinned local copy supplies that evidence. Reference permission is recorded in the narrator profile.

[Block's Dessa page](https://block.xyz/dessa) demonstrates conversational speech-to-speech behavior. It is an aspirational delivery reference here, not an evaluated fourth model or a demonstrated capability of Turbo. No Dessa audio was cloned, used as conditioning, or included in these samples.

Run again into a **different, new directory**:

```powershell
.\.venv-chatterbox\Scripts\python.exe -B -u scripts\expressive_delivery_experiment.py --output benchmarks\results\expressive-delivery\another-run
```

The script refuses an existing output directory, records settings and per-section timings/memory, and verifies production source/reference/project hashes afterward. [measurements.json](../benchmarks/results/expressive-delivery/2026-11-15/measurements.json) is the machine-readable evidence. Production settings, project records, raw audio, selective regeneration, references, export behavior, UI, and model versions have not been changed. A context candidate above 350 characters is not a drop-in production setting: the current section editor/API also have a 350-character limit, which would need a separately approved design if C wins.

**Stop point: experiment and report only. Await listening review before integration.**

## Segmentation-only control: A/D/C

The reviewer preference for C motivates this control; it is not approval to integrate C. **D is baseline sampling plus C's segmentation**, not a newly tuned model. Exactly one new configuration was generated, with no retries, best-of selection, new dependencies, or production changes. A and C are reused from the original run, not regenerated.

| Variable | Existing A | New D | Existing C |
| --- | --- | --- | --- |
| Temperature | 0.8 | **0.8** | 0.9 |
| Grouping | Existing 350-character splitting | **C's complete-sentence, paragraph-aware grouping** | Complete-sentence, paragraph-aware grouping |
| Actual section lengths | 348, 72, 339, 260 | **421, 339, 260** | 421, 339, 260 |
| Seed per call | 1234 | **1234** | 1234 |
| All other sampling/reference settings | Original baseline | **Exactly original baseline** | Original baseline |

Thus **A versus D isolates segmentation**, and **D versus C isolates temperature** at the same segmentation. Same script SHA256, reference SHA256, model/code revisions, installed Turbo source hashes, and reference-normalization settings are checked by the runner. D has top-p 0.95, top-k 1000, repetition penalty 1.2, `norm_loudness=true`, CFG/exaggeration 0.0, and default inactive min-p 0.0. No new reference conditioning, punctuation rewriting, or export cleanup is introduced. The existing 600-character context bound is unchanged.

### Listening files

Start with these statically level-matched **1.00x** copies; only D involves new speech synthesis:

- [Existing A, comparison copy](../benchmarks/results/expressive-delivery/2026-11-15-segmentation-control/A_baseline_listening_levelmatch_1.00x.wav)
- [New D, baseline sampling with context](../benchmarks/results/expressive-delivery/2026-11-15-segmentation-control/D_baseline_context_listening_levelmatch_1.00x.wav)
- [Existing C, comparison copy](../benchmarks/results/expressive-delivery/2026-11-15-segmentation-control/C_context_listening_levelmatch_1.00x.wav)

The A/C comparison files are derived into the **new** run directory, so the old raw and listening files are never overwritten. Level matching uses the same original method: choose a common integrated target of -23 LUFS or lower if any raw peak requires it to maintain -1 dBFS headroom, then apply static gain only. No compression, fades, time changes, or pause trimming affect this comparison.

D's untouched [raw 1.00x master](../benchmarks/results/expressive-delivery/2026-11-15-segmentation-control/D_baseline_context_raw_1.00x.wav) and its three emitted `D_baseline_context/section-NN_raw.wav` files are retained. An optional [tempo-only 1.10x copy](../benchmarks/results/expressive-delivery/2026-11-15-segmentation-control/D_baseline_context_tempo_1.10x.wav) is separate; use the 1.00x files to judge delivery. The [new measurement manifest](../benchmarks/results/expressive-delivery/2026-11-15-segmentation-control/measurements.json) records all settings, traces, measurements, comparisons, and integrity checks.

### Results

| Configuration | Raw duration (s) | Generation (s) | Peak allocated / reserved (GiB) | Script-implied WPM | Internal quiet runs >=200 ms | Longest quiet run (s) |
| --- | --- | --- | --- | --- | --- | --- |
| A | 65.16 | 52.39 | 3.24 / 3.78 | 160.2 | 20 | 0.64 |
| D | 67.76 | 54.85 | 3.49 / 3.90 | 154.1 | 15 | 1.63 |
| C | 64.48 | 45.41 | 3.43 / 4.54 | 161.9 | 14 | 0.71 |

D's separate native-runtime preparation took 20.09 s and its verified model load took 16.85 s. Generation timing excludes these and includes first-call warm-up. A/C timings are historical measurements; cross-run timing and allocator cache differences prevent a fair speed ranking. No new performance conclusion is drawn.

All three comparison copies use the **same original -24.455 LUFS target**. The A/C copies decode to exactly the same samples as their original listening files. D requires -2.55 dB static gain and then peaks at -2.36 dBFS. Its raw peak is +0.195 dBFS (four float samples above full scale); this is retained in the raw file, not hard-clipped or normalized away. Use the level-matched copy for safe comparison.

D has no generation errors, nonfinite samples, or detected speech-token-limit hits; its sections contain 719, 555, and 411 speech tokens. The last two paragraphs produce **bit-identical decoded samples to A** at the unchanged settings, despite the fresh process. Only the opening paragraph changes between A and D, providing a particularly clean segmentation comparison.

The opening paragraph is 28.88 s in D versus 26.28 s across A's first two sections, so D is 2.60 s longer overall than A and 3.28 s longer than C. D contains a detected **1.63 s quiet run at 24.11-25.74 s** of its raw/level-matched master, near the end of the opening paragraph. C's longest detected internal quiet run is 0.71 s. This could be a meaningful pause or an awkward delay: listen rather than treating it as improvement. Lower temperature does not automatically mean smoother rhythm. No word-level alignment or ASR was used to assign that pause to specific words.

D's reference speaker-cosine range is 0.869-0.888, within the ranges already seen. Adjacent-section cosines are 0.978, 0.971. These are identity proxies, not proof of human-perceived consistency or a quality ranking. Word accuracy and audible artifacts require listening.

Integrity checks confirm all original experiment files, saved narration/reference files, and production source files are unchanged. The app was idle but holding the model in VRAM; the development server was stopped only to free GPU memory and was restored afterward. No project was created or edited. The earlier launch was blocked before any synthesis because that model was resident; the successful run synthesized D only.

### Listening decision and remaining questions

The structural benefit does not require temperature 0.9: D also removes the mid-sentence cut after “most residents.” Whether that change provides the perceived naturalness benefit must still be judged from D's audio. No unperformed human listening, pronunciation audit, or artifact assessment is reported as completed.

| Criterion | What this control establishes | Listening approval still needed |
| --- | --- | --- |
| Sentence flow | D retains the complete opening sentence, like C | Does D fix the awkward restart as convincingly as C? Does its long opening sentence have natural breath groups? |
| Pronunciation and words | Same exact source words; generation finishes without detected token-limit truncation | Listen against the script for omissions, additions, repeats, and the pronunciation of “harbor,” “breakwater,” and “coordinated” |
| Rhythm and emphasis | Timings and quiet-run statistics are descriptive only | Compare the weather question, “the right person,” and “the surprising part”; avoid preferring speed alone |
| Artifacts | Finite waveform and peak/headroom checks | Listen for buzzing, rough joins, warble, and unnatural breaths |
| Narrator identity | Same authorized conditioning; embedding proxies recorded | Does it still sound like Voice C, with a consistent accent and delivery across all three paragraphs? |

**Conditional recommendation: prefer D if its sentence flow is improved over A and its pronunciation, rhythm, artifacts, and identity are at least as good as C.** That retains the original sampling settings and makes only the segmentation change. Higher temperature is not justified merely by C's earlier preference. If C is noticeably better than D, temperature may matter; record where before considering it. If D does not reliably improve flow, keep A and investigate further. A single script/seed is not evidence of broad reliability or long-form identity stability.

Production remains on A. No segmentation limits, editor/API behavior, sampling defaults, regeneration behavior, references, or export processing have been integrated or changed. Listen in an order such as D, A, C, then C, D, A, and approve explicitly before any integration.

Reproduce only this control into another new directory:

```powershell
.\.venv-chatterbox\Scripts\python.exe -B -u scripts\expressive_delivery_experiment.py --segmentation-control-from benchmarks\results\expressive-delivery\2026-11-15 --output benchmarks\results\expressive-delivery\another-segmentation-control
```
