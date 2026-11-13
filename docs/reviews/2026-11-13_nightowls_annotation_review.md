# Independent Claude Opus review of the NightOwls annotation inventory

**Disposition: REQUEST CHANGES (small, coordinator-resolvable).** Every count the inventory publishes reproduces exactly from the private JSON. One public statement is materially wrong: the "sixth recording" is a **null `recordings_id`**, so only five non-null recording keys exist. The scoped Opus proposal also says people under 50 px are unannotated, and the actual JSON contradicts that. Neither finding needs new data, compute or a new implementation. This is a Claude Opus 5.5 AI review. It is not my human merge approval and makes no novelty, generalization or G0 claim. G0 (scoped and original BDD-primary) remains **PENDING**, and the review authorizes no new resources.

**Coordinator disposition, 2026-11-13:** GPT Sol corrected the producer, counts-only inventory, note and figure to five known keys plus 1,318 null-key frames. Null frames remain pooled and never vote as one sequence; dusk frames are excluded from the proposed night panel and the five-key floor stands without slack. The below-50 absence claim is withdrawn; pose-reference scope and tracking-value concentration are reported. Corrected counts were checked against this review's independent JSON. The [policy decision](../decisions/2026-11-13_nightowls_external_policy.md) declares native unclipped pedestrian eligibility, explicit null-occlusion handling, person-compatible ignore/rider absorption as primary and unused categories as a fixed secondary. It preserves all candidate sizes, so it explicitly does not claim official SDK score reproduction. No existing result or raw annotation was changed. A minimal adapter is a separate implementation assignment and needs its own independent review. The original findings above remain preserved; this is the coordinator's disposition, not a new reviewer statement or G0 passage.

## Scope and provenance

- **Reviewed:** GPT Sol coordinator commits `3b36c43f023e41fb920bf3484155ef18c43fe8e4` (acquisition record, inventory JSON, notes, figure, `scripts/data/nightowls_annotation_inventory.py`) and `b00d12e8da9b8804379642d94c831d13101d8994` (gate-log and route note update), on branch `nightowls-annotation-preflight`. Context was read from AGENTS, CONTRIBUTING and `docs/claude/2026-11-13_opus_direction.md` (the current scoped claim). Earlier Opus work counts as historical context only, not new verification.
- **Private input:** `C:/Users/Advait/autonomous-sys-research/data/nightowls/annotations/nightowls_validation.json`, 10,696,948 bytes, SHA-256 `584c0dc11f0d086fc5bcbaca0385cf2dd9794074f815f2727fbf9a093fd9a9b6`. It matches the acquisition record, and `git check-ignore` confirms it is ignored by `data/**`. No new annotation download took place.
- **Official SDK (read-only source, about 42 KB of text):** `ox-vgg/nightowlsapi` pinned at `ad0f18fc95e093e86036f055ab210a3de46021b7`, retrieved with `gh api` (tree) and `raw.githubusercontent.com/ox-vgg/nightowlsapi/ad0f18f…/{README.md, python/eval.py, python/eval_MR_multisetup.py, python/coco.py}` on 2026-11-13. Local SHA-256 of the copies: README `cf84277e…`, eval.py `63ffc2ea…`, eval_MR_multisetup.py `8a7b8411…`, coco.py `6958010a…`. The 49.6 MB sample-detections file and the MATLAB Caltech tools were **not** retrieved, and neither was the ACCV 2018 paper. Everything below about SDK behaviour comes from reading its *implementation*. It is not a publisher statement of annotation protocol.
- **Not done:** no images, image archive or index, GPU, Colab, installation, child tasks, paid compute, push, PR or merge, and no pHash or whole-dataset re-audit. The CPU Python was `C:/Users/Advait/ar-work/venv-rtdetrv2/Scripts/python.exe -I -B`.

## Independent recomputation

The [checker](2026-11-13_nightowls_annotation_check.py) is independent of Sol's script; it does not import it. It writes aggregates only to [check JSON](2026-11-13_nightowls_annotation_check.json), with no file names, IDs, timestamps, tracks or boxes. Comparing it against the committed inventory gives `inventory_mismatches: []`.

