# GPT cross-review: ACDC grouping and RTX 5060 smoke

**Reviewer:** GPT, `gpt-6.1-sol`, high reasoning effort, 2026-11-08. This is a separate formal review of Claude-authored work, not a continuation or approval of the interrupted GPT draft.

**Reviewed:** `e5a7e92..5b97242`, specifically grouping `9506b11`, smoke `16bd343`, and the milestone records in `5b97242`. Review checkout: `d4b5fe3`, branch `t3/review-grouping-smoke`. The subsequent merge changes only the README relative to `5b97242` and is outside the substantive review.

**Disposition:** grouping **accept with fixes** (F1, F2); smoke **accept with fixes** (F3, a documentation correction). No P1 findings; **one P2 and two P3 findings**. The counts, dependency blocking, conversion, and recorded mechanical PASS results are supported. The literal statistical impossibility claim needs qualification. **G0 remains pending.** No allocation, protocol amendment, or merge approval is granted by this review.

## Method and limits

Read `AGENTS.md`, `CONTRIBUTING.md`, `docs/PROJECT_CHARTER.md`, `docs/collaboration/peer_protocol.md`, `docs/gpt/protocol.md`, and the final gate/drift-log sections before substantive review. Inspected the complete contribution files, tests, configs, JSON and SVG sources. Both SVGs parse as XML; their conceptual labels and displayed values match the notes. No browser/rendering assessment is claimed.

- **Independent real-data grouping check:** a separate stdlib script traversed and SHA-256-hashed all 8,012 PNGs under `C:/Users/Advait/autonomous-sys-research/data/acdc/extracted/`, built an explicit adjacency graph and traversed its components (rather than calling the reviewed union-find), independently read the four detection/reference JSONs, and recomputed allocations and every aggregate panel. Annotation/README input hashes and the reconstructed full-manifest hash match the committed summary. Chapter continuity, recurring tokens/numbers, session-proxy counts, and duplicate sets also match.
- **Draft provenance:** read the uncommitted module and summary in `t3-db535805` without editing that worktree. The seed, allocation rule, group-ID recipe and inherited implementation structures are present. Running the completed module with byte edges disabled reproduces the draft's panels, totals, input hashes and 6/6/8 + 6 role counts. This is verification now, not evidence that GPT previously agreed.
- **CPU-only smoke audit:** recomputed image selection, training-pool IDs, role splits and all 128 YOLO label files from local COCO annotations; checked all three checkpoint hashes; compared the committed log against retained local run JSONs and six candidate documents under `C:/Users/Advait/ar-work/smoke/`. Validated canonical documents, coverage, candidate/person counts, cap nesting, censoring, and full-population evaluator outputs without invoking a detector. Recomputed finite-loss, skipped-step, memory and timing summaries. Checked environment freeze hashes after normalizing checkout line endings and verified installed Ultralytics/torch/torchvision package versions.
- **Local primary-source inspection:** Ultralytics 8.4.197 in `det-eval-2d/.venv/Lib/site-packages/ultralytics/`; clean RT-DETR checkout at `df2a96c8c3a098567a1149bf0248da6efe6d495d` in `C:/Users/Advait/ar-work/rtdetr-src`. No internet fetch or substitute version was needed.

The independent audit scripts and aggregate outputs remain in ignored `outputs/review_grouping_check.{py,json}` and `outputs/review_smoke_check.{py,json}`. This commit contains the review only. No detector inference, GPU work, installation, download, BDD work, protocol edits, peer messages, push or PR occurred. Hardware measurements are verified against retained evidence, not independently remeasured. Visual correspondence, true trip/route independence, historical execution outside the retained records, and nominal interval coverage remain unverified.

## Findings, ranked

### F1 — P2: an assumed precision illustration is presented as an impossibility bound

**Locations:** `src/threshold_transfer/acdc_grouping.py:235` (`feasibility_verdict`, including its default `minimum=8`); `docs/claude/acdc_grouping.md:60` and `:70`. The stronger verdict is propagated at `docs/claude/acdc_grouping_summary.json:917`, `docs/claude/acdc_grouping.svg:65`, and `docs/gate_log.md:74`.

**Verified evidence:** the code emits `INFEASIBLE_FOR_5PP_HALF_WIDTH` whenever any condition has fewer than eight held-out components, independent of any estimated variance. Eight is a new proposed count floor, not a protocol-derived precision criterion. The note explicitly assumes equally weighted independent group recalls and an unmeasured between-group SD; that t calculation is not a bound for the protocol's object-weighted ratio recall, much less its refitted threshold-selection procedure.

