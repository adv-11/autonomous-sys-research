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

### After PR #5 merged

**Scope check: on course.** The next PR contains the already reviewed ACDC adapter, its synthetic tests, aggregate evidence, diagram and review resolution, plus this publication record. No subagent is active, no new parser feature or optimization is being commissioned, and no completed full-data audit is being repeated. Integration tests check the merged code once; the research bottlenecks remain release identity, grouping and model feasibility. Corrective prompts are reserved for an observed deviation in a future active task.

## 2026-11-06 — Grouping and smoke-test milestone (Claude coordinator)

**Overall: green, with a provider interruption.** Both tasks stayed within their G0-prerequisite scopes. Neither ran a detector on ACDC/BDD, used paid compute or claimed gate passage.

| Work | Evidence and finding | Action |
|---|---|---|
| GPT ACDC grouping | Stopped after ~4 minutes: the Codex workspace ran out of credits. Uncommitted draft left in its worktree. | Notified the Claude smoke task that GPT could not answer. On my instruction, reassigned to a Claude task that verified the draft before reuse and attributed it explicitly. |
| Claude ACDC grouping | Reproduced the draft's counts with the new links disabled; added byte-identity links and computed a precision verdict. The coordinator independently re-hashed the reference images: 12 identical sets, 2 cross-condition. | Accepted. The infeasibility verdict is a finding, not a reason to change the allocation rule after seeing results. |
| Claude smoke tests | One bounded probe per batch size; one environment retry for an OS DLL block. Recorded values match the JSON log; checkpoint hashes re-verified by the coordinator; `det-eval-2d` unchanged. The note corrects two statements from its own peer reply. | Accepted. DEIM was correctly left untested. |

**Unsupported-claim assessment:** no unsupported performance claims were found. The interrupted GPT exchange is recorded as unanswered, not as agreement.

**Next checkpoint:** GPT cross-review of both commits once Codex has credits again; PR publication follows that review and my approval.

### After GPT cross-review (2026-11-08)

**Scope check: on course.** One formal GPT review, run once Codex usage returned; no re-review loop. The review found an overstated statistical claim (F1) and two documentation errors, not fabricated results. The coordinator fixed them directly and regenerated the grouping summary once, because its verdict logic changed; all other counts reproduced. No detector, GPU or new acquisition work was added.
