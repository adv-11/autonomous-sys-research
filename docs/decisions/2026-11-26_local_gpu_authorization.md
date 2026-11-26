# Local GPU research authorization and division of work

I explicitly authorized local GPU use on 2026-11-26 after repeated Colab
allocation failures, superseding the earlier Colab-only restriction. I also
asked to use both Claude and OpenAI models. GPT Sol is the sole local training
operator; Claude Opus at medium effort collaborates on the scientific design
and interpretation. Neither creates another operator or competing GPU job.

The coordinator checked `colab usage` and `colab sessions`: 169.50 CU,
0 assignments, 0.00 CU/h and no active sessions. There is nothing to stop.
No further paid allocation or automatic Colab retry follows from this decision.
The 140-CU project check-in remains in force; local time is not Colab CU.

## Actual local resource checks

- NVIDIA GeForce RTX 5060 Laptop GPU, 8,151 MiB total, 6,635 MiB free in the
  snapshot; no training process, desktop applications only, 0% utilization.
- About 15.5 GiB system RAM, only 2.8 GiB free. About 416.6 GiB disk free.
- Existing separate research environment: Python 3.12.14, torch 2.11.0+cu128,
  torchvision 0.26.0+cu128. These are package metadata, not a successful model
  compatibility check. Do not downgrade this working shared environment to
  the old Colab torch 2.4.1 recipe or claim identical numerics across runtimes.

Use local verified datasets and official hash-pinned weights/source; do not
download duplicate data or access credentials. Do not close desktop apps or
terminate unrelated processes. Start with a small Windows-compatible loader
(no worker-process replication or whole-dataset RAM cache while memory is low).
The first meaningful check is actual official-model loss/backpropagation on
real source images, not a synthetic training qualification or test framework.

## Training deliverable

Preserve the pinned RT-DETRv2 R18 model, ten-class ontology, exact source/
selection/test partitions, native query policy and reference evaluator. Freeze
a local-runtime amendment before any new held-out scores. Target source-only
training followed by matched day-only and day/night continuations; use the
already frozen mixed-training subset and a declared hash-selected day-only
control of the same image/update budget. No calibration, selection or test
labels enter training. Both continuations start from the same baseline EMA.

The local first study is bounded to **24 wall-clock hours including preparation,
training, inference and evidence capture**, with an independent deadline stop
and resumable checkpoints. Use at most one throughput pass capped at 45 minutes.
Choose baseline epochs from 50, 30, 20, 12 (largest fitting) using measured
throughput only, a 1.25 safety factor and at least two hours reserved for final
inference/retrieval. Continuations are five epochs each on 8,000 images with
matched optimizer/reset/augmentation rules. Freeze the exact selected plan
before baseline results; if it does not fit, report the blocker rather than
introduce another arbitrary epoch gate or silently shorten arms.

Try physical batch 16 only if the measured free memory permits. A single
documented reduction to batch 8 after a real OOM is permitted; then freeze and
use that batch for all local study arms. This is a locally amended experiment,
not an identical numerical reproduction of Colab. Changing the YOLO repeat
recipe is not authorized by that exception.

Report source-selected FPPI-1 and recall-target policies, actual night and
clear-day FP costs/recall, and explicit infeasibility. The matched continuation
control asks whether night data helps beyond additional day training; it does
not isolate architecture causality or establish method novelty. Preserve all
nulls and failed attempts. No test-based checkpoint or policy choice.

Two exact YOLO11s 1280-pixel, 100-epoch seeds remain authorized in principle,
but the original recipe's measured peak memory was about 16 GiB. Do not call
a smaller-batch/memory-modified local run an exact seed replicate. Defer those
runs if the original recipe cannot fit, and report that resource limitation.

## Collaboration and review

Claude may challenge the design and suggest only corrections within the
assigned local study. Focused active peer prompts are allowed; neither silence
nor a missing message route implies agreement. GPT owns implementation/runs;
Claude owns its concise scientific note. No additional paid compute, broad
model sweep, credentials or nested delegates. A separate independent review
of completed results is still required before a PR; my approval governs merge.
G0 remains pending. The unused T4-only proposal is superseded for execution.