| Quantity | Sol inventory | Opus recompute |
|---|---:|---:|
| images / annotations | 51,848 / 17,091 | same |
| night / dusk; all 1024×640 | 51,846 / 2 | same |
| frames with no annotation at all | 42,359 | same |
| night native nonignored pedestrians | 10,178 | same (the 10,179th is on a dusk frame) |
| night frames without one | 45,611 | same (6,235 frames have ≥1) |
| out-of-image boxes; area = w×h | 2,231; 0 mismatches | same; ints, all finite and positive |
| per-slot pedestrians | 1,577/348/6,072/560/280/1,341 | same, and frames/empty frames per slot also match |
| ID uniqueness; image/category refs | pass | pass |

**What the JSON itself establishes (newly reported here):**

- `ignore == 1` **if and only if** `category_id == 4` (6,325 boxes). In this file the flag and the category coincide exactly, so they cannot disagree.
- `difficult` is null **only** on ignore-category boxes (5,238). `occluded` is null on 5,249 ignore, **114 nonignored pedestrian** (all night) and 7 bicycledriver boxes. `truncated` is False for every pedestrian, including the **158 nonignored pedestrian boxes that extend outside the frame**. Truncated=True occurs only on ignore boxes (1,087). The 2,231 out-of-image boxes split into ignore 2,058, pedestrian 158, bicycledriver 11 and motorbikedriver 4.
- Nonignored night pedestrian height (`bbox[3]`) ranges from 15 px; **1,358 are < 50 px**. Ignore boxes go down to 6 px.
- `recordings_id` is a float on 50,530 frames and **`null` on 1,318 frames**. That null group is inventory slot 6, holding 1,341 pedestrians. All float keys are integer-valued.
- Distinct `tracking_id` counts per slot, for night nonignored pedestrians: 134/49/172/16/15/46. Slots 4 and 5 have 560 and 280 boxes but only 16 and 15 tracks.
- `poses` has IDs 0–4 (front/left/back/right/"nan"), but 5,356 annotations use `pose_id` 5, which does not resolve (ignore 5,237, pedestrian 117, bicycledriver 2). This is most likely an off-by-one, but that is not established. Pose plays no role in the proposed claim.

## Official SDK implementation semantics (`eval_MR_multisetup.py` @ `ad0f18f`)

1. **Category scope:** `useCats=1`, and `accumulate` hard-codes `catIds=[1]`. Official MR uses only category-1 GT and category-1 detections. Ignore-category regions (category 4) and riders sit in other category buckets, so they **neither absorb nor match pedestrian detections**. A pedestrian detection on an ignore region or a rider counts as a false positive. A native category-4 ignore region is therefore *not* an evaluation ignore region in this Python implementation. The bundled Caltech MATLAB tools were not inspected, and they may differ.
2. **Ignore GT inside category 1:** `ignore` comes from the native flag (always 0 for pedestrians here). It is then set to 1 when `height=bbox[3]` falls outside `HtRng` or `vis_ratio` falls outside `VisRng`. Ignored GT are matched with crowd IoU, which is intersection over detection area.
3. **Visibility:** `vis_ratio = 0.5 if occluded else 1.0`. A **null `occluded` therefore counts as fully visible**. `difficult` and `truncated` are never read.
4. **Setups:** Reasonable = height ≥ 50 and vis ≥ 0.65, so occluded pedestrians become ignore. All = height ≥ 20 and vis ≥ 0.2. IoU is 0.5. Detections shorter than `50/1.25` px are dropped under Reasonable.
5. **FPPI denominator:** `I0 = len(imgIds)`, which is every image in the GT JSON, empty frames and both dusk frames included. Retaining empty frames is consistent with this.
6. **Implied counts on night frames** (descriptive, not an adopted policy): Reasonable-eligible pedestrians = **7,649** (per slot 1,006/291/4,999/332/149/872). All-eligible = 10,169.

**Still unknown without RGB or the paper:** whether pedestrian boxes are visible-extent or amodal (the 158 out-of-frame boxes suggest full-extent boxes, yet `truncated` never marks them); whether rider boxes include the vehicle; whether people under 50 px are labelled completely; what `occluded=null` means to the publisher (the SDK treats it as visible); and whether recording keys or the null group correspond to independent trips or scenes. Timestamp units and cadence are **not** adopted. Gaps within each key are non-uniform, so the null-key group may well span several segments.

## Findings

