# NightOwls contract amendment, version 2 — 2026-11-18 UTC

I want the external comparison to use a height-aligned BDD reference and to
show the remaining annotation and scale limitations. GPT Sol prepared this
amendment in response to the independent [Claude Opus review](../reviews/2026-11-18_opus_review_nightowls_contract.md)
of `8a89a635`. This **supersedes conflicting analysis and execution provisions
of version 1**; all other cohort, checkpoint, matching, candidate, oracle,
bootstrap and privacy rules in the [original contract](2026-11-17_nightowls_external_contract.md)
remain fixed. The review is preserved unedited, not rewritten as approval of
these fixes. The coordinator retains review/publication and inference control;
my explicit GitHub approval governs merges. **G0 remains pending.**

Timing: the coordinator reports that raw NightOwls predictions are now being
generated, but **no NightOwls metric has been computed or inspected**. Freeze
this amendment by its own commit before any NightOwls scoring. This is a
**pre-scoring amendment, not a pre-prediction preregistration**. GPT Sol has
not accessed NightOwls predictions. BDD results already exist and motivated
the review, so the new policy is **post hoc/exploratory on BDD**, even though
fixed before NightOwls metrics. No source threshold or target choice may be
changed after NightOwls scoring. Failed/infeasible results remain results.

## H1: height-aligned population and threshold reselection

The **primary source policy reselects t*** on existing BDD clear-day
selection predictions using eligible pedestrian GT with native height
**≥50 px**, with shorter pedestrian boxes as reusable same-category ignore
regions. Apply the existing evaluator's **`--min-height 50`**, unchanged
IoU≥.50/score-prefix matching and highest-observed-score boundary/whole ties.
Do not train, recalibrate, alter predictions, split or inspect NightOwls.
Use exactly the same BDD ≥50 rule for selection, clear-day test and night
test. Primary threshold-transfer target is **.80**, with **.90 and .95**
reported as fixed sensitivity targets; infeasibility remains explicit. This
chooses a common measurable operating aspiration from the original target
grid, not a target discovered on NightOwls. Reselection is preferable to
calling an all-height source threshold an equal-recall ≥50 threshold. It
may make A/C feasible; feasibility is measured on BDD, never assumed or
forced with a fallback. All arms use their own ≥50 source t* unchanged on
NightOwls Reasonable, and bootstrap source draws reselect on this same
height-restricted population.

Recompute BDD selection, **clear-day and night** recall, ceiling, miss
decomposition, FPPI and precision with the existing private predictions and
GT (`outputs/bdd_transfer_20261115/{preds,private}`). These are CPU source/
reference calculations, not NightOwls metrics. The **BDD ≥50 clear-day**
reference at the matching run/policy t* enters every primary clear-reference
loss identity; BDD ≥50 night is the within-dataset night comparator. Do not
subtract all-height BDD recall from Reasonable recall and label it the primary
domain-transfer loss.

Secondary: preserve original all-pedestrian source-selection t* and its
original source-infeasible statuses. Evaluate each available original t*
on the **same ≥50 BDD selection, clear-day and night populations** and
NightOwls Reasonable. This gives the no-shift expectation at the original
threshold; target .80 is not claimed attained at exactly .80 on the ≥50
population. Report original all-height BDD results only as a historical,
population-confounded secondary; never use them as the primary clear
reference. Historical low-target/h32 policies retain their exploratory status.

**Occlusion remains unaligned:** the prepared BDD evaluation GT has no
occlusion flag; its box-only evaluator cannot enforce NightOwls' not-occluded
Reasonable rule. No occlusion metadata is inferred or silently recovered.
Native-height alignment reduces one population mismatch, not all of them.
Dataset label completeness, box extent, visibility and image composition
still preclude a causal night-effect or fully matched-population claim.

## M1: primary FPPI comparison and ignore sensitivity

