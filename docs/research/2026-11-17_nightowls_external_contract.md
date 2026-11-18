# NightOwls external threshold-transfer preregistration

**Version history:** the dated [version 2 amendment](2026-11-18_nightowls_contract_v2.md)
supersedes conflicting population, primary ignore, scale, support and Colab
handling rules below. The remaining text preserves version 1's historical
pre-prediction contract; v2 was fixed during prediction generation, before scoring.

I want an external night-pedestrian test of the frozen BDD clear-day-trained
YOLO11s runs A/B/C. GPT Sol prepared this contract on 2026-11-17 Pacific
(2026-11-18 UTC), from `origin/main` `6d1813631519c9e9cfee2fd45b39dc0d4eecc7ca`.
It is frozen by its first Git commit **before any NightOwls predictions**.
Claude Opus confirmed that none exist and that its current Colab assignment
excludes NightOwls until coordinator authorization. No training, model choice,
new inference allocation or merge is authorized here. **G0 remains pending.**

## Data and target

Use the official PNG/JSON validation release linked on the [publisher download
page](https://www.nightowls-dataset.org/download/), accessed 2026-11-18 UTC.
Annotation source: `https://thor.robots.ox.ac.uk/nightowls/python/nightowls_validation.json`,
10,696,948 bytes, SHA-256
`584c0dc11f0d086fc5bcbaca0385cf2dd9794074f815f2727fbf9a093fd9a9b6`.
This matches the already acquired labels; there is no new annotation download.
The image archive and completed checks are recorded in the
[verification note](../datasets/2026-11-17_nightowls_archive_verification.md).

Retain all native `daytime == 'night'` frames, including empty and unkeyed
frames; exclude both dusk frames and the original 64 access-pilot images, as
required by the [full-download decision](../decisions/2026-11-14_nightowls_full_download.md).
Use the exact private pilot manifest (SHA-256
`4f31e685cd3d2d263448e7faf207d80f7befe8c6738b041c3bc4d6614b5de99a`),
never a new seed or inferred exclusions. Final cohort: **51,782 images**,
including **42,316 natively empty frames**, five known recording keys and
1,304 unknown-key frames. Archive PNG names must match the complete native
image table one-to-one before cohort exclusion. Missing images are failures,
not deletions from the denominator. No label-dependent sampling is allowed.

Primary eligibility follows the existing [NightOwls policy](../decisions/2026-11-13_nightowls_external_policy.md):
native category 1 (`pedestrian`), `ignore == 0`, native **unclipped** height
at least 50 pixels, `occluded is not True`. Null occlusion follows the SDK
convention (visible), without asserting visibility. Difficulty/truncation
do not add exclusions. Preserve native xywh boxes and out-of-frame extents;
do not infer visible/amodal extent or repair pose metadata. Primary Reasonable
support is **7,631 eligible GT**, including **860 on unkeyed frames**.

All ineligible pedestrian boxes become ignore regions. Primary
`person_compatible_ignore` also makes categories 2 (`bicycledriver`, person on
bike), 3 (`motorbikedriver`) and 4 (`ignore`) absorbing regions. Riders are
never eligible pedestrians and their vehicle/body extent is not inferred.
The fixed `unused_nonpedestrian` sensitivity omits categories 2/3/4 instead;
pedestrian eligibility and candidate outputs are identical. This needs only
pedestrian-class predictions, **no rider-class outputs**. A rider-class output
is outside the evaluated prediction class; a pedestrian-labelled output on a
rider region is absorbed only under the primary ignore policy.

## Official setups and project height strata

The pinned [official Python SDK](https://github.com/ox-vgg/nightowlsapi/blob/ad0f18fc95e093e86036f055ab210a3de46021b7/python/eval_MR_multisetup.py#L429-L446)
defines four GT setups, checked from source on 2026-11-18 UTC. Upper height
bounds are inclusive; its nominal unlimited bound is 1e10. Visibility is
1.0 for false/null occlusion and 0.5 for true occlusion. Freeze these GT
subset diagnostics now, with Reasonable primary:

| Setup / adapter `setup` | GT height and visibility | Mapping to project bins |
|---|---|---|
| Reasonable / `reasonable` | h ≥50, visibility ≥.65 | [50,64) part of [32,64), [64,128), ≥128 |
| Reasonable_small / `reasonable_small` | 50 ≤h ≤75, visibility ≥.65 | [50,64) and [64,75], splitting the 64 boundary |
| Reasonable_occ=heavy / `reasonable_heavy` | h ≥50, .2 ≤visibility ≤.65 | same height mapping as Reasonable; true occlusion |
| All / `all` | h ≥20, visibility ≥.2 | [20,32) part of [16,32), [32,64), [64,128), ≥128 |

Project bins remain [0,16), [16,32), [32,64), [64,128), ≥128 in **native**
pixels. Do not equate [32,64) with Reasonable_small. Report zero-support bins
as undefined. Within-setup height recall uses the full setup's assignments;
each separate official GT setup reruns eligible-first matching with excluded
GT as ignore. Report its eligible/ignored GT, images and unkeyed support.

These are SDK-inspired GT subsets, **not official miss-rate results**. We
exclude dusk/pilot frames, preserve the frozen candidate pipeline rather than
the SDK's setup-dependent detection-height filter (40 px under Reasonable),
use cap 3000 rather than SDK 1000, and primarily absorb rider/category-4
regions that the pinned SDK's category-1 scoring leaves unused. No claim of
official benchmark replication follows.

## Frozen predictions, matching and operating points

Use each PR13 final EMA `last.pt`, hash-pinned in the existing
[compute ledger](2026-11-15_bdd_clearday_transfer/compute_ledger.json): A at
**imgsz 640**, B at **1280**, C at **640**. NightOwls is 1024×640: A/C
downsample and B upsamples under native Ultralytics letterboxing. Keep
`ultralytics==8.4.197`, FP32 (`half=False`), confidence floor **1e-4**,
class-aware NMS IoU **0.70**, `max_det=3000` across all classes, then retain
class 0 (pedestrian). No retraining, augmentations, pedestrian-only pre-cap
filter, candidate-size filter or target-based cap/floor tuning. Safe list
chunks are 16 at 640 and 4 at 1280 (list length is the effective predict
batch); record actual batch/letterbox shapes and any inference failure/cap hits.

Cache the existing private NPZ format (`names`, `offsets`,
`all_class_candidates`, native-coordinate `boxes` xyxy float32, `scores`) and
summary with checkpoint/prediction hashes, timing, complete coverage and cap
hits. Keep NPZ and all IDs/boxes/images under gitignored `data/` or `outputs/`.

Convert labels with `convert_nightowls(..., profile=PRIMARY_PROFILE,
setup='reasonable', matching_category='pedestrian', exclude_image_ids=pilot_ids)`.
Use **unchanged `ReferenceEvaluator`**, `categories=['pedestrian']`,
`ignore_policy='same_category_ioa'`, `bounds_policy='allow_outside'` for native
GT. Sort score descending, then candidate ID; match highest-IoU unmatched
eligible GT at **IoU ≥.50**, GT-ID ties deterministic. Only then absorb an
unmatched candidate at intersection/**prediction** area ≥.50 against a
same-category ignore region (reusable); other duplicates are FPs. Native
zero-area predictions remain explicit FPs at their scores, using BDD
`match_chunk`'s side-channel convention; reversed/nonfinite geometry fails.
All evaluated images, including those with no candidates or eligible GT,
remain in coverage and FPPI. Do not pass zero-area boxes to the schema validator.

Transfer the exact stored BDD **all-height** source-selection t* for targets
.80/.90/.95, with inclusive score ≥t* and whole ties. Only **B at .80** has
a feasible original threshold: **0.014860522001981735** from
[`B_1280.json`](2026-11-15_bdd_clearday_transfer/B_1280.json).
A/C at all three targets, and B at .90/.95, are `INFEASIBLE_SOURCE_TARGET`:
transfer/oracle-gap-at-source-t* are undefined, never replaced by the ceiling.
Report ceilings and NightOwls oracle feasibility for **all** runs regardless.

Keep PR13 amendment-2 low-target .60/.70 policies (`*_low.json`) and h≥32
source policies (`*_h32.json`) as **separately labelled exploratory, post hoc
BDD policies**, although their NightOwls evaluation is now preregistered.
Transfer their exact stored thresholds where feasible, without selecting a
NightOwls replacement. The target remains Reasonable h≥50 for those panels.
No matched-FPPI threshold search or additional model arm is commissioned here.

For each setup/policy/run report recall, FPPI, precision, ceiling, source
feasibility and the **NightOwls oracle**: highest observed target score with
recall ≥ each target, whole ties; `INFEASIBLE` below ceiling, `UNDEFINED`
without eligible GT. Oracle use is diagnostic on these same target labels,
not target calibration or an unbiased deployment estimate.

Decompose total eligible-GT misses at an available source t*: (1) no matched
candidate in the greedy full prefix at IoU≥.50 and score≥1e-4; (2) matched
candidate removed by score<t*. Counts sum to GT−TP(t*); divide by GT for
recall units. This is not literally “no geometric overlap”: competition,
NMS, class assignment, floor/cap and localization all affect the ceiling.
Use the existing target-gap and clear-reference loss identities. A contrast
with BDD clear-day involves different dataset/GT populations, not a causal
night effect or aligned-denominator domain effect.

Freeze the existing `sensitivity.py` diagnostic definitions: greedy floor
1e-3, any-candidate IoU≥.50 and any-candidate IoU≥.30 at floor1e-4. Keep
operating recall/matching at primary IoU≥.50 unchanged. For loss splitting,
use residual threshold part = operating loss − ceiling difference; with
any-candidate ceilings this is a definition sensitivity, not matched-GT miss
attribution. Floor1e-3 decomposition is only defined at source t*≥1e-3;
otherwise mark not applicable. No assertion of positivity or dominance is
made before results; retain null, negative and failed outcomes.

## Uncertainty and grouping

Use **1,000 replicates**, seed **20261117**, paired target draws across runs,
policies and height panels. Compute image-level TP/FP/GT totals, then sum
weighted counts (object-weighted recall, image-weighted FPPI). Known recording
IDs exist: sample **five recording keys with replacement**, retaining every
image of each drawn recording with its draw multiplicity. Do not draw frames
independently within a known recording in the primary bootstrap.

Null keys stay null; filenames, timestamps and tracks do not repair them.
Pooled point estimates retain their 1,304 frames. In pooled bootstrap intervals
hold their image weights at one: label intervals **conditional on the unkeyed
frames**, since their sequence uncertainty is not identified. Also report a
known-key-only cluster interval and an **IID-image bootstrap sensitivity** of
the full cohort, explicitly potentially anti-conservative under video
correlation. Do not call the null bucket a sixth sequence. With just five
keys, cluster intervals are descriptive and may be unstable; keys do not
establish independent trips. No G0 inference follows.

Independently resample the 1,842 BDD source-selection images and reselect the
same source-policy t* in each joint replicate, as in `evaluate_transfer.py`.
Apply that replicate's t* to its target draw; retain and count infeasible
replicates, report interval support and do not substitute ceilings. Observed
source infeasibility remains undefined even if some bootstrap draws are
feasible. For clear-reference contrasts also resample BDD clear-test images
independently with shared weights across paired runs. Target-only intervals
at the exact frozen observed t* may be reported as a labelled conditional
sensitivity. Oracle bootstrap reselects on the resampled target and reports
infeasible/zero-GT frequency. Percentile 2.5/97.5 intervals use only defined
replicates and disclose their number. Preserve source bootstrap assumptions
and original BDD-policy exploratory status.

## Download and execution handoff

**No datasets may be uploaded from this PC to Colab.** The sole recommended
route is direct download inside the coordinator-authorized Colab session from
`https://thor.robots.ox.ac.uk/nightowls/python/nightowls_validation.zip` and
require **57,481,286,834 bytes**, SHA-256
`6663dc5099714ffb8c18bb37942ce523de9dfdda44327284bdab12354e8fcf9d`, before use.
A Windows `curl.exe --head --range 0-0 --max-time 45` check on
2026-11-18T07:36:48Z received unauthenticated **206**, Content-Range
`bytes 0-0/57481286834`, ETag `"5ce813b8-d6226d4b2"`, Last-Modified
`Fri, 24 May 2019 15:54:32 GMT`; HEAD read **zero response-body bytes**.
This verifies endpoint metadata/access from this PC, not sustained Colab
throughput. If direct download inside Colab fails or requires unavailable
credentials, stop and report that limitation; there is no PC-upload fallback.
Verify free disk against archive plus 57.60 GB uncompressed images and outputs;
avoid retaining duplicate extracted datasets. Local archive remains unextracted.

Inference covers **51,782 images per run, 155,346 total**. Prior L4 BDD timings
over 11,842 images were 133/208/125 seconds for A/B/C: linear extrapolation
is about **10/15/9 minutes**. Budget planning uses **10/15/10 minutes**,
approximately 35 minutes inference total, excluding download, CRC, extraction
and evaluation. This is an estimate, not a NightOwls timing. Claude separately
reported current L4 1280 throughput about 57 images/s, compatible with ~15
minutes for B, and estimated 1.5–2 CU including overhead; resource/budget
approval and retrieval/teardown remain the coordinator/executor's responsibility.
Do not allocate another session or use the local GPU.

## Implementation evidence and actual peer exchange

GPT Sol extends the existing adapter, preserving its default interface,
matcher and legacy policy. Synthetic fixtures test exact 20/50/75 boundaries,
occlusion, categories, exclusions, empty frames, native geometry, grouping and
eligible-first/reusable ignore matching. A preparation CLI checks label and
pilot hashes and exact archive/native image coverage; it writes only private
canonical data. These are implementation checks, not detector results or a
new independent review. The coordinator commissions review separately.

Actual exchange, 2026-11-18 UTC: GPT Sol sent `PEER PROPOSAL` with cohort,
GT policy, cluster/unkeyed handling, sizes and unchanged source thresholds.
Claude Opus replied `PEER FINDING`: no NightOwls predictions; no objection to
cohort, Reasonable GT or clustering; preserve source infeasibility and
historical exploratory labels; retain native policy/zero-area convention;
add definition sensitivities and source-selection resampling. These are
incorporated above. Claude offered rider outputs if needed; none are needed.
Claude suggested optional B2; it is deferred outside this A/B/C assignment.
The user/coordinator then prohibited PC-to-Colab dataset uploads; the direct
download-only handoff above records that constraint. No assent is inferred
for other choices, no review task was launched, and no agreement on results
or authorization for inference/merge is implied.
