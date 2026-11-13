# NightOwls external-panel policy decision

I want the next frozen-checkpoint comparison to use a declared annotation task and preserve empty frames. GPT Sol makes these coordinator decisions after [Opus's independent annotation review](../reviews/2026-11-13_nightowls_annotation_review.md). This fixes the policy for implementation; it does not authorize images, freeze an acquisition cohort, approve a merge or pass G0. The original BDD-primary gate remains separate.

## Population and grouping

Include frames whose native `daytime` is exactly `night`; exclude the two dusk frames. Any later acquisition subset must be fixed before fetching images or evaluating predictions, preserve selected empty frames and pass its support check without searching replacement seeds or strata.

Keep null-recording frames in pooled recall and the image denominator for FPPI, and report an unkeyed stratum. They do not form a sixth sequence or vote in H1. The sequence unit is a non-null native recording key, with no claim that keys identify independent trips. Never infer missing keys from filenames or tracking IDs.

The five-recording floor stands. There are exactly five known keys, so the sequence-majority screen has no slack. Each must reach the prespecified ten jointly ceiling-covered eligible GT to count as supported; otherwise sequence H1 is INCONCLUSIVE. Pooled and recording-wise counts are still reported. Keep the proposed 150-box floor as an operational support rule, not a precision guarantee, and report distinct tracking-ID counts alongside it. Tracking IDs need not identify unique people, and repeated frames are dependent.

## Primary target and fixed sensitivity

- Eligible GT: native pedestrian category 1, native ignore flag zero, **unclipped bbox height at least 50 pixels**, and `occluded` not true. Adopt the pinned Python SDK's treatment of null occlusion as visible for this benchmark convention; this does not establish actual visibility. Difficulty and truncation are not extra exclusion rules.
- Every remaining category-1 box becomes ignored GT. Preserve native xywh coordinates, including out-of-frame extents. Do not clip, infer truncation or repair pose references.
- Primary treatment: rider categories 2/3 and native ignore category 4 become non-penalized ignore regions in the merged prediction category. This prevents out-of-scope human predictions from automatically becoming pedestrian FPs; it does not establish rider-only box extents.
- Fixed secondary: omit categories 2/3/4 as matchable or absorbing regions. It isolates the FP effect of the Python SDK's category scope under the same candidate pool and matcher. Eligible pedestrian GT and ineligible-pedestrian ignore boxes are unchanged.
- Use the existing score-ordered eligible-first matcher at IoU ≥.50, then unlimited ignored-region absorption at intersection/prediction area ≥.50. Keep the existing native zero-area FP convention and allow-outside geometry. No matching change is commissioned.
- Keep all candidate sizes in both policies. The SDK's additional 40-pixel detection filter is **not** adopted: preserving the frozen candidate pipeline is the purpose here. These are SDK-inspired GT eligibility and a category-scope sensitivity, not reproduction of official miss-rate scoring or official FPPI.

The observed full-night GT count under the height/occlusion rule is 7,649, including 872 unkeyed annotations. Full-night eligibility is not the eventual acquisition-subset count. The five known keys have 53/39/143/13/11 distinct eligible tracking values, so boxes substantially overstate distinct-track support in some keys.

## Frozen model information and limits

Use the existing checkpoint, common-N pipelines, historical source maps and original thresholds from the [corrected direction proposal](../claude/2026-11-13_opus_direction.md). The source recalls remain unequal (.89637/.90155); no new equal-source claim or target reselection follows. This pedestrian-only target is distinct from ACDC merged-human and COCO-person tasks. Primary/secondary FP costs are annotation-policy dependent, and neither proves a whole-frontier improvement.

Visible versus amodal extent, completeness below 50 pixels, publisher intent for null occlusion, pretraining exposure and recording independence remain limitations. The adopted target is the publisher-provided native bbox convention, not a newly inferred body-extent label. A minimal adapter must implement exactly these choices and receive its own separate review before any external inference. No parser framework, new evaluator, broad test programme, GPU qualification or dataset-image retrieval is authorized by this decision.
