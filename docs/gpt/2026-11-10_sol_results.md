# Frozen-model transfer pilot

**GPT Sol, 2026-11-10. Failed exploratory attempt; G0 pending.** Real-data YOLO11s inference reached the first native batch, then aborted on a nonpositive-extent output box. No complete policy predictions were retained, so recall, FPPI, ceilings and H1 are unavailable. Both owned sessions were stopped after evidence retrieval; final server state has zero active assignments. Displayed balance decreased by 0.31 CU. No YOLO26 inference, training, push, PR or merge occurred.

I want to distinguish absent native candidates from operating-point losses using a small fixed panel. GPT Sol executed this attempt and interpreted its failure; GPT Astra proposed H1. This attempt supplies a runtime/geometry failure and annotation counts, not a detector-performance result, primary BDD experiment, training qualification, complete calibrated bridge or independence claim.

## Frozen launch record (before allocation)

- Base `6847916241d7a08444bdf4313bb7703c9e112ebd`; seed `sol-transfer-pilot-2026-11-10-v1`. Ascending SHA256 of `seed + newline + native file_name` selects 256 COCO source-selection and the next 256 disjoint COCO reference images. The available smoke manifest excludes 128 distinct train/evaluation IDs (evaluation images are included in that training pool). No label-based rescue, scene audit, target selection or endpoint search. COCO is not verified clear/day, and pretrained checkpoint exposure remains possible.
- ACDC: first 32 adverse val filenames per condition by the same hash, with all available annotated normal references: fog 16, night 12, rain 15, snow 17. All selected images, including zero-human images, remain. Paired adverse subsets are reported separately from all adverse images. Sequence/view dependencies remain; no IID intervals, precision guarantee or causal weather claim.
- [Frozen config](../../configs/research/transfer_pilot_20261110.json): native YOLO11s first; floor .0001/cap3000, same floor/caps100 and300, floor .01/cap3000. Person-only native class filter; no all-class competition claim. COCO person and ACDC person+rider are explicitly relabelled human, not pedestrian. Native predict geometry is converted xyxy→xywh without additional repair/clipping; `allow_outside`; provisional same-category crowd IoA .50, greedy matching IoU .50. Existing stdlib converters/evaluator are reused; ACDC masks are not reaudited.
- **Exact planning allowance:** 700 unique images × 4 direct policies = 2,800 YOLO11s forward images. Allow 30 minutes including upload/install/inference/retrieval: at the last observed L4 quote 1.94 CU/hour, `30/60*1.94 = 0.9700 CU`. This is an allowance, not measured throughput. Conditional YOLO26 O2O/O2M adds 5,600 forward images and 25 minutes (`0.808333 CU`); combined 55 minutes/`1.778333 CU`. Admission must verify actual rate ≤6 CU/hour. Absolute outer stop is 90 minutes/≤10 existing CU; at 1.94, 90 minutes would be 2.91 CU. No top-up, subscription change, training or local GPU use. Balance before allocation: 299.97 CU, rate 0, active assignments 0.
- Sole operator GPT Sol; isolated state and raw packet/results under ignored `C:/Users/Advait/autonomous-sys-research/outputs/colab/empirical_20261110/`. Retrieve evidence and stop only the named owned session in a `finally` block, then verify no owned assignment remains. One concrete runtime correction permitted; repeated infrastructure failure ends allocation.

## Actual peer exchange before inference

Sol asked Astra for one falsifiable hypothesis and a kill criterion, including the possibility that .90/.95 are infeasible. Astra proposed H1 at rho=.90: for tighter policy q versus maximal p, `B_c=R_q,c(t_q)-R_q,c(t_p)`, `D_c=R_q,c(t_p)-R_p,c(t_p)`, and `abs(B_night)>abs(D_night)` plus `abs(B_night)>abs(B_COCOref)`. Absolute recall/FPPI/M and paired normal responses are required controls. No feasible contrast satisfying both kills H1 on this finite panel; infeasible .90 means untestable, without substituting .80. Sol explicitly accepted before model inference and will preserve private per-image outputs.

