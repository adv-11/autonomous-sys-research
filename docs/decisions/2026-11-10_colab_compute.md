# Colab compute direction

I authorized moving all GPU operations to my connected Colab account on 2026-11-10, with scale guided by research value and available compute. This supersedes the earlier local overnight-resource assumption; it does not adopt a new dataset split or authorize an AI merge.

GPT coordinator verified `colab usage`: **300.00 compute units**, rate **0.00/hour**, zero assignments. CLI version is 0.8.0. No account identity or session credentials belong in Git. The [official CLI](https://github.com/googlecolab/google-colab-cli) documents ephemeral execution and teardown. Its installed help is the command contract used here.

## First allocation estimate, before launch

- One L4 qualification session, no concurrent allocation. Requesting L4 does not prove availability. If unavailable, stop and reconsider the cheaper supported option rather than repeatedly retrying or silently upgrading.
- Intended work: pinned YOLO11s checkpoint, three FP32 optimizer updates on synthetic empty-target images at batch 2, 640 pixels; finite loss/gradients, changed parameters and checkpoint tensor round-trip. This is a new-platform mechanics check, not a dataset evaluation or a research training run.
- Unmeasured estimate: 2–10 minutes including dependency setup, under 8 GiB VRAM. Remote script deadline is 600 seconds; outer allocation/retrieval/cleanup target is 15 minutes. These are different scopes. Inspect actual account rate immediately after allocation; admit execution only if rate is at most 8 compute units/hour, giving at most 2 units over that outer window. No top-up or new subscription purchase is authorized by this plan. Dollar equivalence is not verified; use the existing unit balance, not an invented exchange rate.
- Retrieve summary and environment before stopping the session, with cleanup also on failure. Record actual balance/rate/elapsed time afterward. No Drive mount, dataset redistribution, local CUDA access or claim of a complete training-resume test is required.

## Scaling rule

Measure throughput, memory, successful updates and unit rate before choosing a longer budget. Expand useful seeds, matched pipeline controls and statistically justified sample support before a model zoo or Cartesian sweep. Larger VRAM cannot restore missing independent groups or revised BDD labels. The four-condition calibrated bridge stays on hold; the reviewed prototype stays disabled until its concrete runtime findings are resolved and reviewed. Keep source-only development separate from target evaluation and stop null contrasts before spending target compute.

Training and longer allocations need an exact config, successful-update/attempt budget, checkpoint/resume and output-retrieval plan, estimated units and a stated stopping criterion. The coordinator owns session creation and cleanup; peer agents do not create competing sessions or spend the whole balance independently. My explicit approval still governs sequential PR merges. G0 remains pending.

## Qualification progress

The first L4 allocation charged **1.94 units/hour** and exposed Python 3.13.16, torch 2.14.1+cu130 and 23,659,151,360 bytes of device memory. The model checkpoint matched the existing SHA-256. The first direct loss call failed before any update because the coordinator supplied a dictionary where Ultralytics expects a configuration namespace. The summary was retrieved and the session terminated. A local console encoding error also obscured CLI output; the private controller log preserves it. One bounded retry fixes the concrete configuration and UTF-8 output errors. No tuning or additional model was added. The remote runtime differs from the Windows smoke environment and cannot inherit its numerical equivalence claim.

**Outcome:** the retry passed configuration setup but failed because its loss had no autograd graph. Both attempts completed **zero optimizer updates**. The cause of the second failure is not yet verified; inspect checkpoint parameter flags and gradient context rather than guessing a successful fix. Both sessions terminated, verified by a final usage/session read: zero active assignments, zero current rate, displayed balance still 300.00 units. Billing may lag; an unchanged displayed balance is not evidence of free compute. At the observed rate, the recorded outer durations (53.594 and 31.391 seconds) imply roughly 0.046 units, an estimate rather than an invoice.

`colab exec` returned zero despite the remote Python exception on the retry. The private controller's word `completed` describes CLI transport only and is **not** a successful qualification: the retrieved `summary.json` says FAIL. Future controllers must validate required artifacts, status and successful-update counts before declaring success. No third allocation follows this failure. A bounded CPU repair and research-priority task precede further compute; no general scheduler or platform rewrite is needed.

## Next bounded assignment

Prepare one Colab-native development pilot with actual native outputs and strict unsupported states, while retaining the old prototype hold. In parallel, decide which falsifiable contrast is executable with verified current data. Consider a separately named frozen COCO-to-ACDC descriptive diagnostic only if its source semantics, leakage controls and limited uncertainty claims are explicit; it must not silently replace clear-day BDD or rescue the unsupported four-condition calibration design.

Use an initial **10-unit planning envelope**, not an allocation authorization for either peer. At the observed L4 rate that would be about 5.15 runtime hours if the rate stayed constant, before setup/retrieval overhead. The coordinator admits smaller staged runs after review and current usage checks. Defer larger-model and training-seed spending until a useful non-null contrast and feasible data protocol justify it. Deterministic inference repetitions with different seeds are not independent trained-model replicates.
