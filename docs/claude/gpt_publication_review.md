# GPT publication review of Claude's Phase 0 revision

**Reviewer:** GPT (gpt-6.1-sol), 2026-11-03. This is GPT's final bounded cross-review under [CONTRIBUTING.md §5](../../CONTRIBUTING.md), performed directly without delegates. It records an AI review, not my GitHub approval or permission to merge.

**Exact reviewed Claude SHA:** `5cec0a254c448625bab1abc352e356305194533b` (reported original: `e460cf6830cff370c9086b4a97accbef613e1291`). GPT reviewed its six-file revision diff and current Claude documents, including the unchanged [coordinator agenda](discussion_agenda.md). The comparison was the actual GPT response `80519fcee2c99d134a5a6a89559f743772c2ffb8`, read with `git show`, including its protocol and source evidence addendum. GPT also read the clarification diff `b9a24ba3f27a72e2608f33fee7f7665a9bd7ec43`; those already completed GPT-side fixes are context, not new review requests.

**Recommendation: approve with minor corrections for a Phase 0 PR.** No substantive publication blocker remains. The actual [Claude reply](discussion_with_gpt.md) answers GPT's requested corrections, preserves changed positions and distinguishes proposal agreement from empirical validation. The two wording corrections below can be applied directly during integration; no replacement review or review of this record is requested. **G0 remains pending.**

## Requested correction disposition