For **all primary BDD-versus-NightOwls comparisons**, including FPPI and
precision, use NightOwls **`unused_nonpedestrian`** with Reasonable GT:
2,520 ineligible-pedestrian absorbing regions, while rider categories 2/3
and native ignore category 4 are unused. This aligns the class scope more
closely with BDD pedestrian-only outputs; BDD ≥50 also absorbs short
pedestrians but counts pedestrian outputs on riders as FPs. Use the ≥50
BDD comparator at the corresponding source t*. This explicitly changes
version 1's primary profile for the cross-dataset question.

Report **`person_compatible_ignore` as the fixed sensitivity** on the exact
same images/candidates: 9,421 absorbing regions = 2,520 ineligible pedestrians
+ 585 rider boxes + 6,316 category-4 boxes. Keep it labelled in every table,
including within-NightOwls summaries; do not mix its FPPI with BDD FPPI and
claim comparable FP burden. Even `unused_nonpedestrian` FPPI/precision are
annotation-policy-dependent: NightOwls also ignores occluded pedestrians
and some height-excluded GT, while the available BDD evaluator ignores
only short pedestrians. Thus neither profile yields fully equivalent FPPI.
Report ignored-candidate totals by profile, counts of eligible/ignored GT
and all-image denominators; do not interpret fewer FPs after absorption
as a detector improvement. Riders are never eligible GT in either profile.

## M2: model-input height strata and residual scale confounding

In addition to all native-height strata, report GT recall/ceiling/miss counts
in **model-input pixel** bins [0,16), [16,32), [32,64), [64,128), ≥128.
Use unclipped native GT height × actual isotropic letterbox resize ratio,
not padded image height, and reuse each population's full matching
assignments. Do not rerun matching separately per display bin or change GT
eligibility: ≥50 remains a native-pixel rule. Report the ≥50 population's
minimum input height and zero-support bins as undefined. Record actual
preprocessing shapes/ratios; nominal ratios are:

| Runs / inference size | BDD 1280×720 ratio | NightOwls 1024×640 ratio | ≥50 input-height boundary, BDD / NightOwls |
|---|---|---|---|
| A/C, imgsz 640 | .5 | .625 | 25 / 31.25 px |
| B, imgsz 1280 | 1.0 | 1.25 | 50 / 62.5 px |

NightOwls GT is **1.25× taller in model-input pixels at equal native height**.
Fixed inference size per run preserves the deployed pipeline but confounds
native-height/dataset contrasts with object scale. Input-height stratification
makes this visible; it does not align support, occlusion or composition and
does not establish the sign of the total transfer effect. No new scale-matched
inference (512 for A/C, 1024 for B), checkpoint or GPU work is authorized here.

## M3: recording dominance, sensitivity and minimum support

Publish per-recording **aggregate** results under R1–R5, assigned once by
ascending native recording-key order (same ordering as the historical
anonymous inventory), plus a separate `unkeyed` row. Keep the key/ID mapping
private. Include image/eligible/ignored GT counts, distinct eligible native
tracking-value count, transferred recall/FPPI/precision, oracle feasibility,
ceiling and miss decomposition, under each reported source policy/profile.
Tracking values are not verified unique people; publish only counts.

The dominant recording is fixed **from eligible GT counts, without model
scores**: 4,994 of 7,631 Reasonable GT (65.4%; 73.8% of known-key GT). Report
a **leave-dominant-recording-out pooled result**, retaining all other images,
including unkeyed frames, with original source t* unchanged. Report remaining
image/GT/group support. Do not select an exclusion based on transfer scores.
This is a sensitivity, not an alternative primary population or independent
replication. In its bootstrap, draw the remaining four known keys with
replacement and keep unkeyed weights fixed; pair draws across models.