Astra clarified that person-first filtering removes direct output-class competition, not duplicates/background or upstream argmax loss. Under prefix-preserving semantics the floor-only arm is a feasibility/null control: a still-feasible observed-boundary threshold cannot move. A few source images could explain a target response; ordinary finite-source instability remains an alternative. No new allocation or source block is authorized by that exchange.

## Results

The first owned L4 allocation (22:35:33–22:35:58 UTC) failed on a single 490,741,760-byte packet upload with `ConnectionResetError(10054)`, before setup or inference. Empty remote evidence and session history were retrieved; teardown succeeded and server sessions/usage showed no active assignments. This is an infrastructure failure, not a model result. The one permitted correction uploads the unchanged selected packet as 118 pieces of at most 4 MiB and verifies its SHA256 after reconstruction. This conservative chunk size replaces the initially contemplated 32 MiB size before any corrective launch. Allow five additional minutes (`5/60*1.94 = 0.161667 CU`), within the original outer deadline measured from the first allocation. A second infrastructure failure ends allocation.

The corrective session reconstructed and hash-verified the packet and installed Ultralytics successfully. The remote process then returned 1 while `colab exec` returned 0, confirming why artifact status must govern success. Downloaded `yolo11s_status.json` reports `ERROR`, `coverage={}`, `expected_images=700` and `AssertionError('nonpositive native box; no repair allowed')`. The traceback is inside the first maximal-policy batch, after native prediction and the output-count check. The eight-image batch therefore reached native outputs, but **zero complete 700-image policy artifacts** exist; a precise completed-image/invalid-box count cannot be reconstructed.

The checked code rejects `x2<=x1` or `y2<=y1`; it did not discard or repair the box. This is a geometry compatibility failure, not source infeasibility, low recall, a measured ceiling of zero, NaN evidence or evidence for/against H1. The captured pinned predictor calls native `scale_boxes` before returning Results; native boundary clipping is one possible explanation, but the offending coordinates were not retained and its cause is unverified.

**Evidence gap attributable to GPT Sol:** the initial script persisted predictions only after a complete policy, so the failing raw batch was lost when its subprocess exited. The packet, inspected image manifest, annotations, source code, install status, traceback, session history and teardown logs are retained privately. A small post-run capture change now writes native batches before geometry validation and retains validated partial rows on failure. That change has **not** been GPU-executed or qualified, and no further allocation was made. The shared evaluator and its positive-area contract were not changed. A future run requires an explicit geometry-accounting decision; this note does not silently adopt dropping, clipping, epsilon boxes or a new evaluator.

| YOLO11s native policy | Valid complete policy coverage | Outcome at all .80/.90/.95 objectives |
|---|---:|---|
| floor .0001, cap 3000 | 0/700 | Invalid partial; threshold, recall, FPPI, M, W, B and D unavailable |
| floor .0001, cap 100 | 0/700 | Not run |
| floor .0001, cap 300 | 0/700 | Not run |
| floor .01, cap 3000 | 0/700 | Not run |

Every H1 contrast is **untestable due to missing valid coverage**, a different reason from source recall infeasibility. No lower-recall substitution, all-output fallback, policy selection or target rescue occurred. YOLO26 O2O/O2M were not admitted after the failure. No research figure is justified by these missing performance data.

## Actual panel composition

These are annotation counts from the fixed private manifest, not evaluated performance. Empty means no eligible noncrowd human; all empty images remain. ACDC person/rider counts describe native GT before explicit human merging.

| Panel | Images | Eligible GT | Empty-human images | Human crowd regions | Person/rider GT |
|---|---:|---:|---:|---:|---:|
| COCO selection | 256 | 579 | 116 | 14 | 579/0 |
| COCO reference | 256 | 528 | 120 | 12 | 528/0 |
| ACDC fog | 32 | 27 | 16 | 0 | 22/5 |
| ACDC night | 32 | 77 | 13 | 1 | 68/9 |
| ACDC rain | 32 | 40 | 22 | 1 | 39/1 |
| ACDC snow | 32 | 72 | 11 | 4 | 72/0 |