| Requested correction | Evidence in the Claude revision | Disposition |
|---|---|---|
| O3: upstream rank invariance, equivariant boundaries, isotonic plateaus | [Methodology O3](methodology_objections.md#o3-b-for-rq3-a-global-strictly-increasing-recalibration-with-equivariant-threshold-reselection-cannot-change-recall-transfer) states fixed geometry/labels/ties, transformed cutoffs and one global strict map; corrects top-k/hard-NMS invariance; gives the midpoint counterexample and distinct-score merging. Fixed-probability and adaptation arms have separate baselines. | Resolved at proposal level. |
| O4: feasibility versus margin; signed versus positive gaps; targets | [Methodology O4](methodology_objections.md#o4-b-preregister-feasibility-headroom-and-the-gap-decompositions-separately) and [SVG](protocol_splits.svg) agree on 0.80/0.90/0.95, `M_S < ρ`, descriptive low headroom, undefined empty populations, `S = U + V`, `D = U + T`, and the signed held-out `L` identity. Clear loss uses independent clear-test recall. | Resolved; no empirical feasibility implied. |
| Independent fit, selection and test groups; selection uncertainty | SVG assigns training, development, calibrator-fit, threshold-selection and clear-test roles separately; related recordings stay together. ACDC adaptation has distinct fit/selection groups and held-out val. Cross-fitting requires fold-specific fitting/selection and out-of-fold tests; uncertainty repeats the procedure. Claude's reply adopts GPT's paired group weights and selection-aware uncertainty. | Resolved as a design; manifests, group counts and coverage remain prerequisites. |
| Population policy and invalid/void distinction | Methodology O1–O2 retain BDD-fine-tuned pedestrian primary and rider supervision, separate union panels with their own thresholds/denominators, and an ACDC `person` primary-model panel. Official instances replace semantic components. Invalid labels remain eligible; void/crowd/other-person handling is explicitly provisional. | Resolved as a proposal; evaluator/ontology audit remains pending. |
| Causal wording and matched ACDC population | Methodology O6–O7 and novelty table use a conditional same-checkpoint head/pipeline contrast; neither NMS nor assignment is isolated. Matched reference/adverse views use the same annotated subset and weights; all-adverse results stay separate. Scene correspondence supplies no pedestrian pairing or causal weather intervention. | Resolved. Detached-feature interpretation is conditional on checkpoint training provenance. |
| RQ2 information regimes and dependence | Methodology O5 separates source raw TP-ECE, unlabelled-target score statistics, and target-labelled diagnostics. Fitted-map ECE needs independent/out-of-fold groups. The small model panel supports description; OCE shares missed-object information with recall. Tuning and precision pilots exclude test groups. | Resolved; no advance-warning or inferential guarantee claimed. |
| RQ0 proxy, novelty and evidence precision | Methodology O8, novelty audit and source addendum qualify the literal-rule proxy, missing provenance, code search, bounded novelty search, author-reported venue evidence and anomalous dates. Twelve full PDF hashes identify Claude's reported inspected bytes; code is pinned, not executed. GPT-only checks are explicitly attributed. | Substantively resolved; two minor wording remnants below. |

## Findings for direct integration

1. **P3 / minor — unspecified matching is summarized as confirmed unmatched matching.** `docs/claude/phase0_recommendation.md:10` says the weather paper “uses an unmatched” correctness rule. The source ledger at `docs/claude/source_audit.md:39` instead establishes that one-to-one matching and duplicate handling are **not stated**; O8 correctly treats unmatched evaluation as a literal-rule proxy. Replace the summary phrase with “states class match and IoU > 0.5, without specifying one-to-one matching or duplicate handling.” This keeps the proposed mechanism hypothetical. No additional source search is needed.

2. **P3 / minor — template appearance does not establish publication status.** `docs/claude/source_audit.md:20`, survey row 1, infers “so not yet published” from placeholder manuscript dates. Retain the observed template evidence and replace that conclusion with “publication/acceptance status not verified from the inspected sources.” This is a qualification of existing evidence, not a request to reopen the survey.

Both findings remain open in the exact reviewed SHA. This review changes only this record and does not edit Claude's attributed prose. There are no major or substantive blocking findings.

## Explicit prerequisites that may remain pending

Publication can proceed with these disclosed G0 or affected-run prerequisites unresolved:

- Lawful data access, exact archive versions/hashes, instance/reference/correspondence artifacts and annotation/evaluator audits, including class extents, crowd/void/invalid policies and eligibility.
- Independent recording/route groups, role manifests, image/object/group counts, matched-subset weights and non-test precision pilots; sparse strata may remain descriptive.
- Source-selection candidate-ceiling feasibility, floor/cap diagnostics and frozen policy choices. A low-headroom flag or algebraic identity is not a population guarantee.
- Exact checkpoint hashes, both YOLO26 branches before fusion, training-path provenance, explicit inference settings and separate-copy runtime checks; an unavailable contrast must be reported as unavailable.
- Complete OS/driver/PyTorch/torchvision/CUDA pins and actual RTX 5060 forward/backward/evaluator smoke tests with memory logs.
- A frozen preregistered protocol, meaningful implementation checks and simulation coverage checks before nominal bootstrap-interval claims. Mathematical illustrations do not validate these.

These are prerequisites to gate passage or affected claims, not blockers to publishing an honest Phase 0 proposal. The [recommendation](phase0_recommendation.md) and diagram explicitly label the design as conceptual, with no measured results. Project-goal and approval prose uses first person; AI source checks remain attributed. Historical initial questions are labelled as preserved history.

## Validation and limits

GPT checked all 21 local Markdown links/anchors in the six pre-existing Claude Markdown files: no failures. `protocol_splits.svg` parses as XML; its three IDs are unique and marker/ARIA references resolve. All twelve full source hashes have valid 64-character hexadecimal syntax; GPT did not rehash the external scratch PDFs. Links added by this record were also checked before commit. External source availability and the literature survey were not re-audited. No browser rendering, empirical experiment or fresh algebra suite was necessary: the displayed identities and counterexample are consistent on inspection, and prior toy checks remain explicitly attributed to their authors.

**Final disposition:** publish the Phase 0 proposal after the two direct wording corrections, retaining pending G0 and explicit GitHub merge approval. Approval to publish the PR is not approval to merge. No push, PR, merge, dataset/weight download, paid compute or package installation occurred in this review.
