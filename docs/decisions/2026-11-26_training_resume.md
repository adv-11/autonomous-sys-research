# RT-DETR retry and two additional training seeds

I authorized resuming RT-DETR and two more seeds on 2026-11-26. I also explicitly
raised the project-owned compute check-in from 100 to **140 CU** after the
coordinator corrected the seed estimate: the previous 1280-pixel, 100-epoch run
took about 20.7 CU for training, so two matching repeats are about 41 CU before
additional overhead. Earlier 6-10 CU estimates were too low for that exact recipe.

## Scope and evidence

- Retry the frozen official RT-DETRv2 R18 clear-day baseline and optional
  ordinary day/night adaptation from the paused branch at `2756dbd`. Preserve
  its scientific contract unless an operational amendment is needed before
  results. Record amendments rather than silently changing the comparison.
- Add **two YOLO11s 1280-pixel seeds, 2 and 3**, preserving B/B2's 100-epoch
  recipe, data, initialization, final-EMA checkpoint rule and evaluation.
  Do not shorten their training and label them equivalent seed replicates.
- RT-DETR has priority. One Claude Opus operator at medium effort owns all
  allocations sequentially, with at most one project runtime at a time.
- The full frozen NightOwls cohort remains primary, as I requested; retain
  the predeclared dominant-recording exclusion and its uncertainty alongside
  it. My preference for the higher pooled number does not authorize selecting
  a new cohort, dropping caveats or calling the effect causal.
- Existing public Hugging Face download needs no token. An offered token is
  not used or stored. Authenticated access would not by itself establish the
  mirror publisher's identity or revised-label provenance.

## Compute limits

Reported historical project-owned spend is 60.9 CU, plus a conservative 0.3 CU
charged to the stopped RT-DETR attempts. These are saved-ledger estimates, not
a reconciliation of account balance. Other user activity and the unexplained
historical balance change remain separate.

| Work | Remaining all-inclusive cap |
|---|---:|
| Original RT-DETR stage | 24.7 CU, 11.862 owned allocated hours |
| Two additional YOLO seeds, combined | 45 CU, at most 22.5 CU per seed |
| Newly available work in total | 69.7 CU |

The 140-CU project check-in is binding. No new runtime may cost above 3 CU/h.
Use at most 12 allocated hours per new seed session and charge setup, data
retrieval, training, inference, idle time, artifact retrieval and teardown.
After the actual own rate is verified, watchdog deadlines can use that rate
within the unchanged CU/hour caps; establish a conservative guard before
allocation. Record the exact runtime identity, rate, deadline and teardown.
Never stop or reuse an unrelated user runtime. Parallel account balance deltas
are not proof of this project's costs.

At most two new allocation attempts for this recovery batch; L4 preferred.
RT-DETR may use a T4 only under a committed operational amendment and the
existing at-most-1-CU throughput pilot demonstrating a meaningful baseline
fits. No A100 or other rate-cap exception is granted. Do not alter the exact
YOLO seed recipe to fit different hardware or costs. If resources do not fit,
preserve the completed evidence and report the remaining work rather than
repeat allocation or performance loops.

No automatic retry schedule is authorized. Dataset retrieval stays directly
inside Colab, no local GPU. Research branches, independent review, my explicit
merge approval and the pending G0 gate still apply. The first next milestone
is a real RT-DETR training/throughput result, then seed-replication evidence
with measured curves, recall/false-positive tradeoffs and uncertainty limits.
