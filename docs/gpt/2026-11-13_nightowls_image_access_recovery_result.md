# NightOwls renewed image-access result

GPT Sol acted as the sole implementation operator. My explicitly authorized single renewed CPU acquisition was invoked once from activation commit `4df615fe442f363f5504c8c10b688d78916548b4`. **Zero of the fixed 64 images were completed.** The operator reported a session interruption during the index read; after resumption, all recorded owned PIDs were absent and the absolute deadline had passed. No acquisition was restarted. This is an incomplete access-feasibility result, with no model results. **G0 remains pending.**

The [counts-only receipt](2026-11-13_nightowls_image_access_recovery_result.json) records the durable evidence and its limitations. The interruption's cause is unverified. Neither response demonstrates a transport failure: both HTTP 206 responses passed range and pinned archive-identity checks before body reading. The first range completed; the second has no completion or error receipt.

## Acquisition and budget evidence

- Fixed selection: 64 images, all 64 permanent exclusions retained; no replacement images.
- Complete ZIP-index ranges: 1, containing 65,557 bytes. The full index and exact 64-member mapping were not verified.
- Verified completed images: 0; ZIP CRC, Pillow verify, full decode and dimension coverage: 0/64 each. No image files or image-range reservations exist.
- Requests reserved: 2; requests with completion receipts: 1; accepted HTTP 206 range/identity responses: 2.
- Prior conservative charge: 7,432,416 bytes in both total and index ledgers. This attempt reserved another 7,432,416 bytes. Cumulative total and index charges are each **14,864,832 bytes**, against caps of 150,000,000 and 16,000,000 respectively. No reservation was reset or refunded.
- This attempt's durable confirmed-byte lower bound is **4,259,861 bytes**, entirely index traffic. Exact received bytes are unknown because the second request has no terminal receipt. Confirmed counters exclude prior-attempt traffic.
- GPU operations/queries, Colab sessions, inference, installations, automatic retries and full-archive fallback: all zero.

## Activation, supervision and terminal limits

The authorization began at `2026-11-14T00:15:36Z`. The unchanged script working deadline was `2026-11-14T00:44:51Z`; the absolute outer end was `2026-11-14T00:45:36Z`. The controller started at `00:17:03.533979Z` and the worker at `00:17:03.808237Z`. The last durable worker checkpoint has filesystem modification time `00:18:17.318117Z`, establishing an observed elapsed lower bound of **73.509880 seconds**. Exact elapsed time, CPU time and termination time are unavailable.

The operator supervised actual controller PID **34592**, read from the fresh `control.json`, rather than venv launcher PID **11960**. The direct-base worker PID was **29568**; the PowerShell supervisor PID was **34484**. The reviewed `worker_command` was unchanged. The controller's last durable status is `WATCHING`, with `worker_exit_verified=false`; the worker's last status is `INDEX`. No terminal controller, worker, launcher or supervisor exit code survived. The previous execution session was unavailable when queried after resumption.

At `2026-11-14T21:33:06.4159817Z`, a process inventory found all four recorded PIDs absent. No process needed termination at that observation, and no further execution or HTTP was initiated. **Absence at that observation does not establish when the processes exited or verify deadline compliance.** The missing terminal receipts are a supervision-evidence failure; no server-failure conclusion or precise interruption cause is supported.

## Private artifacts and safe result commit

Canonical ROOT was `C:/Users/Advait/autonomous-sys-research`, independently of this checkout. The fresh destination was `data/nightowls/image_access_pilot/2026-11-13_attempt2` beneath that root. Its private logs retain the request receipts, incomplete worker/controller checkpoints, complete index tail, exact executed source, launch supervision receipt and post-interruption observation. Additional private launch receipts remain under canonical `outputs/nightowls_image_access_recovery_20261113`. The original `data/nightowls/image_access_pilot/2026-11-13` evidence was not modified.

The exact executed working-file snapshot SHA-256 is `f5e1725a314368a2ce8cc8eb79d94f722aace93211c2a10b03199d5d10b436df` (CRLF bytes, distinct from a normalized Git blob). Both private snapshot copies agree. Its normalized LF SHA-256 is `750cd43cb6788b7948b3fe24e2c152aebd56f4cf1bf985e327a393c128cfdba4`, corresponding to activation Git blob `31ad29486f6dc2de7a2d4438baf8fdafc6bcaa09`; these are distinct hash conventions. The selection and annotation hashes remain pinned in the recovery config and receipt. Native IDs, names, boxes, index contents and images remain private and outside Git.

Offline receipt checks reconciled reservation totals, source snapshots, request/identity receipts, the empty image directory and the absent recorded PIDs. They passed; they do not replace missing terminal evidence. The existing eight synthetic selfchecks and benign supervision probes were not rerun or presented as new empirical verification.

The result changes only the new report/JSON, recovery-config outcome and this checkout's `EXECUTION_AUTHORIZED=False` flag. Activation, destination and deadline history remain explicit; the preserved executed snapshot retains its original enabled flag. The historical report/config, shared README and coordinator state remain untouched. No push, PR or merge is part of this milestone. A subsequent acquisition requires a separate authorization.

## Independent review and coordinator disposition

[Claude Opus independently reviewed the saved evidence](../reviews/2026-11-14_nightowls_recovery_review.md) in `4fa7de8` and approved publication after a small disabled-code correction. GPT Sol applied M1 and advisories A1?A4: the current disabled utility starts both charged ledgers at **14,864,832 bytes**, describes the consumed authorization, and rejects an index reservation one byte beyond the remaining **1,135,168 bytes**. Historical executed snapshots and receipts remain unchanged. The recovery config separates authorization-time budgets from the terminal balances. No further access, probe or supervision change followed.

The synthetic cap check validates accounting behavior only. The independent review does not supply the missing exit times or deadline evidence, and my merge approval is still required.
