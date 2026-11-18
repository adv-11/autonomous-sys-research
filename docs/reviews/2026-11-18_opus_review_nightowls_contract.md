# Review: NightOwls external transfer contract

**Reviewer:** Claude Opus (independent review task), 2026-11-18 UTC. Read-only. No files in GPT Sol's worktree were edited, and no commits, pushes, Colab or GPU work were done.
**Target:** branch `gpt-nightowls-external-contract`, head `8a89a635`. Preregistration commit `d59e2186`; base `main` `6d18136`. I reviewed `git diff 6d18136..8a89a635`.
**Verdict: ready after fixes.** The adapter, the counts and the archive claims check out against real data. One high-severity design issue should be fixed before any NightOwls predictions exist, because fixing it later would make the fix post hoc. It needs no GPU.

## Findings (most severe first)

### H1. The BDD threshold and the NightOwls target count different pedestrians, which biases the transfer gap and the clear-day reference
`docs/research/2026-11-17_nightowls_external_contract.md:110-116, 131-138`

The only feasible preregistered transfer cell is B at .80, with t\* = 0.014860522. That threshold was chosen to give 0.80 recall on **all** BDD pedestrians: every height and occlusion state, and no ignore regions (`config.json` → `evaluation.ignore_policy: "reject"`; `match_chunk` with `min_h=0`, `evaluate_transfer.py:147-158`). The NightOwls target is Reasonable: height ≥ 50 px, not occluded, and every other box treated as an ignore region. At this same t\*, `B_1280.json` already reports BDD recall well above 0.80 on taller pedestrians:

| t\* = 0.01486 | 32–64 px | 64–128 px | ≥128 px | overall |
|---|---|---|---|---|
| BDD selection | 0.811 | 0.925 | 0.928 | 0.800 |
| BDD val clear_day | 0.832 | 0.930 | 0.958 | 0.811 |

Even with no domain shift, a Reasonable population is therefore expected to reach roughly 0.87–0.93 recall at t\*, not 0.80. Measuring "recall vs target .80" (target-gap identity) on NightOwls Reasonable overstates transfer by roughly 0.08–0.1, purely because of definitions. The clear-reference loss identity has the same flaw: it compares BDD clear-day all-height recall (0.811, ceiling 0.897) with NightOwls Reasonable recall, so the night loss is understated. The contract says the populations differ (line 136-138), but it still uses both identities without a comparator that applies the same definitions.

