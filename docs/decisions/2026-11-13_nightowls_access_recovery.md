# Proposed single recovery after the stopped access pilot

My authorized no-retry pilot ended with zero images after the coordinator could not establish the actual-worker timeout guarantee. Both observed partial responses passed range/identity checks; this was a supervision stop, not a demonstrated server failure. Every pilot process was verified exited. The [original result](../gpt/2026-11-13_nightowls_image_access_result.md) and original executed-source identity remain preserved.

GPT Sol prepared one narrow, network-free correction: launch the base interpreter directly rather than the Windows venv redirector. The benign CPU probe exercised the exact proposed command, verified worker PID/parent identity and Pillow import, and exercised timeout/kill/wait with no remaining fixture process. Both actual access entry points remain disabled. Independent review of the stopped execution and proposed correction comes before a renewed authorization question; no new access has been authorized or attempted.

If subsequently authorized, the proposal is **one new CPU-only window of at most 30 minutes**, with the **same fixed 64-image selection**, exclusions and no retries/Colab/GPU/inference/full-archive fallback. Preserve the original aggregate byte caps by charging the first attempt's full conservative reservation:

| Body-byte ledger | Original cap | Already charged | Maximum new transfer |
|---|---:|---:|---:|
| Total, including index | 150,000,000 | 7,432,416 | 142,567,584 |
| ZIP-index phase | 16,000,000 | 7,432,416 | 8,567,584 |

Use a distinct private attempt folder; never overwrite or treat the incomplete old index as verified data. Revalidate the same archive total, ETag and modification time before reading new bytes. Any transport, identity, mapping, CRC, decode or supervision failure ends the recovery without another repair cycle or replacement frames. The new absolute deadline, source hash and remaining budgets would be recorded only after explicit authorization. If the image route remains unsupported, report that limitation rather than extend this into infrastructure work. G0 remains pending.
