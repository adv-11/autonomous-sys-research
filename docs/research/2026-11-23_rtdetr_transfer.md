# RT-DETRv2 daytime-to-night transfer: blocked before allocation

GPT Sol, sole designated Colab operator, 2026-11-23. **No experiment ran. G0 remains pending; method novelty is not established.**

I want to establish whether clear-day-to-night pedestrian threshold transfer persists for an official RT-DETR family model, and whether ordinary balanced day/night adaptation improves night recall versus FPPI while retaining clear-day performance. This is exploratory new-model research on previously observed BDD, not a fresh-test or preregistered novelty claim.

## Concrete blocker

The first CLI invocation, `colab --help`, failed before the executable could run:

```text
Program 'colab.exe' failed to run: An Application Control policy has blocked this file
CategoryInfo          : ResourceUnavailable: (:) [], ApplicationFailedException
FullyQualifiedErrorId : NativeCommandFailed
```

`Get-Command` resolved `C:/Users/Advait/.local/bin/colab.exe`; its SHA-256 is `afd48d325cdd9ba1aa1097f58bc1a11d506a3b47ca5722dbb84ae9b9649d713d`. No policy change or alternate launch route was attempted. The error is from Windows Application Control, not a Colab authentication or model failure. The CLI's current version and account connectivity were not verified. The copied error excerpt and CPU manifest observations are preserved privately under `C:/Users/Advait/autonomous-sys-research/outputs/rtdetr_transfer_20261123/`.

No paid allocation was attempted. `colab usage` and `colab sessions` could not be obtained through the blocked CLI, so the current balance, other compute owners and server-side assignment state are unknown. This task created no sessions; that is distinct from verifying zero assignments on the server. No training, pilot, inference, evaluation, local GPU operation or dataset upload occurred. Training curves, recall–FPPI curves and measured miss splits therefore do not exist for this stage.

## Preserved contract and evidence

GPT Sol read CONTRIBUTING, the charter, GPT protocol, peer protocol, the original BDD report including its erratum, the threshold-remedies report, all four amendments, the existing config and `remote.py`. No incoming NightOwls scores were requested, read or used. No peer exchange or independent review occurred in this task.

The [official implementation](https://github.com/lyuwenyu/RT-DETR) identifies the repository as the authors' RT-DETR and RT-DETRv2 implementation. Its [RT-DETRv2 model table](https://raw.githubusercontent.com/lyuwenyu/RT-DETR/main/rtdetrv2_pytorch/README.md), accessed 2026-11-23, links RT-DETRv2-S to the R18 config `rtdetrv2_r18vd_120e_coco.yml` and [official COCO checkpoint](https://github.com/lyuwenyu/storage/releases/download/v0.2/rtdetrv2_r18vd_120e_coco_rerun_48.1.pth). This verifies the published artifact route, not the checkpoint bytes, native behavior or runtime compatibility. No weights were downloaded. No YOLO substitution was made.

GPT Sol independently checked the canonical local manifest bytes with SHA-256 and counted their entries: **10,635 source-training images, 1,842 selection images, all 10,000 validation images**. All three hashes and the pedestrian-GT hash match the existing committed config. This is data-integrity evidence, not detector performance. The ten classes and separate pedestrian/rider mapping are retained in the [incomplete config](../../experiments/2026-11-23_rtdetr_transfer/config.json).

That config deliberately has `execution_permitted: false`. It preserves the authorized goals, manifests, class mapping, source-only recall targets 0.80/0.90/0.95, explicit infeasibility, secondary source FPPI 1 and budget constraints. **It is not a fully frozen executable contract:** exact code revision, weight hash, environment, training recipe, native preprocessing/query-top-k/class-filter order and optional adaptation subset remain unset. No inference or evaluation may precede their committed freeze. The intended adaptation excludes the existing 2,000-image night-calibration set and all source-selection/val/test images; no adaptation subset was generated or trained.

The miss-split interpretation follows the original report's erratum: absolute night unmatched share is `1-M_night`; the signed ceiling component is `M_clear-M_night`; the signed threshold component is `(M_night-R_night)-(M_clear-R_clear)`. None is measured here.

## Budget and stopping disposition

The [ledger](2026-11-23_rtdetr_transfer/compute_ledger.json) records zero new allocations, zero allocated hours and zero CU attributable to allocations by this task. Account balance delta remains unmeasured. Historical project spend is the reported 60.9 CU, not a new usage check. The stage retains the stricter of 25 CU and 12 allocated hours, rate at most 3 CU/h, one owned session and the 100 CU project check-in.

The unmeasured planning envelope reserves 0.75 h for setup/download, at most 1 CU for the first pilot, 6 h for training, 0.75 h for inference/retrieval/teardown and 1.5 CU reserve: 25 CU at the rate cap. It establishes a cap, not feasibility of 50 epochs. A throughput-only pilot must determine the feasible epoch budget before outcomes, with adaptation pending if it cannot fit. No watchdog was started because no allocation was possible; a functioning independent budget/deadline stop remains required before any allocation.

The stage stops at this environment blocker, as authorized. Restoring policy-approved execution of the connected Colab CLI is the next dependency. After that, the remaining contract must be frozen and the current usage/sessions checked before allocating. Baseline transfer, adaptation benefit and clear-day retention remain unanswered. No push, PR, merge, child task or independent review was initiated.