Even within the illustration, `precision_design({'example': 2}, sigmas_pp=(0.5,))` gives **4.49 pp**, while `feasibility_verdict({'example': 2})` still declares infeasibility. Thus the assertion that the design bound “settles the question” is too strong. Also, two unequal groups have a discrete, nonconstant bootstrap distribution: equal-size groups with recalls 90% and 91% yield resampled means 90%, 90.5%, and 91%. One group is degenerate; two groups are extremely inadequate for reliable coverage, but not necessarily degenerate.

**Consequence and requested fix:** retain the practical rejection of this three-role allocation for confirmatory inference: one fog group and one night group cannot estimate between-group uncertainty, and two rain/snow groups provide very weak support. Label this **insufficient support for confirmatory 5 pp precision**, with an explicitly conservative design decision, rather than a proved precision impossibility. Qualify/remove the eight-group rule and correct the bootstrap wording; update the derived note/JSON/SVG/log assertions consistently. Do not replace the missing pilot or coverage validation with another numerical cutoff. No detector pilot or protocol change is requested in this review.

### F2 — P3: observed train/val leakage is overstated as occurring through every edge type

**Location:** `docs/claude/acdc_grouping.md:30`.

**Verified evidence:** all **12** byte-identical sets lie within an official split: **7 train, 1 val, 4 test**. None supplies a train-to-val byte-identity edge. The two cross-condition sets are respectively test/test and train/train. Chapter/recording recurrence does establish official-split leakage, but it does not establish leakage “through every edge type.”

**Requested fix:** attribute observed train/val leakage to the verified chapter/recording overlap and describe byte identity as additional cross-condition dependency evidence. Keep byte links in the policy. The earlier official-split adaptation design remains unsuitable; this correction changes the explanation, not that decision.

### F3 — P3: inference timing boundaries differ from the note

**Locations:** `docs/claude/model_feasibility_smoke.md:97`; `scripts/smoke/ultralytics_smoke.py:184`; contrast `scripts/smoke/rtdetrv2_smoke.py:204` and `:208`.

**Verified evidence:** Ultralytics starts its timer before `model.predict(str(path), ...)`. Its pinned `engine/predictor.py:352` sets up the source and `:376` iterates the loader within that call; `data/loaders.py:499` decodes the image. RT-DETRv2 opens/converts the PIL image before starting its timer. Therefore the statement that inference timing excludes image decoding is false for Ultralytics, and the reported seconds/image have different boundaries.

**Requested fix:** document the actual timing scopes and avoid treating these values as comparable model latency. Preserve the measured numbers. No new inference run is needed to correct this report, and this does not invalidate mechanical PASS.

## Verified grouping results and attribution

All three population totals and all role/condition panels match independently, including crowd and empty definitions:

| Population | Images | Components | Person non-crowd / crowd | Rider non-crowd / crowd | Empty all classes / no non-crowd person |
|---|---:|---:|---:|---:|---:|
| Labelled adverse | 2,006 | 18 | 2,175 / 46 | 273 / 3 | 35 / 1,184 |
| Annotated reference | 1,003 | 18 | 2,597 / 0 | 576 / 0 | 1 / 404 |
| Adverse with annotated reference | 1,003 | 18 | 1,059 / 23 | 124 / 2 | 13 / 578 |

The full tree has 4,006 adverse/reference stems, 60 chapter components, 26 recording families before byte links and 24 components afterward. The labelled condition counts are fog 6, night 4, rain 4, snow 6; these sum above 18 because two components cross conditions. Roles contain 5 fit, 5 selection, 6 held-out, 2 descriptive-only, and 6 unlabelled-only components. Held-out condition counts are 1/1/2/2, with fog only 7 images and 7 non-crowd persons. Descriptive-only contains 449 labelled adverse images. The reconstructed manifest SHA-256 is `04c6a0ad1a805d666a09f5a24d4634b1ba248858749ccaa3e60f4249e794fcf3`.

All duplicates are references; the cross-condition equal-byte file sizes are 2,684,373 and 3,017,555 bytes. Neither member of the fog/snow test pair is annotated; exactly one member of the night/snow train pair is annotated. There are 28 cross-split chapter tokens and 15 cross-split recording numbers. The 27/39 chapter-boundary continuity count and maximum frame index 1061 reproduce. These support conservative dependency blocking; they do not verify physical trips or independence.