**Fix, before predictions, CPU-only:**
- Add a BDD comparator restricted to pedestrians ≥ 50 px, with shorter pedestrians as ignore regions. The existing `--min-height` path already does this matching (`evaluate_transfer.py:147-158`; eligible means h ≥ min_h, matching NightOwls' ≥ 50).
- On that comparator, report BDD selection and clear-day recall and FPPI at the **transferred all-height t\***. That is the no-shift expectation.
- Use it as the clear reference for the loss identities. Keep the all-height comparison only as a labelled secondary.
- Disclose that BDD occlusion cannot be matched: `prep.py:63` keeps only boxes, so the "not occluded" mismatch remains.
- Optionally, preregister an h ≥ 50 BDD source-selection policy, labelled exploratory and post hoc on BDD but fixed before NightOwls. It would probably make A and C testable as well: their h ≥ 32 policies are already feasible at .80 (0.0273 and 0.0259), while all their all-height targets are infeasible.

### M1. FPPI under the primary ignore policy is not comparable to BDD
`contract:41-49, 99-101`

BDD counted every unmatched pedestrian-class output as an FP, with no ignore regions and riders as their own class. Under the NightOwls primary profile, unmatched outputs are absorbed by many regions. My count over the 51,782-frame cohort:
- 6,316 category-4 ignore boxes
- 585 rider boxes (324 category 2, 261 category 3)
- 2,520 ineligible pedestrians

That is 9,421 absorbing regions against 7,631 eligible GT. The secondary profile still absorbs the 2,520 ineligible pedestrians. The contract does not say which profile's FPPI or precision enters BDD-vs-NightOwls contrasts.

**Fix:** state that cross-dataset FPPI and precision contrasts use the h ≥ 50 BDD comparator from H1, report both NightOwls profiles, and label primary-profile FPPI as not comparable to BDD.

### M2. The input-scale mismatch is noted but not analysed, so native-pixel height bins are confounded
`contract:66, 82-84`

Under letterboxing, BDD is resized by 0.5 at imgsz 640 and NightOwls by 0.625. At 1280 the factors are 1.0 and 1.25. A NightOwls pedestrian of a given native height therefore reaches the model **1.25× taller** than a BDD pedestrian of the same height. For example, h = 50 px becomes 31.25 px of model input on NightOwls versus 25 px on BDD for runs A and C. Recall depends strongly on size: A's selection ceiling is 0.51 at 16–32 px and 0.81 at 32–64 px. The scale difference therefore favours NightOwls in per-height and clear-day contrasts. B also runs above NightOwls' native resolution, whereas B on BDD ran at native resolution.

**Fix:**
- Record the per-run scale factors.
- Also report heights in model-input pixels (native height × scale), or label native-pixel bin comparisons as scale-confounded.
- A scale-matched sensitivity (A/C at 512, B at 1024) would need new inference, so it is the coordinator's budget decision. Keeping imgsz fixed per run is defensible as long as this is stated.

### M3. One recording dominates the cluster bootstrap, and the contract drops recording-wise reporting
`contract:151-166`

Reasonable eligible GT per known recording key is 4,994 / 1,005 / 332 / 291 / 149. One key holds 65%, and the unkeyed frames hold 860 (11%), which the bootstrap holds fixed. About 0.8⁵ ≈ 33% of replicates will leave out the dominant key, and only 126 distinct key multisets exist, so the intervals will be lumpy or multimodal. The contract does call them descriptive (line 164-166). However, it leaves out the 2026-11-13 policy's per-recording counts and support floor: ten jointly ceiling-covered eligible GT per key, the 150-box operational floor, and distinct-track counts (`docs/decisions/2026-11-13_nightowls_external_policy.md`, "Population and grouping").

**Fix:**
- Preregister per-recording point estimates under pseudonymous labels R1–R5 (aggregates only; no native keys committed), with the support-floor status for each.
- Add a leave-one-recording-out pooled estimate, at least without the dominant key.
- Disclose the 126-multiset limit.

### L1. The contract was edited after it was frozen, without an amendment note
`contract:6, 195`

Commit `8a89a63` changed the disk figure from "57.47 GB" to "57.60 GB" after `d59e218`, but the contract says it is frozen by its first commit. The change is substantively harmless: 57,595,824,667 bytes is correct, and no predictions existed. The other changes after the freeze cannot affect the analysis: adapter docstring wording, a stricter output-path guard in `prepare_nightowls_transfer.py`, and catching `zlib.error` in the verifier. Record these as corrections made before predictions.

### L2. Colab disk and download cost are only conditionally feasible
`contract:183-201`

If the images are extracted, the peak footprint is 57.48 GB of archive plus 57.60 GB of images, about 115 GB before outputs. That may exceed free disk on some Colab runtimes. Downloading on a GPU runtime also spends compute units while the GPU sits idle, and the budget excludes that time.

**Suggestion:** decode PNGs directly from the CRC-verified ZIP instead of extracting them, which keeps peak disk around 60 GB. Set an abort threshold on download throughput or elapsed time. The server supports range requests (206), so a download can be resumed.

## Verified (no objection)

- **Matching matches BDD.** The contract uses `ReferenceEvaluator` unchanged (`metrics.py:115-145`): score-descending order with candidate-ID ties, highest-IoU eligible GT at ≥ .50 with annotation-ID ties, then reusable ignore absorption by IoA over prediction area. Score floor 1e-4, cap 3000 across all classes before keeping class 0, class-aware NMS 0.70 and FP32 all match `config.json`. The ceiling is defined as the full greedy prefix. Zero-area outputs are explicit FPs, as in `match_chunk`. Height bins are the same five native-pixel bins (`common.py:22`).
- **Thresholds.** B .80 t\* = 0.014860522001981735 equals `B_1280.json`. A and C are infeasible at all three targets, and B at .90 and .95. Low-target and h ≥ 32 thresholds exist as stored.
- **SDK setups,** checked against the pinned `eval_MR_multisetup.py`: HtRng `[[50,1e10],[50,75],[50,1e10],[20,1e10]]`, VisRng `[[.65,∞],[.65,∞],[.2,.65],[.2,∞]]`, `vis_ratio = 0.5 if occluded else 1.0`, `expFilter 1.25` (giving 50/1.25 = 40 px, as stated), and `maxDets 1000`. The adapter's `SETUPS` and visibility mapping (`nightowls.py:23-26, 137-141`) match.
- **Adapter on real labels.** I ran an independent count script against the real labels (aggregates only, nothing committed), and ran the adapter with both profiles and all four setups. Results:
  - Images: 51,848 = 51,846 night + 2 dusk; the 64 pilot images are all night, leaving **51,782**. All images are 1024×640.
  - Frames: **42,316** natively empty; **1,304** unkeyed; five keys.
  - Eligible GT: Reasonable **7,631** (860 unkeyed); Reasonable_small 2,396; Reasonable_occ=heavy 1,165; All 10,142.
  - Ignored records: 9,421 under the primary profile, 2,520 under the secondary.
  - `ReferenceEvaluator.gt_count` equals the eligible count in every case, and every retained box uses the token `pedestrian`.
  - Native `ignore` is 1 only for category 4, so it removes no pedestrians in practice.
  - 125 eligible GT extend out of frame. Their smallest in-frame fraction is 0.65, so a perfect frame-clipped prediction still matches every one of them (IoU ≥ .50).
- **Tests.** All 10 NightOwls and ZIP tests pass with the specified interpreter. The full suite ran 188 tests with 1 failure and 2 errors, all environmental and outside this diff: `numpy` is missing in the base interpreter, and one CLI subprocess cannot import the package under `-I`.
- **Archive.**
  - Annotation SHA-256 `584c0dc1…a9b6` matches.
  - ZIP central directory: 51,849 members (1 directory, 51,848 unique PNGs), 57,595,824,667 bytes uncompressed, basenames identical to the native table, all 51,782 cohort PNGs present.
  - Local size is 57,481,286,834 bytes.
  - My own unauthenticated ranged HEAD request returned 206, `Content-Range: bytes 0-0/57481286834`, and the same ETag and Last-Modified. No credentials were needed.
  - Full re-hash: see the addendum.
- **Restricted content.** The diff contains no image names, boxes, image IDs or recording keys. `data/**` and `outputs/` are gitignored. Private canonical files stay under `outputs/`.
- **Preregistration timing.** `d59e218` (07:41:35Z) predates any NightOwls predictions. None exist in the main checkout or any worktree. The only "night" NPZs (`outputs/bdd_transfer_20261115/stage2/preds/nightcal_*.npz`, 07:53Z) are BDD: 2,000 images at 720×1280, `image_set: nightcal`. The remote branch head is `8a89a635`. Commit times are self-reported, so the evidence is that no predictions exist, not a trusted timestamp.
- **Arithmetic.** 3 × 51,782 = 155,346 images. Scaling the BDD timings by 4.373× gives about 9.7, 15.2 and 9.1 minutes for A, B and C.

## Addendum: full archive SHA-256
I re-hashed the local ZIP independently (base CPython, `-I`, 100.7 s): `6663dc5099714ffb8c18bb37942ce523de9dfdda44327284bdab12354e8fcf9d`. This **matches** the verification note and the contract. Like Sol's hash, it is a local first reference, not a checksum authenticated by the publisher. I did not repeat the member CRC pass.
