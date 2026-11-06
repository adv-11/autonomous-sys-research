# Coordinator task-drift reports

I want periodic checks for drift, unsupported claims, excessive scope and stalled or repetitive work. GPT coordinator assessments below use actual task artifacts and review evidence; they are not claims about a model's intent. Checks run at meaningful milestones and during longer active work under [the collaboration rules](../../CONTRIBUTING.md#coordinator-drift-checks).

## 2026-11-06 — Acquisition milestone

**Overall: amber, corrected.** The completed tasks stayed within acquisition/preflight scope and did not run detector experiments, spend paid compute, substitute legacy GT for Detection 2020 or declare G0 passed. The principal efficiency risk was letting bespoke parser validation delay the research milestone. All acquisition and review delegates have finished; none is currently stalled in an active task.

| Work | Evidence and finding | Action |
|---|---|---|
| GPT BDD acquisition | The [Claude review](../reviews/2026-11-06_bdd_acquisition_review.md) independently reproduced archive hashes and metadata counts, but found three double-counted full-parse documents. Revised labels remain unavailable through the checked routes. | Corrected distinct counts and attribution; retained explicit release limits. Stop additional endpoint probing for this milestone. |
| Claude ACDC adapter | The [GPT review on the Claude research branch](https://github.com/adv-11/autonomous-sys-research/blob/claude-research/docs/reviews/2026-11-06_acdc_adapter_review.md) supported the real annotation counts but found malformed-input and PNG defects. A mistaken RLE representation claim was explicitly retracted in the peer exchange. | Fixed the defects directly; 108 combined tests pass on 3.11/3.12 and all 2,006 real adverse masks pass the revised decoder. No further parser feature or speed work for this milestone. |
| Review and verification | One formal cross-review per contribution; coordinator fixes rather than serial re-review tasks. The full mask pass was repeated after the decoder changed. | The repeat addressed a concrete correctness change. Stop repeating passed checks without a new change or concern. |
| Coordinator focus | Acquisition and tooling do not answer the threshold-transfer question. BDD release identity/revised labels and defensible group allocation remain the research bottlenecks. | Publish the bounded acquisition/preflight PR, then the ACDC PR sequentially. Next research work must resolve a prerequisite or produce a justified detector smoke test, rather than accumulate infrastructure. |

**Unsupported-claim assessment:** the reviews found concrete counting and parser errors, not evidence of fabricated detector results. Archive/release ambiguity, prefix-only JSON inspection and unverified grouping are documented as limits. No unqualified claim that every statement is hallucination-free is made.

**Next checkpoint:** before publication, confirm review corrections and diff scope; after my merge, reassess the next experiment's data, grouping and feasibility requirements. No additional agent task is needed just to produce another status report.

**Requested steering policy:** the coordinator will use [evidence-based corrective prompts](peer_protocol.md#coordinator-corrective-prompts), with a narrowed action, bounded verification and explicit stop condition, when a check finds a problem. There are no active delegates at this checkpoint, so no new corrective exchange is claimed. During the BDD task, the actual coordinator prompt already required explicit malformed-file denominators, null groups until justified, no legacy-GT substitution and completion of the current inventory without more acquisition; the task returned those limitations. The next report will distinguish the prompt sent from the response and demonstrated outcome.
