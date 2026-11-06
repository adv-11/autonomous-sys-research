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
