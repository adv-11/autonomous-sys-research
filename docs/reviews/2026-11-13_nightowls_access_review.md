# Independent Claude Opus review of the stopped NightOwls access pilot and supervision correction

**Disposition: APPROVE the stopped-pilot record and the disabled-code correction for publication. The direct-base-interpreter launch addresses the observed Windows venv-redirector PID mismatch well enough for one proposed future attempt. One P2 fix is required before any renewed run: encode the cumulative byte ledger in code.** Three P3 clarifications are listed below. This is a new Claude Opus 5.5 review task. It is an AI review, not my renewed image-access authorization or merge approval. **G0 remains PENDING.** No scientific or null performance claim follows.

**Coordinator disposition, 2026-11-13:** GPT Sol resolved P2 by seeding both charged counters from `PRIOR_CHARGED = 7_432_416` in the actual worker's shared initializer. The added no-network selfcheck rejects an 8,567,585-byte index reservation with the exact `index_byte_cap` reason; all eight protective selfchecks pass. The prior archive identity is pinned in that initializer as required by the recovery plan. The controller's displayed stop time now derives from `DEADLINE`. The recovery decision labels LF/CRLF historical hashes, requires operator supervision of real `control_pid`, and reserves deadline headroom inside any new window. Both actual entry points remain disabled, and no new HTTP or supervisor probe was run for these budget/metadata edits. The original approval and conditional finding are preserved; this is the coordinator's resolution, not renewed user authorization or new Opus verification.

## Scope

- **Original operator commit** `4b211557` (integrated as `1fd6f67`): `scripts/data/nightowls_image_access_pilot.py`, `docs/gpt/2026-11-13_nightowls_image_access_result.md` and `…_counts.json`.
- **Root correction** `f2ab537`: the same utility, now disabled; `docs/gpt/2026-11-13_nightowls_watchdog_probe.json`; `docs/decisions/2026-11-13_nightowls_access_recovery.md`; and the config, gate-log and drift-log entries.
- **Private evidence, read only:** `data/nightowls/image_access_pilot/2026-11-13/{logs,archive_index}` and `outputs/nightowls_watchdog_probe_20261113/`. Nothing was overwritten. A before/after SHA-256 listing of all 8 evidence files was identical.
- **Not done:** no HTTP request, archive or HEAD access, download, image, install, GPU, Colab, child task, retry, push, PR or merge. I did not inventory or kill any process except my own fixture child.

## What I verified directly

| Check | Result |
|---|---|
| Executed-source identity | The Git blob at `4b211557` and at `1fd6f67` hashes to `22e30ab6…cae2`, which matches the counts JSON. This is the **LF** blob hash. I did not find a separate private source copy in the private folders I inspected. The Git blob is the verifiable copy. |
| Candidate identity | The working-tree file (CRLF, `core.autocrlf=true`) hashes to `1a3d3118…7798`, which matches the probe JSON and byte-matches the private `candidate_utility.py`. The LF Git blob at `f2ab537` hashes to `728a1809…5cc5`. |
| Private artifact hashes | All 5 hashes in the counts JSON reproduce: request log, worker checkpoint at stop, original controller record, operator stop record and index tail. |
| HTTP evidence | 2 reservations and 2 `206` headers. Content-Range equals Content-Length equals the reservation (65,557 and 7,366,859). Both responses report total 57,481,286,834, ETag `"5ce813b8-d6226d4b2"` and Last-Modified Fri, 24 May 2019 15:54:32 GMT. There is 1 `body_complete` event and 0 `request_failed` events, which fits a forced kill and is not a handled error. There was no redirect or rejected response. |
| Byte accounting | Charged = 65,557 + 7,366,859 = **7,432,416**. Confirmed = **3,997,717** = 65,557 + 3,932,160, and the partial second body is exactly 60 × 65,536-byte checkpointed chunks. Partial bytes were only in memory and were never written. The `archive_index/` folder holds only the 65,557-byte tail. There are 0 PNG files. The lower and upper bounds are reported truthfully, and the exact consumption is correctly marked unknown. |
| Process identities | `control.json` `worker_pid` 32756 is the launcher. The checkpoint and operator record give the actual worker as 31788, with parent 32756. `control.json`'s historical `worker_exit_verified: true` therefore means the **launcher** exited. `status.json` and `operator_stop.json` carry the separate `actual_worker_exit_verified`. The report says "the controller captured the launcher exit" and makes no claim of orphan behaviour. This is accurate. |
| Timing | 19:44:06.286987 − 19:43:31.373845 = 34.913142 s. The stop came well before the 20:09:00Z deadline, which never fired. |
| Disabled refusal | `--execute` and `--worker` both exit 1 with `Stop: stopped_pilot_no_renewed_execution_authorization`. In both entry points the check runs before `mkdir`, before `requests.jsonl` is opened and before any request. Two more independent barriers remain: the expired `DEADLINE` makes `check_time` stop, and the existing `DEST` makes `mkdir(exist_ok=False)` refuse. |
| `--selftest` | 7/7 pass with 0 network requests. Each cap check asserts its exact reason (`total_byte_cap` or `index_byte_cap`) and is isolated from the expired deadline through `patch.dict`. The checks leave state unchanged. |
| Privacy | The public diff contains no native file names or IDs, image paths, user paths or interpreter paths. |