Restore the [2026-11-13 support policy](../decisions/2026-11-13_nightowls_external_policy.md):
**five known recording keys**, each with **≥10 jointly ceiling-covered
eligible GT** for any claimed sequence-majority comparison; fewer supported
keys makes that sequence claim **INCONCLUSIVE**. Joint coverage means the
intersection of eligible-GT IDs greedily matched at the full frozen candidate
prefix by every run included in that contrast (A/B/C for the joint panel,
explicit named pair for a pairwise panel). Do not count ignored GT or the
unkeyed bucket, change the panel after support inspection, or imply such a
sequence claim was tested merely by presenting recall. Also report the
**150 eligible-box operational floor per recording and pooled**, and
distinct eligible tracking-value counts alongside it; this is a support
flag, not a precision guarantee. Do not lower the floor: one known key has
149 eligible boxes after exclusions. Unsupported rows remain visible.

Known-key GT counts are 1,005 / 291 / 4,994 / 332 / 149 in the fixed anonymous
ordering; unkeyed GT is 860. The primary cluster bootstrap remains descriptive:
only **126 distinct multisets** exist for five draws of five keys, and the
chance of omitting the dominant key is **(.8)^5 = .32768**. Disclose lumpy/
multimodal intervals and fixed-unkeyed conditioning. Per-recording and
leave-dominant-out results supplement, not replace, the fixed pooled result.

## L1: explicit correction history

Version 1 froze at `d59e218`; `8a89a63` then corrected the disk figure from
57.47 GB to **57.60 GB**, consistent with 57,595,824,667 uncompressed bytes.
It also clarified an adapter docstring, tightened the private output-path
guard and caught `zlib.error` during ZIP verification. These changes occurred
**before predictions**, did not alter matching/analysis choices, and should
have had an explicit correction note. This paragraph supplies that note;
the historical commits and review remain unchanged. The current v2 is a
substantive amendment **during raw prediction generation, before scoring**,
not another numerical correction claimed to predate predictions.

## L2: ZIP-only Colab handling and download cost

The executor reads/decompresses images directly from the verified ZIP;
**do not extract the archive**. Allow archive size 57.48 GB plus model,
output and working-memory/disk buffers; the previous 115 GB extraction
footprint is not required. Preserve exact hash/CRC/coverage requirements.
All dataset acquisition remains a **direct Colab source download**, never a
PC upload; credentials/download failure is a stop/report condition.

For a future or still-running download, impose a **60-minute cumulative
download wall-time cap including retries/resumes**, plus **120 seconds
without byte progress** as a stall stop. Require projected completion within
the remaining cap using the trailing five-minute throughput once five
minutes have elapsed. On breach stop the download, preserve received-byte/
elapsed/error evidence and tell the coordinator; no new session, fallback
upload or unbounded retry follows. A coordinator-authorized resume retains
the same cumulative time/byte accounting and archive identity. These are
v2 limits, **not a claim that an already completed transfer used them**;
record the actual original limit and elapsed time separately if available.

Allocated GPU time during download is **billable CU time** even when GPU
utilization is zero. Include download, verification/decode, inference,
evaluation, idle/retrieval and teardown in the executor's cumulative session
ledger, with actual rate × allocated hours and displayed balance changes
(billing-lag caveat). At historical L4 **1.94 CU/h**, 60 minutes download
+ 35 minutes inference alone is **3.07 CU**, before other stages; at the
existing 3 CU/h rate ceiling it is **4.75 CU**. These are planning estimates,
not measured charges or an additional budget grant. The previous 1.5–2 CU
estimate did not bound a long download and is superseded for planning.
Stay within the coordinator's remaining authorized total; a longer transfer
or changed rate requires coordinator decision, not an executor extension.
No local GPU or Colab action is performed by GPT Sol.

## Disposition and stopping condition

H1, M1–M3 and L1–L2 have the explicit rules above. GPT Sol will record CPU
BDD ≥50 results separately, preserving actual inputs/hashes and source
infeasibility; no NightOwls metric is required to implement this amendment.
Commit/push the amendment and relevant checks, then hand back for the
coordinator's review/PR. No new independent reviewer was launched from this
implementation task, and no review assent or inference/merge approval is
inferred from silence.
