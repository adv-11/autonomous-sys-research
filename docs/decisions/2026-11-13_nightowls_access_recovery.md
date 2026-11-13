# Proposed single recovery after the stopped access pilot

My authorized no-retry pilot ended with zero images after the coordinator could not establish the actual-worker timeout guarantee. Both observed partial responses passed range/identity checks; this was a supervision stop, not a demonstrated server failure. Every pilot process was verified exited. The [original result](../gpt/2026-11-13_nightowls_image_access_result.md) and original executed-source identity remain preserved.

GPT Sol prepared one narrow, network-free correction: launch the base interpreter directly rather than the Windows venv redirector. The benign CPU probe exercised the exact proposed command, verified worker PID/parent identity and Pillow import, and exercised timeout/kill/wait with no remaining fixture process. Both actual access entry points remain disabled. The separate Opus review approved publication and the direct-launch correction, subject to a cumulative-budget fix now applied. No renewed access has been authorized or attempted.

If subsequently authorized, the proposal is **one new CPU-only window of at most 30 minutes**, with the **same fixed 64-image selection**, exclusions and no retries/Colab/GPU/inference/full-archive fallback. Preserve the original aggregate byte caps by charging the first attempt's full conservative reservation:

| Body-byte ledger | Original cap | Already charged | Maximum new transfer |
|---|---:|---:|---:|
| Total, including index | 150,000,000 | 7,432,416 | 142,567,584 |
| ZIP-index phase | 16,000,000 | 7,432,416 | 8,567,584 |

Use a distinct private attempt folder; never overwrite or treat the incomplete old index as verified data. Revalidate the same archive total, ETag and modification time before reading new bytes. Any transport, identity, mapping, CRC, decode or supervision failure ends the recovery without another repair cycle or replacement frames. The new absolute deadline, source hash and remaining budgets would be recorded only after explicit authorization. If the image route remains unsupported, report that limitation rather than extend this into infrastructure work. G0 remains pending.

## Review fixes and operator record

The disabled candidate now initializes both charged counters at `PRIOR_CHARGED = 7_432_416`; confirmed counters describe only a future attempt. Its eighth no-network selfcheck rejects an index reservation of 8,567,585 bytes from that initial state. The previously observed archive size, ETag and modification time are also initialized as the required identity; old interrupted bytes remain charged and cannot be reclaimed. Re-reading the complete index would charge another 7,432,416 bytes, leaving at most **135,135,168 bytes for subsequent image ranges**, with 1,135,168 bytes of index headroom. This is not an additional 150 MB budget.

A renewed operator must supervise the real `control_pid` in `control.json`, never the venv launcher PID. Set the working deadline 45 seconds before the new 30-minute outer window ends, preserving cleanup/read-timeout headroom; the controller derives its recorded stop time from the same `DEADLINE`. The worker has per-read deadline checks and a socket timeout of at most 30 seconds. The original receipts retain their original deadline.

Hash conventions: the historical executed hash `22e30ab6d4cc890e02e8243e4adbb74f414743352d3cbc1047c35dd67554cae2` identifies the LF Git blob at `4b211557`. The as-probed working snapshot `1a3d31181387861f3f6cf5c981508ce9799f94790adee2cc0ed6efe483447798` is CRLF; the corresponding LF blob at `f2ab537` is `728a1809769eeae65a7b0d806ec9bcf9f0800bc422cad5b3b395b3c2bf695cc5`. Subsequent counter/deadline-recording edits do not rewrite either historical identity or claim a new supervision probe.
