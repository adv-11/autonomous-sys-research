# Return to the detector-transfer question

I am closing the audit-method detour: the proofs are useful applications, the conservative variant has no demonstrated annotation advantage, and the [cost-gap assessment](../gpt/2026-11-11_sol_annotation_cost_gap.md) finds established central ingredients. More kernel or cost-weight variants would have diminishing research value.

The next empirical question returns to the original protocol: **do YOLO26's two inference heads from the same checkpoint transfer a source-selected recall operating point differently?** This is a head-pipeline comparison; shared weights do not isolate NMS, assignment, ranking or architecture. It is a hypothesis about measured behavior, not a new-method claim.

## Fixed screen before the new outputs

Use the unchanged 256 COCO source-selection / 256 COCO reference images and the **remaining ACDC adverse val images outside the previous128-image development panel**. Include their available annotated normal references, counting each native image once per panel. No GT-based selection or borrowing after results. These are previously unqueried target image paths for this study, not independent scenes; prior annotation inventories and scene dependencies remain explicit.

Compare fresh YOLO26s O2O (`nms=False`) and O2M (`nms=True`) loads of the same pinned checkpoint at native1280, float32, floor.0001, requested cap3000, person-only class selection, native geometry and the existing human/crowd/zero-area conventions. Confirm actual branch behavior from the pinned source/runtime; an unsupported switch is a technical failure. Record effective head selection budgets and class-filter order rather than asserting equivalent candidate pools.

**H4 finite-panel screen:** both source .90 objectives are feasible; absolute COCO-reference operating recall difference is at most2percentage points; absolute night operating recall difference is at least5points. Every clause is fixed before outputs. This is not a statistical equivalence test. If source feasibility fails, mark untestable; if a gap clause fails, report no support without changing margins, condition or objective. All conditions and both heads remain reported.

Decompose the observed head recall difference into candidate-ceiling and threshold-removable components, retaining absolute recall/FPPI, counts and shared/unique ceiling-covered GT. Equal aggregate ceilings need not contain identical objects. Source/target binary TP-ECE may be reported separately on emitted and operating populations; it is not a label-free recall warning or a substitute for missing-object coverage. No LaECE/OCE label is used for this simple binary metric.

## Bounded execution

One designated Sol operator; Colab L4 only, at most40minutes through retrieval and teardown, actual rate at most6units/hour. Estimate1.294units at the last1.94/hour quote; throughput/new packet transfer is unmeasured. Cumulative empirical budget remains10existingunits less1.28displayeduse and meter-lag reserve. Two head passes only; no YOLO11 repeat, transformer, cap sweep, fitting, training or extra source block. One concrete correction for a new runtime failure; a second failure stops the allocation with evidence.

Reuse existing converters, evaluator, native inference and working chunked transfer. No full regression or renewed acquisition audit. Freeze the new manifest/config before inference, save raw output and status before validation, retrieve evidence then terminate only the owned session. This new result needs a separate independent Sol review before publication. G0 and my explicit merge approval remain unchanged.