| Paired condition | Pairs | Adverse GT / empty images | Normal GT / empty images |
|---|---:|---:|---:|
| Fog | 16 | 13 / 8 | 32 / 6 |
| Night | 12 | 25 / 5 | 35 / 3 |
| Rain | 15 | 22 / 12 | 27 / 5 |
| Snow | 17 | 37 / 6 | 60 / 4 |

## Provenance, resources and validation

- Actual runtime: NVIDIA L4, 23,659,151,360 bytes device memory; Python 3.13.16, torch `2.14.1+cu130`, Ultralytics `8.4.197`. The failed model process lasted 9.267 seconds including initialization and first batch; no valid image throughput, peak-memory or speed comparison is available.
- YOLO11s checkpoint SHA256 `85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5`; expected YOLO26s SHA256 `646f8bc3fe0a656803d95c294f7852321748cb29d13466a1af8862e2db384a1b`. Both local checkpoint pickle metadata identify native class 0 as person, checked without loading torch or querying local CUDA. They are pretrained checkpoints, not BDD fine-tuned artifacts. Only YOLO11s was inferred. Runtime head before fusion: `Detect`, `end2end=False`, no O2O heads; O2M cv2/cv3 present.
- The pinned source also qualifies the person-filter description: YOLO26 O2O head-level all-class top-k precedes the downstream person filter, with an upstream head budget at least 300. That branch was not executed here. No head availability or isolated class-competition/NMS result is claimed. The actual classes argument stays `[0]`.
- Packet SHA256 `d2cd1a7f669c401417f06e9b712dbc32b20b2f8b54055b18a1b9adcc8e938a24`; private manifest SHA256 `21c5a2c738a22c5e6e6bff535c1122a8fdc3cbac69216ce9e9ba07c3e3b1156a`; frozen packet config SHA256 `704dbfbba0085e6ca69632c584820b246fcbb017f7669079e8993220009a5bf1`. Sent script SHA256 `46017cd38f12059b21d780e94b601f678dbea0eae928c18e8818adbcabdd73e1`; its inference-function SHA256 `3c33338c98a81a466d9df7767e0fad73d84a8d765cb63b72174c615ccad82085`. The final committed script includes the explicitly unrun capture correction and aggregate failure handling.
- Sole-operator correction: first allocation 22:35:33 UTC; corrective allocation 22:37:08 UTC; final evidence retrieval/teardown verification finished 22:48:16 UTC. Outer elapsed **763.027701 seconds (12.72 minutes)**. Both admissions measured 1.94 CU/hour. Final usage: 299.66 CU, 0 CU/hour, 0 active assignments; initial displayed balance 299.97 CU. The 0.31 CU display difference is not an itemized final billing receipt. No other session was stopped. The five-minute extra-upload allowance underestimated transfer overhead; the original outer limit was respected.
- One tiny synthetic geometry/crowd example passed: native outside-image coordinates retained, one TP, one reusable crowd ignore, zero FP, two images including an empty image. This validates the intended positive-area conversion/ignore path, not low-floor native geometry or research quality. No full regression suite, training test or local GPU call was run. Final CPU aggregation was checked against the downloaded error status; missing metrics remain unavailable.
- [Aggregate JSON](2026-11-10_sol_aggregate.json) contains panel counts, explicit unavailable objectives/H1 contrasts, runtime and public hashes. Raw ACDC images/annotations, inspected IDs, packet and logs remain ignored/private under the launch directory; no raw boxes or identities are published.

## Disposition

The scientific question remains unanswered. This failed attempt neither confirms nor kills source-boundary amplification, and cannot distinguish absent candidates from operating-point losses. The bounded stopping rule ended allocation after the upload correction and geometry failure. No peer agreement is inferred beyond the recorded exchange; Astra had finished before this failure and was not restarted. The coordinator handles any separately authorized continuation, focused review and publication. My explicit approval remains required for merges.
