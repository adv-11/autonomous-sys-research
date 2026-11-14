# Independent Claude Opus review of the renewed NightOwls access result

**Disposition: APPROVE the renewed zero-image result, the cumulative accounting and the disabled flag for publication once one small must-fix is applied.** The must-fix is in the disabled script, not in the result: its docstring still says the attempt is authorized, and `PRIOR_CHARGED` still holds the pre-attempt-2 charge. The result report and JSON match the private receipts. They make no server-failure, cause, duration or deadline claim. The privacy boundary holds. G0 remains pending. This review does not authorize any further access.

Reviewer: Claude Opus 5.5, as a separate review task, on 2026-11-14. This review does not re-review NightOwls science or adapters; it reuses [the prior Opus access review](2026-11-13_nightowls_access_review.md) (`41f55ac`).

## Scope

| Item | SHA |
|---|---|
| Root HEAD (`nightowls-image-access-pilot`) | `54f82d9b1fb5fce1b39bb33929eb10fe5efeb34f` |
| Activation | `4df615fe442f363f5504c8c10b688d78916548b4` |
| Producer commit (GPT Sol) | `fcf6d79b74c674915b127719f84f90e8bf4585a6` |
| Integrated as | `b2a0759e4545891480c51fae9b353fae664adb19`. Tree `d3c87ff3…` and parent `4df615f` are both identical to the producer commit's, so this is a byte-identical integration. |
| Coordinator disposition | `54f82d9` (README, drift log and decision appendix) |

Private evidence was read only, under canonical ROOT `C:/Users/Advait/autonomous-sys-research`:

- `data/nightowls/image_access_pilot/2026-11-13_attempt2/`
- `outputs/nightowls_image_access_recovery_20261113/`
- the original `data/nightowls/image_access_pilot/2026-11-13/`, used for the unchanged-evidence check

**Not done:** no network/HTTP request, image access, install, GPU query, torch import, Colab session, inference, child task, process inventory, selftest rerun, push, PR or merge. Checks used `sha256sum`/`cmp`, `git` and stdlib Python with `-I`. The index tail and any native IDs or names were never printed.

## Evidence checks

| Check | Result |
|---|---|
| Private artifact hashes | All 7 `artifact_sha256` entries in the result JSON reproduce exactly: executed source, request log, status, control, launch receipt, post-interruption observation and index tail. Both `stdout`/`stderr` logs and both controller logs are empty (0 bytes). |
| Duplicate copies | `outputs/…/executed_source.py`, `supervision.json` and `post_interruption_terminal_observation.json` are byte-identical (`cmp`) to their `logs/` counterparts. |
| Executed source identity | `f5e1725a…436df` is CRLF: 22,092 bytes, 469 CRLF line endings, no bare LF. Normalized to LF it is SHA-256 `750cd43c…dfba4`, Git blob `31ad2948…` — exactly the activation blob at `4df615f`. Its flag is `EXECUTION_AUTHORIZED = True`, with `DEST …_attempt2` and `DEADLINE 2026-11-14T00:44:51Z`. HEAD differs from the activation blob only by `True → False` (HEAD blob `31926cfd…`). |
| Requests | 2 reservations. Both returned a `206` response whose Content-Range and Content-Length equal the reservation (65,557 and 7,366,859). Both carry the pinned total 57,481,286,834, ETag `"5ce813b8-d6226d4b2"` and Last-Modified, and both have `identity_accepted_before_body`. There is 1 `body_complete` and **0** `request_failed`/`http_error` events. The request log does not support any server or transport failure claim. |
| Charged ledger | 7,432,416 + 65,557 = 7,497,973; + 7,366,859 = **14,864,832**. This equals 2 × 7,432,416, and the total and index ledgers are identical. `status.json` agrees. Nothing was refunded. |
| Confirmed lower bound | **4,259,861** = 65,557 + 64 × 65,536. The second body stopped at exactly 64 checkpointed 64-KiB chunks, held only in memory. `archive_index/` holds one 65,557-byte file. Its hash equals the original attempt's tail, consistent with the pinned identity. |
| Images | `images/` is empty, and every per-image counter is 0. No image-phase reservation exists. |
| Caps | Index: 16,000,000 − 14,864,832 = **1,135,168** remaining, which is less than the 7,432,416 bytes a full index reread needs. Total: 135,135,168 remaining. The decision's "accounting evidence, not proof the route is unusable" wording is correct. |
| Timing | Last worker checkpoint mtime − worker start = 00:18:17.318117 − 00:17:03.808237 = **73.509880 s**, matching the JSON. The controller's `timeout_seconds` 1667.466 from 00:17:03.534 ends at 00:44:51Z. |
| Original attempt | All 5 original private hashes in `…image_access_counts.json` still reproduce. File mtimes are all on 2026-11-13 between 11:43 and 11:45 PST. The historical report and config are untouched in `4df615f^..54f82d9`. The decision doc and drift log were only appended to. |
| Disabled entry | `controller()` and `worker()` both call `require_execution_authorization()` before `mkdir`, before any log is opened and before any request. HEAD's flag is `False`. Two more independent barriers remain: the past `DEADLINE` (`check_time`) and `DEST.mkdir(exist_ok=False)` on the existing `_attempt2` directory. I did not execute the script to test this. |
| Fixed cohort | Selection `4f31e685…` and annotation `584c0dc1…` hashes are unchanged in the config, the result JSON and the source. The cohort has 64 planned images, and all 64 remain permanent exclusions. |
| Privacy | The public diff `4df615f^..54f82d9` contains only counts, hashes, PIDs, timestamps and the already-public archive URL and identity. It contains no native file names or IDs, boxes, index records or images. |
| Attribution and scope | GPT Sol is named as the operator. The result is stated as access feasibility only, with no model or novelty claim. G0 is pending in every file. |

