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

## 2026-11-09 — Novelty milestone intervention

**Finding: productive narrowing, with an access-loop risk.** The active GPT research task found close prior coverage of threshold-aware calibration, cross-class ranking/candidate limits and clean-threshold transfer. A prefix certificate or a cap effect alone is not a defensible novelty claim. Its newly identified tracking-calibration prior has verified identity but incomplete method access; the agent explicitly retained that limit.

**Prompt sent:** the coordinator directed GPT to make the falsifiable mechanism audit the contribution hypothesis, keep the certificate as a supporting control, stop repeated blocked-publisher retries, and finish the exact fold design, prioritized ablation configuration and counterexamples. The original BDD question and unseen ACDC/BDD detector outcomes remain protected. No new scope, GPU run or review task was added.

**Response/outcome:** the corrective prompt was delivered to the active task. Final artifacts and the agent's disposition are pending; no completed redirection or novelty is inferred from delivery alone. The coordinator verified the two older papers' identities and abstract-level findings, rather than claiming an independent full-method audit. Next checkpoint: the committed design and the pilot's concrete metadata must agree on native selection semantics.

### Dependency premise invalidated; GPU work blocked

**Evidence received:** GPT relayed Claude's actual finding of ten visually judged reference pairs crossing v1 roles, with a 24-to-15 component sensitivity and 31 unreviewed component pairs. The agent revised its design premise rather than executing a knowingly incomplete exclusion rule. The separate GPU pilot is blocked by unrelated user training; this is a resource constraint, not evidence of an agent performance loop.

**Corrective prompts delivered to both active tasks:** hold bridge execution; preserve v1; let Claude produce one confirmed-reference closure and GPT regenerate conditional fold support. Exclude whole closures touching original descriptive-only components, retain the 449-image exclusion, label earlier fold counts as upper estimates and stop seed/role rescue. A bounded all-flagged-edge sensitivity may expose uncertainty, without pretending the flags are confirmed. Do not expand the visual audit or run ACDC/BDD detectors.

**Resource intervention:** Claude was instructed to leave the user's training untouched, stop GPU waiting/retries and finish only CPU artifacts, tests and a clearly blocked pilot record. No new delegate was created. Both prompts were delivered; final artifacts and demonstrated outcomes remain pending. Next checkpoint is whether closures leave a scientifically useful bridge at all, not whether more infrastructure can be added.

### One regeneration reaches the design's stop condition

**Outcome reported by GPT:** its single CPU feasibility regeneration took 0.59 seconds and exactly matched Claude's closure/ledger mapping and hashes, with v1 unchanged. The proposed confirmed-link closure fails to support the complete four-condition calibrated bridge under the declared inner-group rule; the all-flagged sensitivity supports no fold. Raw-arm structural support and empirical threshold feasibility are separate, and must not be conflated with calibration-arm failure.

**Prompt delivered:** the coordinator stopped further graph/allocation regeneration, visual expansion and seed rescue, and requested a committed negative feasibility result with arm-specific statuses and supporting provenance. This is a disconfirmed design premise, not an instruction to optimize until something works. The full four-condition bridge stays on hold, GPU work stays blocked, and no training is ready to queue. Final artifacts and formal review remain outstanding; the coordinator has not independently re-audited the visual judgments or regenerated the graph again.

### GPT design completed

GPT committed three assigned files in `14eacfa`: the research program, source/novelty audit and 12-axis ablation matrix. The final text adopts the corrective prompts: no standalone cap/certificate novelty, no further blocked-publisher retries, one closure regeneration only, explicit night/fog arm failures and no bridge execution or GPU job. It preserves incomplete source access and records actual peer exchanges. This demonstrates the intended narrowing and stop behavior rather than mere prompt delivery.

The coordinator integrated the same patch and checked the matrix and local links. The claimed synthetic case counts and source interpretations still need the separate Claude formal review; they are not accepted solely because the agent reported them. No additional design variant or implementation task is commissioned.
