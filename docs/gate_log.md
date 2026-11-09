# Research gate log

## 2026-11-03 — Initialization and scope correction

- Evidence: the workspace contained only `RESEARCH_PLAN.md`; I authorized GitHub setup and independent GPT/Claude branches.
- Scope: personal PhD-depth research, no course deadlines or professor approval requirement.
- Environment observed: Windows; RTX 5060 Laptop GPU, 8,151 MiB; NVIDIA driver 616.64; Python 3.11 available through `uv`.
- Decision: begin Phase 0 source verification and protocol work. Retain the original cloud budget ceiling pending clarification.
- Gate G0: **pending**. No datasets, slice counts, model train/evaluation smoke tests, or reproduction protocol have yet been verified.

## 2026-11-03 — Collaboration and approval clarification

- I requested two research subagents, GPT and Claude, with a genuine exchange before PR creation.
- PRs must provide a compact summary, sufficient supporting detail, and relevant images or SVG diagrams for architecture/protocol decisions.
- I'll review on GitHub. Research merges await my explicit approval and occur sequentially, GPT then Claude.
- Initial repository setup may be pushed now; no research PR is ready yet.

## 2026-11-03 — Public repository and writing voice

- I want the repository to be public and the project prose to read in my voice.
- Use first person for my goals and decisions, with neutral technical prose and explicit GPT/Claude attribution for AI research.
- These editorial changes do not verify any research claim or advance G0.

## 2026-11-03 — Phase 0 research and peer discussion

- GPT and Claude completed independent source audits, then exchanged committed questions and answers before PR creation. The attributed exchange and corrections are linked from `docs/gpt/review_resolution.md`; Claude's reply and GPT's final review are on `claude-research`.
- Proposal-level decisions: BDD pedestrian primary, separate merged-human panels; independent calibrator-fit/threshold-selection/test groups; explicit recall feasibility and candidate ceilings; conditional same-checkpoint YOLO26 head/pipeline comparison; descriptive initial RQ2 analysis.
- Broad novelty and isolated architectural-cause claims are withdrawn. The reproduction target remains a sensitivity audit with unresolved source provenance.
- Checks cover document links, SVG structure/rendering and attributed algebraic illustrations. They do not establish empirical results, evaluator correctness or bootstrap coverage.
- G0 remains **pending**. My review and explicit approval are required before each research PR merges, GPT first and Claude second.

## 2026-11-05 — Merged initial research; implementation resumes

- I merged both initial PRs on GitHub and authorized continuing the work. The host records PR #2 at `93937a89ae140cede3312c61d35c70d448680135`, followed by PR #1 at `a23aad138fe6117431277ab8157492b3ca5fa04e`. Both contributions are now present on `main`.
- I want the agents to prompt each other directly. The new peer protocol supports focused live exchanges; the coordinator starts any later formal review tasks without requiring me to relay messages.
- The repository's `data/` contains only its README. External dataset locations have not been supplied. No datasets or annotations are claimed to have been acquired.
- Next work: dependency-light reference metrics and dataset-preflight/conversion tooling, with meaningful synthetic tests and a shared provisional JSON contract.
- G0 remains pending. No paid compute, training, checkpoint/GPU validation or real dataset evaluation is authorized by an implementation test passing.

### Local asset discovery later in the same session

- My `det-eval-2d` folder contains COCO val2017, KITTI images/labels, cached predictions, detector weights and a CUDA-capable Python environment. The verified inventory, hashes, provenance and reuse limits are in `docs/local_assets.md`.
- The earlier “no datasets in this repository” observation remains correct, but data tooling can now inspect these external assets without another download. No BDD100K/ACDC assets were found there.
- Use existing data and caches for development and diagnostic replay. Prior KITTI results are not fresh confirmatory findings for this project, and cached outputs are score/cap censored.
- G0 remains pending; importing torch and detecting CUDA does not replace the planned per-model forward/backward/evaluation checks.

### Reference-tooling milestone

- GPT implemented deterministic reference evaluation and Claude implemented data/cache preflight. Their actual direct interface prompts and decisions are recorded in the implementation notes; I did not need to relay prompts.
- Separate formal cross-reviews followed automatically. The coordinator fixed the reported safeguards and converter defects directly, preserving the reviews and resolution records.
- The evaluator branch passes 32 tests; the combined adapter/evaluator branch passes 67 on Python 3.11 and 3.12. Real local COCO/KITTI conversions pass direct dictionary integration under explicit diagnostic policies. Unknown-group held-out checks fail as intended.
- These are implementation and development-asset checks. No BDD/ACDC data, verified condition/group manifests, model-specific training/evaluation smoke tests or new weather-transfer findings are claimed. G0 stays pending.

## 2026-11-06 — Missing dataset acquisition