## Terminal limits (agree with the report)

- **Not established:** controller 34592 and worker 29568 were only observed absent at `2026-11-14T21:33:06Z`, about 21 hours after the deadline. Their exit codes, end time, exact duration and deadline compliance are not established. That absence is a point-in-time observation.
- **Reviewer inference from the code paths (not new evidence):** a running worker checkpoints after every ≤64-KiB read. Its socket timeout is ≤30 s, and any exception, including `absolute_deadline`, writes a `request_failed` event and a `STOPPED` status. A controller that was alive at its wait timeout would have written `WATCHDOG_KILLED` or `WORKER_EXITED`. Neither record exists. So the most likely explanation is that both processes ended without Python-level cleanup, through an external hard termination or a suspension that never resumed. Whether that happened before the deadline cannot be shown. This does not support a server-failure claim, and the report correctly makes none.
- Both attempts stopped inside the same 7,366,859-byte central-directory request at about 4 MB (3,997,717 and 4,259,861 confirmed bytes). The two stops had different recorded triggers. This is a coincidence-level observation, not a causal finding.

## Must-fix (small; root may apply without another review)

**M1. The disabled script is not truthful about its current state or the cumulative charge.** In `scripts/data/nightowls_image_access_pilot.py` at HEAD:

- The docstring at lines 3–4 still reads "Renewed single attempt explicitly authorized… Prior charges remain cumulative".
- `PRIOR_CHARGED = 7_432_416` at line 33 seeds both ledgers with the pre-attempt-2 charge.

If the flag, `DEST` and `DEADLINE` were changed for a future run, the worker would allow another full 7,432,416-byte index read. That read would reach 14,864,832 under its own ledger, but the true cumulative total would be 22,297,248, which exceeds the 16,000,000 index cap. This is the same class of issue as the prior review's P2. It is latent only, because three barriers currently block execution.

Fix either way:

- (a) Set `PRIOR_CHARGED = 14_864_832` and update the docstring to "Consumed renewed attempt; execution disabled; no retry authorized". The existing `prior_index_cap` selfcheck, which reserves 8,567,585 bytes, still rejects with the same reason.
- (b) Text only: change the docstring, and add a comment on `PRIOR_CHARGED` stating that the true cumulative charge is 14,864,832 and that the constant must be updated before any future authorization.

The preserved executed snapshot keeps its original text either way.

## Advisory

- **A1.** Result md, paragraph 2: "Neither partial response demonstrates a transport failure". Only the second response was partial. Suggest "Neither response…".
- **A2.** Record the LF identity of the executed source next to the CRLF hash, following the convention in the decision doc: LF SHA-256 `750cd43cb6788b7948b3fe24e2c152aebd56f4cf1bf985e327a393c128cfdba4`, which equals Git blob `31ad29486f6dc2de7a2d4438baf8fdafc6bcaa09` at `4df615f`.
- **A3.** "The session was interrupted during the index read" is the operator's account. No durable receipt records the session interruption itself, only the absence of later checkpoints. Suggest "the operator session was interrupted (operator-reported)".
- **A4.** The recovery config keeps the authorization-time `max_additional_*` and `max_image_bytes_after_index_reread` fields. Prefix them or annotate them as historical so that 135,135,168 is not read as currently usable image budget, since the index cap now binds first.
- **A5.** Optional: the code-path inference above could be added to the result as a labelled reviewer inference. It is not required.

## Remaining missing evidence (not recoverable from saved receipts)

- Terminal exit codes for the controller, worker, launcher and supervisor
- Process end times, exact elapsed and CPU time, and bytes received after the last checkpoint
- The cause of the interruption, and deadline compliance

No fresh process inventory, retry, probe or supervision framework is recommended. The saved receipts are sufficient to close this access record as a truthful zero-image result.