**P1 — The null recording key is presented as a sixth recording.** Notes line 9 ("six native `recordings_id` values"), the inventory (`recording_count: 6`, slot 6), the figure and the gate-log entry all count it as one. In fact 1,318 frames have `recordings_id = null`. This bears directly on the proposed unit ("recording sequence") and on the floor of "five recordings / five supported sequences". Only five keyed recordings exist, so the floor is met with zero slack, and that holds only if every keyed recording is supported. The null group cannot be assumed to be one sequence. *Fix:* report "five non-null keys plus 1,318 null-key frames"; label slot 6 as the null key in the inventory and figure caption; add `null_key_frames` to the script output. Before freezing, decide how the null group is handled. My recommendation: keep its frames in the pooled all-frame cohort and the FPPI denominator, but exclude it as a unit from the sequence-level H1 majority (report it as an unkeyed stratum). State explicitly that five keyed recordings is the exact maximum, so H1 has no spare sequence.

**P2 — "People under 50 px are unannotated" is contradicted by the data.** Line 52 of `docs/claude/2026-11-13_opus_direction.md` makes that claim, but there are 1,358 nonignored night pedestrians under 50 px (minimum 15) and ignore boxes down to 6 px. The supportable statement is narrower: below 50 px, completeness is not established, and the SDK's Reasonable setup treats those boxes as ignore. *Fix:* replace the clause with "*f* is secondary because annotation completeness below the frozen height floor is not established and native ignore/rider handling changes the FP set."

**P2 — The ignore-region and rider policy is an open decision that the SDK does not settle the way a COCO-person evaluator would.** The SDK leaves category-4 regions and riders unused, so they count as FPs. A COCO person detector will fire on riders and on people inside ignore regions. Under the scoped claim, this mainly moves FP and *f*, and greedy competition for entry scores. H1/H2 TP admissions are affected only through that competition. *Fix (recommendation, not frozen):* before any image proposal, define eligible GT as category 1, `ignore=0`, `bbox[3] ≥ 50` on the native unclipped box, and `occluded` not True (with null counted as visible, as the SDK does, and its count of 114 recorded). Remaining category-1 boxes become non-penalized ignore GT matched by IoA. For category 4 and both rider categories, pre-declare one primary treatment: either non-penalized IoA ignore regions (aligned with COCO person) or SDK-faithful (unused). Report the other as a fixed secondary. Keep native boxes unclipped. Report the effect of clipping only if the existing evaluator requires clipping. Record that this pedestrian-only estimand still differs from the ACDC merged-human and COCO-person tasks.

**P3 — "Annotation references resolve" is stated more broadly than it was checked.** Image and category references resolve, but 5,356 `pose_id` values fall outside the `poses` table. *Fix:* narrow the sentence to image and category references, or note the pose off-by-one. No G0 consequence.

**P3 — Track concentration.** Annotation counts overstate the effective support of people: slots 4 and 5 hold 16 and 15 tracks. *Fix:* report distinct-track counts next to the 150-eligible-GT proposal. This is not a power claim, and it gives no reason to change the minima after the fact.

**Confirmed without change:** empty frames are retained and are not yet an evaluation policy. Raw counts are not final eligible GT. No box is repaired. Recording keys are not treated as proof of independence. Night identity comes from the explicit `daytime` field (two dusk frames would need explicit exclusion or inclusion in the frozen rule).

**Privacy:** the inventory, notes, acquisition record, figure (whose SVG text includes only slot labels and axis ticks) and both review artifacts carry vocabulary, response headers and nonrecoverable counts only. Slot ordering is by string-sorted native key and reveals no key values. No frames, annotations, native recording, track or image IDs, boxes or file names are committed.

## Root next decision

The coordinator can apply the P1–P3 wording fixes directly, and those need no new review. Before any image-acquisition proposal, the coordinator or I must freeze four things: (a) the null-key handling and the sequence unit, (b) the eligibility rule and ignore/rider primary treatment above, (c) handling of the two dusk frames, and (d) whether the five-keyed-recording floor stands, knowing it has zero slack. If (b) cannot be fixed without visual inspection of extents, record that as a stated limitation or as a blocker. Do not resolve it after seeing detections. If substantive new implementation follows (a converter or evaluator change), it needs its own separate review.

Reproduce: `C:/Users/Advait/ar-work/venv-rtdetrv2/Scripts/python.exe -I -B docs/reviews/2026-11-13_nightowls_annotation_check.py PRIVATE_JSON --inventory docs/datasets/nightowls_validation_inventory.json --output docs/reviews/2026-11-13_nightowls_annotation_check.json` (about one second on CPU).