- I merged the tooling PRs and authorized downloading the missing datasets and continuing the research. PR #3 merged into `main`; PR #4 merged into `gpt-research`, so the approved adapter contribution still needs a main-targeted PR. No research merge was performed by an AI.
- GPT acquired the seven relevant ACDC archives directly from ETH. All seven match the official MD5 values, have recorded SHA-256 hashes, pass full ZIP CRC checks and are extracted. The [archive manifest](datasets/acdc_archive_manifest.json) records exact identities and verification. Raw and converted data remain outside Git.
- The ACDC image ZIP contains 8,012 PNG images. GPT checked all 3,009 image paths referenced by detection annotations and their PNG dimensions: no missing images or dimension mismatches. This does not verify visual viewpoint correspondence or group independence.
- Claude implemented an ACDC adapter and inspected actual annotations. The GPT coordinator independently confirmed train/val sequence-token overlap; [the evidence](datasets/acdc_split_overlap_check.json) distinguishes this check from the GPT BDD subagent. The adaptation allocation is on hold pending a defensible group-disjoint design; official split names are insufficient.
- BDD image, legacy-label and Info candidate archives are complete and pass ZIP CRC checks, but their MD5 values differ from the published archive values. The live Detection 2020 button supplies images rather than JSON; revised labels remain unacquired. Legacy labels are not substituted. Info native-ID inspection finds a train/val overlap, with full-parse versus prefix-only denominators explicitly recorded; no independent group assignments are claimed.
- G0 remains **pending**. Acquisition and annotation inspection are not detector results, verified independent splits, pinned model environments or the required forward/backward/evaluation smoke tests.

### Acquisition merged; ACDC adapter follows

- I merged [PR #5](https://github.com/adv-11/autonomous-sys-research/pull/5) into `main` at `2d93bbd23d16f2958b9bef51c56717ac666052e3` on 2026-11-06. This also integrates the adapter contribution previously approved in PR #4.
- The coordinator updated `claude-research` against that merged `main` for the next sequential PR. The ACDC change includes Claude's implementation, actual peer discussion, GPT's separate formal review and the direct resolution of both P2 findings. No new implementation was added during this synchronization.
- Validation covers 108 combined synthetic tests on Python 3.11/3.12, all 24,771 real detection mask areas/bboxes, and the revised decoder on all 2,006 adverse invalid masks. These checks do not select an experimental allocation or measure detector performance.
- G0 remains pending. The next research work must address the remaining data/grouping and model feasibility prerequisites; it should not repeat completed parser work.

## 2026-11-06 — Grouping and model-feasibility prerequisites (after PR #6)

- I merged [PR #6](https://github.com/adv-11/autonomous-sys-research/pull/6) at `e5a7e92` and asked the work to continue. The Claude coordinator started two bounded G0-prerequisite tasks: ACDC dependency grouping (GPT) and RTX 5060 model smoke tests (Claude).
- The GPT task stopped partway because its Codex workspace ran out of credits. Its draft was uncommitted and unreviewed. I chose to reassign the grouping to Claude. Claude verified the draft independently and completed it; it is attributed as an incomplete GPT draft completed by Claude, not as GPT-reviewed or GPT-agreed work.
- **ACDC grouping ([note](claude/acdc_grouping.md)):** linking whole GoPro recordings, adverse↔reference pairs and byte-identical reference images gives 24 dependency groups, 18 with labelled adverse images (6 fog, 4 night, 4 rain, 6 snow). The coordinator independently reproduced the 12 byte-identical reference sets, two of which cross conditions. The proposed group-disjoint allocation leaves only 1–2 held-out groups per condition and gives **insufficient support for confirmatory ~5 pp precision**: fog and night each have a single held-out group. GPT's cross-review requested that this be stated as a conservative design decision rather than a proved impossibility. Claude recommends ACDC as a source-only descriptive panel, with any adaptation arm only as exploratory leave-one-group-out cross-fitting. This is a proposal awaiting GPT review and my decision.
- **Model feasibility ([note](claude/model_feasibility_smoke.md)):** YOLO11s, YOLO26s (O2O, explicit `nms=False`) and RT-DETRv2-S/R18 (pinned `df2a96c`) each completed 20 optimizer iterations with finite losses and an end-to-end raw-candidate export plus evaluator run on 50 COCO val2017 images. Peak reserved VRAM was 6.25, 7.36 and 6.45 GiB at batches 24, 24 and 16. Checkpoint hashes and environment pins are recorded. AMP skipped 4–6 updates per run. Windows silently spills beyond 8 GB instead of raising OOM, so batch selection uses a 7.5 GiB reserved-memory limit. The 300-candidate cap censors all three pipelines. DEIM-D-FINE-S was not tested.
- No detector ran on ACDC or BDD. These are mechanical checks on development assets, not performance results. 143 tests pass locally.
- G0 remains **pending**: revised BDD Detection 2020 labels are unacquired; the ACDC allocation and its support verdict await my decision; candidate floors/caps, box clipping policy and the training-budget step definition remain open; wide driving frames and BDD class heads are untested.

### GPT cross-review resolved

- GPT (`gpt-6.1-sol`) reviewed both contributions after Codex usage returned: accept with fixes, with 0 P1, 1 P2 and 2 P3 findings. It independently recomputed every grouping count and hash from the full image tree, and checked the smoke values against retained logs and pinned source code. The coordinator fixed all three findings; see the [resolution](reviews/2026-11-08_grouping_smoke_resolution.md).
- The ACDC verdict is now *insufficient support for confirmatory ~5 pp precision*, a conservative design decision rather than a proved impossibility. My decision on the source-only descriptive panel and the exploratory cross-fitting alternative is still required. G0 remains pending.
