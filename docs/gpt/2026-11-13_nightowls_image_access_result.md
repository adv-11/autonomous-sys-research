# NightOwls image-access pilot: stopped execution

I authorized only the fixed private 64-image access pilot in the [decision](../decisions/2026-11-13_nightowls_image_access_pilot.md) and [configuration](../../configs/research/nightowls_image_access_pilot_20261113.json). GPT Sol was the sole operator on 2026-11-13. **The pilot was executed once and stopped during ZIP-index retrieval: 0/64 images completed. G0 remains PENDING.** No image selection, annotation policy, evaluator or adapter changed. All 64 planned images remain permanently excluded from a later quantitative image pool, regardless of retrieval success.

The existing [Claude Opus adapter/plan review and GPT coordinator disposition](../reviews/2026-11-13_nightowls_adapter_review.md) were read before execution. Those are historical review evidence, not independent verification of this new utility or result. Formal publication review belongs to the coordinator; no new reviewer or child agent was launched.

GPT Sol implemented a task-specific stdlib urllib range/file interface for stdlib `ZipFile`, with bounded reads, ZIP64 support delegated to stdlib, exact member-mapping checks, PNG bounds, CRC and Pillow verification/load checks. Before endpoint access, seven in-memory protective checks passed: non-206, mismatched/missing range, changed validator/total, and total/index-cap refusal. Neither these synthetic checks nor the implemented image checks establish successful real image access. Both pinned input hashes and the unchanged 64 native records were checked locally without resampling or GT-based selection.

## Actual outcome

The controller ran from **19:43:31.373845 to 19:44:06.286987 UTC**, about **34.913 seconds**. It durably recorded its PID and timeout before launching a separate subprocess and atomically checkpointed request reservations and reads. The timeout was bounded by 30 minutes and the absolute **20:09:00 UTC** stop, with a one-second termination margin.

During execution, GPT Sol observed that the Windows venv launcher PID differed from the actual Python HTTP-worker PID. The controller's timeout targeted the launcher, while termination of its descendant was not verified. GPT Sol therefore stopped the actual identified HTTP worker immediately rather than allowing an unverified process-tree watchdog to continue. The controller captured the launcher exit. A subsequent host process inventory verified zero live pilot Python processes; the host command/session also exited. This is a conservative operator stop for an unverified guard, **not a demonstrated transport failure or proof that terminating the launcher would leave its child alive**. The deadline mechanism never fired. There was no restart, repair loop, replacement frame or further network request.

| Observed quantity | Result |
|---|---:|
| Requests reserved / complete / interrupted | 2 / 1 / 1 |
| Responses with accepted 206, exact range and identity checks | 2 |
| Durably confirmed body bytes (lower bound) | 3,997,717 |
| Conservative charged body bytes (upper bound) | 7,432,416 |
| Index charged bytes / index cap | 7,432,416 / 16,000,000 |
| Total charged bytes / total cap | 7,432,416 / 150,000,000 |
| Complete private index ranges / bytes | 1 / 65,557 |
| Completed exact member mappings / PNGs / CRC / verify / load | 0 / 0 / 0 / 0 / 0 |

The second request reserved its entire 7,366,859-byte central-directory range before opening the connection. Forced termination may have interrupted a read or its checkpoint; the exact total consumed is unavailable. The confirmed count is therefore a durable lower bound, and the full reservation remains charged. Both bounds include the complete first suffix response. No uncertain partial bytes are presented as an exact transfer count. The worker checkpoint at termination, original controller evidence, response metadata, reservations, accepted identity checks and completed tail are retained privately; a separate operator record explains the terminal status. No PNG payload exists.

Both accepted responses reported total archive length **57,481,286,834 bytes**, ETag **`"5ce813b8-d6226d4b2"`**, and Last-Modified **24 May 2019 15:54:32 GMT**. The source was the configured publisher HTTPS archive. There was no observed identity change, redirect, cap breach or rejected response. A complete index, selected-member mapping, image CRC and decode coverage remain unestablished.

The [compact aggregate JSON](2026-11-13_nightowls_image_access_counts.json) records bounds, timing and artifact hashes. Raw logs, controller records, index bytes and the fixed selection remain private and gitignored under the canonical project root. Native names and IDs are absent from the public artifacts. The utility is preserved as executed; its process-tree timeout is **not qualified for reuse with this Windows venv launcher**. No corrective implementation or second execution was attempted.

There were **0 GPU operations, 0 Colab sessions, 0 inference calls, 0 package installs, 0 retries and no paid compute**. No model, torch, Ultralytics, CUDA or Colab CLI was imported or queried. The abrupt worker termination precluded a final CPU-time sample; the observed controller wall duration is reported instead. No push, PR or merge occurred in this task. This stopped access pilot supports no detector or scientific performance claim and does not pass G0.

## Later coordinator correction — no network or retry

GPT Sol preserved the executed utility and receipts, disabled both current worker/controller entry points, and prepared one launcher correction: use the actual base Python interpreter directly with the existing Pillow path and a parent-PID check before the target script. A benign CPU probe confirmed that its reported PID equals `Popen.pid`, Pillow imports, and the same timeout/kill/wait path stops and reaps that exact process. The [counts-only probe record](2026-11-13_nightowls_watchdog_probe.json) distinguishes this synthetic supervision check from real access. It does not prove that the old launcher would leave its child alive, validate every process tree, complete ZIP retrieval or authorize a second attempt.

The transport reader and fixed cohort are unchanged. Cap selfchecks now test their exact rejection reasons independently of the expired historical deadline. Original executed-code hashes remain historical; the current disabled candidate has a separate identity. The [recovery proposal](../decisions/2026-11-13_nightowls_access_recovery.md) is pending independent review and renewed explicit authorization. No further HTTP request occurred during this correction.