Attribution in the module, tests, note, summary, SVG and milestone records is accurate: an incomplete, unreviewed GPT draft was reused and completed by Claude; byte links and the design diagnostics are Claude additions. The note records the interrupted peer exchange, including Claude's corrections, and silence is explicitly not assent; this review did not independently retrieve the message transcripts. Agreement with an old draft sentence is not presented as a subsequent GPT review. This report records GPT's present findings only.

## Answers to Claude's five grouping questions

1. **Byte identity in the main policy:** yes. Exact shared reference bytes are observed dependencies, including fog/snow and night/snow. Block the complete connected components across roles; a sensitivity can quantify the effect of omitting edges but cannot justify a primary independence claim that ignores known reuse.
2. **The 449 descriptive-only images:** retain this treatment in the recorded three-role proposal; retain all 449 in the source-only descriptive panel. Pooling condition-signature strata now would change the inherited rule after inspecting allocation feasibility. It is a post-hoc design amendment, although no detector outcome was inspected and the proposal was not frozen/approved. A separately justified, versioned, approved pre-outcome amendment is possible; silently replacing the rule is not.
3. **Consecutive-GOPR outing links:** keep them as a sensitivity. Gap <=2 reproduces blocks 1/6/2/4 by condition, but adjacent numbers do not identify an outing, date or route. Do not turn a numbering heuristic into verified session metadata. Equally, retaining separate numbers does not certify independence.
4. **Perceptual reference check:** warranted before any adaptation allocation or independence claim. Use a bounded reference-only similarity search with visual confirmation, without detector outcomes; similarity suggests candidate links, not proven shared drives, and a negative result cannot prove independence. This review did not decode RGB or perform that new audit; it is not necessary to retain the descriptive recommendation.
5. **Precision verdict and alternative:** agree with rejecting the current allocation for confirmatory precision and with the source-only descriptive panel, subject to F1's qualification. Exploratory leave-one-component-out cross-fitting is reasonable only with a declared fold algorithm, complete global components held out (including related references/other conditions), and separate inner calibrator-fit and threshold-selection groups. Fitting and selecting on the same remaining labels would not satisfy the protocol. Do not infer nominal coverage or guaranteed 5 pp failure from the illustrative t table.

## Verified smoke results and source checks

All reported table values match the committed JSON and retained raw logs after stated rounding:

| Model | Batch | Attempts / skipped / effective updates | Peak allocated / reserved GiB | Median s/iteration after first | Cap-300 removals vs cap 1000: all / person |
|---|---:|---:|---:|---:|---:|
| YOLO11s | 24 | 20 / 5 / 15 | 5.694 / 6.246 | 0.313649 | 2,178 / 1,096, exact |
| YOLO26s O2O | 24 | 20 / 6 / 14 | 6.829 / 7.363 | 0.583758 | >=4,628 / >=1,810 |
| RT-DETRv2-S/R18 | 16 | 20 / 4 / 16 | 5.695 / 6.445 | 0.681732 | >=35,000 / >=3,361 |

Every retained loss is finite, all final batches satisfy the 7.5 GiB reserved-memory rule, six candidate exports validate, and diagnostic evaluator exit codes are zero with G0 pending. The cap binds on 10/17/50 images at 300 and 0/1/50 at 1000. Counts and exact/lower-bound labels are correct; each cap-300 candidate multiset is contained in its cap-1000 counterpart. Empty-image counts/ranges reproduce. RT-DETRv2 has 868/3,519 outside-image boxes at the two caps, with zero degenerate drops. The three PASS verdicts are valid under their explicit **20 attempted optimizer calls** mechanical definition; they are not 20 successful updates or long-run stability evidence.

**YOLO26 source:** `engine/predictor.py:475` passes `end2end=self.args.nms is False`; `nn/backends/pytorch.py:57` applies it before fusion. `nn/modules/head.py:156`, `:201`, and `:290` implement branch choice and removal of the unused branch. Predictor `:350` sets head k to `max(max_det,300)`; head `:266` first selects anchors by maximum class score, then flattened anchor/class top-k, equivalent in score values to global top-k absent tie ambiguity. `utils/nms.py:76` applies strict `conf > floor` and truncation on O2O output. Thus explicit `nms=False`, default/true O2M+NMS, multilabel O2O output, and separately reloaded copies are correctly described. The retained inspection records both 496,892-parameter branches and the stated modes; checkpoint bytes match the config hash. `nn/tasks.py:651` chooses `E2ELoss` by branch presence; `utils/loss.py:1319` confirms dual losses and the 0.8-to-0.1 O2M schedule. Actual same-checkpoint O2M comparative evaluation remains unbuilt; source inspection does not reconstruct historical training provenance.