Checker: [`2026-11-13_nightowls_access_check.py`](2026-11-13_nightowls_access_check.py). It is read-only, prints aggregates only and exits 0.

## Supervision probe (one run, my own fixture)

[`2026-11-13_nightowls_access_probe.py`](2026-11-13_nightowls_access_probe.py) loads the current module from the worktree file without running `__main__`. It asserts `EXECUTION_AUTHORIZED is False` and calls the real `worker_command()` with a scratchpad benign worker as the target. The worker imports Pillow, prints its PID and parent PID, then sleeps 20 s. The harness ran under the venv `Scripts\python.exe` redirector, which reproduces the original condition.

- The child ran the uv base `python.exe` with `-I -B`. `argv[1:]` was `["--worker"]` and Pillow 13.0.0 imported from the venv site-packages.
- **Child PID equalled `Popen.pid`**, and the child's parent PID equalled the controller's real PID.
- `wait(timeout=2)` raised `TimeoutExpired`. `kill()` and `wait()` then reaped that exact child (return code 1, 2.125 s total).
- **Negative check:** the same command launched through one intermediate interpreter failed with `AssertionError: unexpected_worker_parent` before `runpy`. The parent-PID guard therefore rejects an extra process layer instead of silently accepting it.
- No HTTP, GPU or other process was touched. The private result is in my scratchpad and is not committed.

**Judgement.** The worker is a single process: urllib, zipfile and Pillow start no subprocesses. Under the corrected command, `Popen.pid` is that process, so the controller's `kill()` targets the HTTP worker itself. The incident mechanism (a timeout aimed at a redirector whose child does the I/O) is removed for this worker. This is **not** general process-tree coverage, and it does not show that the old launcher would have orphaned its child.

## Findings

**P2: required before any renewed run (not blocking publication).** The cumulative ledger is only a table in the recovery decision. The worker still starts with `charged_bytes = index_charged_bytes = 0` against `TOTAL_CAP = 150_000_000` and `INDEX_CAP = 16_000_000`. If an authorization edit changed only `EXECUTION_AUTHORIZED`, `DEADLINE` and `DEST`, the run could transfer up to 150 MB of new data and breach the stated cumulative caps. *Smallest fix:* add one `PRIOR_CHARGED = 7_432_416` constant and add it to both charged counters at state initialisation. Add one selftest assertion that a fresh-state index reservation of 8,567,585 bytes raises `index_byte_cap`.

**P3: hash normalisation labels.** The executed hash `22e30ab6…` is the LF Git blob. A CRLF checkout of that blob hashes differently. The candidate hash `1a3d3118…` is the CRLF working tree, and its LF blob hashes to `728a1809…`. *Fix:* label the normalisation of each hash in the probe JSON or the recovery decision. Do not replace the historical hash.

**P3: controller-level supervision scope.** My probe shows the controller itself still runs under the venv redirector. Any operator-side watch must target `control.json`'s `control_pid` (the real interpreter), not the shell's launcher PID. If the controller is lost, the worker still bounds itself: `check_time` runs per read of at most 64 KiB, and the socket timeout is at most 30 s. It would stop within about 30 s after the absolute deadline, plus at most one in-progress image decode. *Fix:* add one sentence to the renewed authorization record. No code change is needed.

**P3: duplicated deadline literal.** `controller()` writes `absolute_stop_utc: '2026-11-13T20:09:00Z'` as a literal, separate from `DEADLINE`. *Fix:* derive the string from `DEADLINE` so a renewed window cannot record a stale stop time.

**Informational.**
- The index-budget arithmetic is correct: 16,000,000 − 7,432,416 = 8,567,584 left. A deterministic fresh re-read of the tail plus the central directory costs 7,432,416 again and fits, with 1,135,168 bytes to spare. The total left after that re-read is 142,567,584 − 7,432,416 = **135,135,168** for the 64 images, against 142,567,584 in the original plan. A cap stop then counts as a failure under the no-retry rule. The authorization question should state this.
- `status.json` was rewritten by the operator, and its hash is not published. The unmodified checkpoint and the operator record are both preserved and hashed, so nothing is lost.

## Report truthfulness

The result note, counts JSON, gate and drift entries, and recovery proposal match the raw evidence. They keep the actual worker's exit separate from the launcher's exit. They do not claim an orphan, a server failure or any image coverage. They keep the 64 permanent exclusions and the original cumulative caps with no new 150 MB budget. They require renewed explicit authorization, a new absolute window of at most 30 minutes and a fresh private folder.
