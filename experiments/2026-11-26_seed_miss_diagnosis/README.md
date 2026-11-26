# Existing-seed missed-GT diagnostic

GPT Sol, 2026-11-26; original B/B2 runs and reused `match_chunk` by Claude Opus 5.5.

Scope: existing B (1280 seed 0) and B2 (1280 seed 1), selection plus clear-day/night test; no inference, fitting, threshold selection, GPU calls or NightOwls scoring. Stop after one empirical overlap analysis, exact published-marginal accounting, figure and handback. This is not a formal review.

Run from the repository root in PowerShell. Set `$CpuPython` and `$PlotPython`
to the existing CPU and plotting interpreter executables, `$BddInputs` to the
local BDD experiment inputs, and `$PrivateEvidence` to a private, git-ignored
output directory. Supply these machine-specific values locally:

```powershell
& $CpuPython -B experiments/2026-11-26_seed_miss_diagnosis/diagnose.py --inputs $BddInputs --private-out $PrivateEvidence
& $PlotPython -B experiments/2026-11-26_seed_miss_diagnosis/figure.py
```

The private caches `B_matches.json` and `B2_matches.json` retain person scores, image IDs, evaluator annotation IDs, unique image/geometry keys, boxes and heights; they must not enter Git. Existing prediction hashes, GT hash and evaluator/helper hashes guard cache reuse. New overlap analysis uses exact geometry-key joins; GT order is only used inside the unchanged matcher to construct its own annotation IDs. Duplicate geometry keys fail closed rather than guessing identity. Height bins partition the full matched population without rematching or changing the denominator.

Public `counts.json` contains integer aggregate counts only (including selection accounting). Each 3×3 matrix uses B rows, B2 columns, state order absent / below threshold / detected. “Absent” means unmatched by the frozen greedy evaluator at the candidate floor, not proof no overlapping raw box exists. “Swapped” means exactly one run detected the GT, not a pairing of one lost person with one gained person. Per-GT union counts are descriptive; they are not a measured deployable ensemble.

`provenance.json` retains frozen thresholds and file hashes separately from counts. The real-data accounting assertions check the hash-frozen GT, prediction coverage/floor/cap, identical GT geometry keys and heights, height-bin totals, all overlap totals, and exact published TP/FP/ceiling marginals on selection, clear day and night at both policies. PASS on the real cached predictions; no synthetic test, hypothesis test, seed-variance estimate or new confidence interval was used. CPU matching ran once per run, with caches reused for the provenance correction. New GPU spend: 0 CU. No paid resource was allocated.

The note and figure use only public counts. Preserve the two-seed limitation and the core report's distinction between absolute absence and ceiling difference. The unavailable peer contact is recorded in `docs/research/2026-11-26_seed_miss_diagnosis/discussion.md`. A separate independent GPT Sol review subsequently passed scientific accounting; its required private-path correction and optional terminology correction are resolved in publication. My explicit approval still governs any later merge.