**RT-DETRv2 source:** the pinned R18 config selects the declared backbone/three decoder layers and disables multiscale. `src/solver/det_engine.py:23` confirms the AMP model/FP32 criterion, gradient clipping, scaler, EMA and warmup sequence mirrored by the harness. `references/deploy/rtdetrv2_torch.py:44` uses the same deploy, RGB PIL, Resize(640,640), ToTensor and original `[w,h]` path. `src/zoo/rtdetr/rtdetr_postprocessor.py:50` converts normalized cxcywh to original-pixel xyxy, then flattened sigmoid query/class top-k without clipping; deploy returns contiguous labels before category remapping, so the harness's explicit `mscoco_label2category` conversion is correct. Retained checkpoint-load records have no missing, mismatched or unexpected keys. These source checks and checkpoint hashes support the claimed pipeline, without rerunning it.

**Canonical conversion/data scope:** `src/threshold_transfer/smoke.py:199` converts xyxy to `[x,y,width,height]`, preserves scores without rounding, caps globally before category evaluation, and retains explicit image coverage even for empty outputs. Its no-clipping choice is compatible with `schema.py` under explicit `allow_outside`; it is not valid under strict bounds for the RT-DETRv2 outputs. Candidate IDs are unique and tie ordering is deterministic for a fixed native row order. The scalar schema supports recall/FPPI and binary TP-ECE, not full-vector OCE. Configured paths, recomputed IDs, native subsets and labels all resolve to COCO val2017; no retained script/config/input record uses ACDC or BDD images. This is evidence for the recorded COCO-only run, not a forensic proof about every historical process. Windows spilling is a plausible explanation of over-device reserved bytes plus slowdown, rather than a separately instrumented host-memory measurement.

## Answers to smoke open issues

- **Floors/caps:** choose and freeze them on approved development/calibrator-fit groups only, with prespecified sensitivities. Do not tune on the proposed held-out or source-only ACDC reporting panel. A larger cap is not automatically uncensored: RT-DETRv2 still binds at 1000, and its zero exporter floor-removal count says nothing about candidates below the native top-k. Native YOLO floor removal occurs before export and is also not counted by the exporter's `below_floor`. Driving data needs its own authorized development check once groups are approved.
- **Clipping:** retain and declare native geometry for the primary deployment-pipeline comparison (Ultralytics already clips; RT-DETRv2 does not), using `allow_outside` without silent normalization. If common clipping is desired, freeze a separate sensitivity applied before matching, record newly degenerate boxes, and preserve original coordinates. Export cannot undo Ultralytics' upstream clipping. This review does not choose a project-wide protocol amendment.
- **Training budgets:** record attempted calls, successful updates, images/epochs, elapsed time and AMP skips separately. A budget intended to match optimization updates should count successful updates with an attempt/time ceiling; also declare whether LR/EMA schedules advance on attempts or successful updates. The mirrored native RT-DETRv2 loop advances EMA/warmup even on skipped steps. Do not retroactively relabel these 15/14/16-update runs as 20 effective updates or extend the smoke during this review.

## Validation and handoff

Executed the required command using the existing interpreter read-only:

```powershell
$env:PYTHONPATH='src'
& C:/Users/Advait/det-eval-2d/.venv/Scripts/python.exe -m unittest discover -s tests
```

**Result:** 143 tests passed, 5.584 s (Python 3.12.14). Printed preflight errors are expected negative-test cases. These are synthetic implementation tests, distinct from the real-data metadata/hash audit and from the retained GPU measurements. CPU audit assertions also passed. The precision counterexample is algebraic/synthetic and does not estimate ACDC variance or coverage.

No implementation fix was made: F1 requires correcting the scientific status across artifacts, and F2/F3 require documentation corrections. Author tasks have finished, so questions and requested fixes are recorded here for the coordinator rather than sent to inactive peers. No extra delegate or re-check was started. Stop condition: this review is committed locally; no push or PR.
