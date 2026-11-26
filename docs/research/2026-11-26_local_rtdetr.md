# Local RT-DETRv2 matched continuation study

GPT Sol owns implementation and the sole local GPU process. Claude Opus medium
is the CPU-only scientific collaborator. My research goal is to measure whether
adding night training images changes night detection beyond matched extra day
training, including the actual false-positive cost and clear-day retention.
The local authorization is in the 2026-11-26 decision record. G0 stays pending.

## Frozen design before model outcomes

Use the existing official R18 source revision, initialization and native recipe;
the exact 10,635 source, 1,842 selection and all 10,000 validation images; ten
classes with pedestrian and rider separate. Use the existing frozen adaptation
manifest (4,000 source day plus 4,000 night), excluding night calibration,
selection and validation. Select the 8,000 day control by the first SHA256 hashes
of `rtdetr-local-day-control-v1:` followed by source image stem, storing the
selected set lexicographically. This uses no labels, losses or model scores.

Use the existing Python 3.12 / torch 2.11 cu128 environment without changes.
Windows paths, workers zero, no pinned-memory or full-data RAM cache replace
the Colab delivery settings. This is a local amendment, with no claim of
numerical equivalence to the earlier environment. Native model, loss, AdamW,
augmentation, gradient clip, AMP, EMA and `train_one_epoch` remain official.
Physical batch starts at 16; one reduction to eight is allowed after actual OOM,
then the same batch is frozen across all arms. No other memory tuning loop.

One pilot uses 128 shuffled real source batches with native loss/backpropagation,
capped at 45 minutes. Pilot weights are discarded. Measured seconds per image
including loader cost project source epoch time. A 1.25 factor applies to all
training. Choose the largest baseline in 50, 30, 20, 12 epochs fitting the
remaining 24-hour wall budget after both continuations and at least two hours
for inference, evaluation and evidence. Freeze the selected plan before baseline
fit or new held-out scores. If none fits, preserve the blocker; no shorter arm.

Both continuations train five epochs on 8,000 images, start strictly from the
same final baseline EMA, reset AdamW and EMA with seed zero, use LR 1e-5 and
warmup 200. Each sees the same attempted-update count; report actual AMP skips.
Disable heavy augmentation for the final three epochs: baseline N-3 and both
continuations two. The official EMA warmup remains 2,000; its decay is about
0.713 at 2,500 continuation updates with batch 16, about 0.918 at 5,000 with
batch eight. These are formula values, not measured detection results.

Final declared EMA only; no validation or checkpoint choice during fit. Inference
uses the existing native square640 FP32/query-class top300/no-NMS/floor1e-4
policy, retaining unrounded out-of-frame boxes. Save raw logits, query boxes and
native candidates privately. No new external-dataset inference is in scope.

The independent hidden watchdog owns only its exact child process tree, capped
by an absolute 24-hour deadline including preparation. Each completed epoch
saves optimizer, scaler, EMA, schedulers and RNG state. No desktop processes,
power settings or security settings are changed. YOLO seed repeats are deferred:
their original measured memory requirement exceeds this GPU; a modified recipe
would not be an exact repeat.

## Reporting and limits

Primary policy: each arm's own source-selected FPPI1 boundary; report actual
night and clear-day recall AND FPPI and clear retention. Keep source recall
targets .80/.90/.95 and their infeasibility. Preserve full operating curves and
absolute unmatched share `1-M_night` separately from the signed clear/night
ceiling/threshold decomposition in the existing erratum. Paired 1,000 image
bootstrap draws refit source thresholds and pair test draws across arms.
Contrasts are mixed minus day control and day control minus baseline.

One seed and image resampling do not estimate training or route variance.
The mixed arm adds 4,000 previously unseen images whereas day images are reused;
there is no unused clear-day source pool outside selection. This contrast thus
combines night content with image novelty. Increased recall with increased FPPI
or reduced day recall is reported as a tradeoff. An interval crossing zero
leaves benefit unestablished. Curves are descriptive, not test-chosen policies.
Ordinary adaptation is not a novel method, and architecture comparisons remain
confounded by recipe. Nulls, failures and resource limits remain in the record.

## Actual peer exchange

Claude Opus raised the fixed augmentation epoch 47 as a material issue for a
shortened baseline. GPT Sol confirmed the adapter already sets N-3 and two for
the five-epoch arms. Claude also noted EMA warmup, image novelty, required FPPI
and day-retention readouts, paired uncertainty and descriptive curves. GPT
accepted these, clarifying that intervals including zero mean unestablished
benefit and that a cost must be explicit, rather than imposing an outcome gate.
The actual prompts/responses remain in the active task transcripts. This is
design collaboration, not independent review of completed results; the
coordinator owns that later review. Silence is not recorded as agreement.

## Measured status

Preparation completed: 26,477 image files extracted; source 10,635 images /
204,523 objects, day control 8,000 / 152,897, mixed 8,000 / 142,622. Source,
selection, validation and mixed manifest hashes match the frozen configuration;
all training sets exclude calibration, selection and validation. The exact
private day-control manifest SHA256 is in `plan.json`.

The sole pilot completed 128 physical-batch-16 updates on 2,048 real source
images in 356.164 seconds including checkpoint saving (5.750 images/second).
Native epoch-loop time was 354.976 seconds. Of 128 attempted updates, 123
succeeded and five were skipped during AMP startup; no further skips after
those first five. Peak PyTorch allocated memory was 5.665 GiB, reserved 6.459
GiB. This excludes desktop and other non-PyTorch GPU allocations. No OOM,
batch fallback, dependency change, driver reset or unrelated process closure
occurred. Mean native training loss 18.551 is not detection performance.
The pilot exited zero; a fresh process query found desktop applications and
no Python training process before the scientific run.

The throughput-only rule selected **20 baseline epochs**, with augmentation
cutoff 17. Both continuations are five epochs with cutoff two, 2,500 attempted
updates each, same final baseline EMA and fresh matched optimizer/EMA. Batch
16 is frozen across all three arms. Pilot weights are discarded for baseline
initialization. The exact plan is committed before baseline fit or held-outs.

At freeze, 85,310 seconds remained before the conservative 2026-11-27
14:19 PST hard deadline, anchored to initial task/source reading rather than
the later extraction start. Factored total projections including two-hour
reserve were 140,185 seconds for 50 epochs, 93,948 for 30, 70,829 for 20, and
52,334 for 12. Thus 20 is the largest fitting declared option; its projected
finish is about 10:17 PST on November 27. These are throughput projections,
not promises of completion or model-quality qualifications. Original and
tightened deadline records are both preserved privately.

Three inherited evaluator tests passed (synthetic geometry/ties/empty candidates);
syntax compilation passed. These are implementation checks, separate from the
real-image training pilot. No held-out model inference or detection-performance
result exists at this checkpoint. Private artifacts are under the canonical
`outputs/local_rtdetr_20261126` directory; public artifacts remain aggregate only.
