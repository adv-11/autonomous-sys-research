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

### Final cross-reviews and publication boundary

**Overall: amber, corrected or held.** Both independent tasks and both separate formal reviews are complete. Actual peer exchanges are preserved. No active task is stalled; no replacement or incremental optimization task is needed.

- **GPT scientific claims:** Claude found an algebraic null that made part of the proposed policy effect self-confirming, a zero-GT fog cell, overstated synthetic validation and an unreliable prior identity. The coordinator [resolved these directly](../reviews/2026-11-09_gpt_research_program_resolution.md): separate source reselection from direct target effects, predeclare null/stop rules, correct support and assertion counts, and lower the uncertain source's evidential weight. A bounded counterexample prevents overextending the null to target-only certification. No new graph, seed search or detector experiment followed.
- **Claude runtime readiness:** GPT reproduced the CPU audit counts but found undeclared dependencies, unrelated workload details, fail-open GPU parsing and unverified capture/identity/evidence safeguards. The [resolution on the Claude branch](https://github.com/adv-11/autonomous-sys-research/blob/claude-research/docs/reviews/2026-11-09_claude_dependency_pilot_resolution.md) declares CI dependencies, removes unrelated workload details, tests conservative parsing and disables capture, grid approval and audit reprocessing before resource access. Remaining runtime defects are deferred behind those holds, not reported as repaired. The combined revised branch passes 181 CPU tests in the existing Python 3.12 environment; clean CI remains to be observed.

**Assessment:** concrete overclaims and readiness defects were caught before publication/use; there is no evidence of invented detector results. Earlier corrective prompts achieved bounded completion. Because the tasks are finished, the coordinator made small corrections and enforced holds directly rather than manufacturing another peer exchange or review loop.

**Next milestone:** sequential publication and my review, then a scientifically feasible source-data/experiment decision. The four-condition bridge and GPU pilot remain on hold. Runtime repair is a future scoped task; training needs prior overnight coordination. No further parser, source-access, allocation or performance loop is commissioned.

## 2026-11-10 — Colab resource steering and coordinator qualification stop

I authorized all GPU work on my connected Colab account and scale guided by research value and available compute. GPT verified 300 displayed units, then two short L4 allocations at 1.94 units/hour. Neither used the local GPU or a real dataset. The first synthetic detector loss failed on dictionary configuration; one corrective retry failed on missing autograd. Both completed zero updates, and both sessions were terminated. No third retry or performance-tuning loop follows.

**Coordinator drift/error assessment:** writing a direct training harness before checking the loss/configuration and gradient contracts introduced avoidable setup failures. A zero `colab exec` exit status also failed to reflect a remote exception; the retrieved artifact prevents a false success claim. The corrective action is a bounded CPU repair with artifact-based status validation, not larger hardware or repeated allocations. An unchanged displayed balance is retained with billing-lag uncertainty. Exact failure evidence remains in ignored outputs; the public decision record contains aggregate facts only.

**Next milestone:** a reviewed, small Colab development experiment tied to a falsifiable mechanism, with a unit-budget estimate and native replay evidence. GPT implementation and Claude research-priority assignments must exchange contracts directly, remain CPU-only themselves, and stop at their artifacts. This new instruction moves the execution venue; it does not fix grouping or BDD access, reopen allocation searches, pass G0 or approve a merge.

### Research-first steering: Astra completion

I redirected the work to Sol/Astra and actual Colab inference. The coordinator cancelled the broad CPU contract-repair task and designated Sol as the sole bounded Colab operator. Claude remains unused while unavailable. The [research-first decision](../decisions/2026-11-10_research_first.md) supersedes the earlier agent execution restriction.

**Scope check: on course.** Astra committed only the [prospective hypothesis note](../gpt/2026-11-10_astra_research.md), with no regression suite, new framework, GPU use or invented aggregates. Actual peer messages record Sol accepting H1 before inference: source-induced threshold movement has a larger night-recall consequence than the direct candidate effect and its COCO-reference consequence, at the fixed .90 objective. Infeasibility remains untestable, and an operating null can kill the direction. Person-first filtering makes this a within-human pipeline contrast, not an all-class competition audit.

The coordinator integrated the note and reminded active Sol to finish the real-data result and teardown within the existing 10-unit/90-minute budget. Astra's optional fresh-source repeat is a future conditional recommendation, not another authorized run. No new review, test task or allocation was created at this checkpoint; measured outcomes remain pending.

### First completed empirical result: kill H1, follow coverage

Sol completed all four native policies on700/700images each. All three .90 H1 contrasts have B=D=0 and the same source threshold; the proposed fresh-source repeat is not triggered. The .95 objective is infeasible. This is a real operating null with complete evidence, not a failed run renamed as a null. Total displayed empirical use is .55 units, including the earlier failed .31-unit attempt; both assignments verified teardown.

**Scope check: productive, with a changed research premise.** Native inference itself took79.5seconds; most wall time was transfer/setup/retrieval. The useful result is that the large COCO-to-night recall difference is mainly a finite-pipeline coverage difference, while the small matched normal panel is also weak. No causal night explanation or novelty follows. The coordinator stops the cap/floor direction, avoids repeating qualification or broad tests, and authorizes one fixed-panel resolution intervention plus Astra's focused result interpretation/per-object diagnosis. These actions follow new evidence rather than optimizing a failed hypothesis into success. No model zoo, fresh source block, target-driven cutoff rescue or training is commissioned.

### Resolution result survives the credit interruption

Both GPT assignments were interrupted by workspace credits, after the 1280 inference and owned Colab teardown had already completed. On my instruction to retry, the coordinator checked saved status before relaunching work. Sol resumed CPU aggregation only; no repeated GPU run or Claude substitution occurred. Astra's interrupted review/diagnosis artifacts were retained for a separately delegated GPT completion.

**Observed result:** all700images completed at1280. H2's fixed net-gain/GT criterion passes:34/89small versus12/127larger. The extra headroom diagnostic is essential: net recovery per baseline miss is49.28%small versus63.16%larger, so this does not establish preferential recovery of already-missed small objects. Normal references improve too. Pooled adverse .90 source-reselected recall rises44.44%to59.72%, with FPPI falling2.43to1.40, while some large-object matches are lost. These are finite-panel native-pipeline results, not novelty, physical-scale isolation or causal-night evidence.

**Scope check: on course, with an explicit stop.** Sol reused the packet/evaluator and ran one resolution policy, no new model or testing programme. Cumulative displayed empirical use is.98CU, verified owned teardown and zero active assignments. The coordinator integrated the result and commissions no further allocation from H2 alone. Astra's scientific diagnosis/review will determine whether residual failures justify a contribution hypothesis beyond ordinary scale/task/scene effects. PR#8 remains open; no research merge or G0 passage is inferred.

### Prior-art pressure test rejects the present method claim

Astra completed exactly three targeted primary-source checks and recorded access limits: weighted boxes fusion covers augmented-view fusion/support-based confidence; geometry-conditioned detector calibration is established; prediction-consistency/reliability evaluation is a close prior inspected only at abstract level. The completed note does not claim absence of prior work, complete access to all methods or measured cached-baseline outcomes that had not arrived.

**Scope check: on course; method development stopped.** No test programme, inference or extra allocation accompanied the assessment. The coordinator integrated it and steered active Sol to finish only the two already assigned cached baselines. No learned calibrator, extra baseline or GPU run is commissioned. Any later contribution hypothesis must demonstrate useful information beyond score/geometry/counts and survive unseen validation; a definitional agreement-gate failure or ordinary fusion gain will not be promoted as novelty. The recorded Sol exchange agrees on interpretation, not missing empirical outcomes. The next checkpoint is the actual cached-baseline result and a compact research synthesis.

### Cached baselines complete; close the method branch

Sol completed both fixed CPU baselines, with one small postprocessing/matching check and no new inference. At .90, adverse TP/FP are1280:129/179,fusion:122/143,gate:116/203. Fusion is a tradeoff, not dominated; the gate is worse on both pooled measures. The union oracle provides only four extra adverse GT, already attained by fusion's all-output ceiling. These are actual cached measurements, distinct from Astra's earlier prospective assessment; its final numerical message to the finished Astra task was not delivered and is not treated as peer agreement.

**Scope check: on course and stopped.** No fourth baseline, new calibrator or allocation was added. The coordinator integrates the result into a [compact checkpoint](../research/2026-11-10_checkpoint.md) and commissions one bounded publication review of the newer1280/cached-baseline implementation and claims. The completed640review is reused; no full regression, repeat GPU run or broad new research task is requested. Cumulative displayed empirical GPU use remains.98units. Research merges remain subject to my explicit approval, with PR#8stillopen at the latest check.

## 2026-11-11 — Sol-only continuation and saved review recovery

I requested Sol only to reduce token use. The coordinator records that preference in AGENTS.md; no new Astra or Claude task is launched. Historical research/reviews keep their original attribution.

The latest Astra publication task reported a credit failure, but its isolated checkout contains committed review artifact `7ca2cd0`. The coordinator recovered it rather than commission a duplicate Sol review. It reports no material blocker and records bounded independent execution of the decisive 1280/cached-baseline calculations. The failed task status is preserved; the review's content and verification limits remain attributed to Astra. The checkpoint now links that review.

**Efficiency decision:** reuse completed evidence, keep future briefs concise and commission one Sol task at a time when practical. Current fusion/gating method development stays closed. A new research question must distinguish image information from model-grid effects with clear controls and closest-prior limits before earning another allocation; no repeat sweep or new method name follows from the previous gain.

### Information control complete: stop scale diagnostics

Sol completed one three-arm experiment, with all700images freshly inferred per arm and no corrective rerun. H/L/U adverse ceiling counts are172/127/160of216. The fixed criterion passes because33/45netgain exceeds onehalf. The coordinator preserves the distinction between a ratio of net changes and identities of recovered objects; signed gained/lost counts remain in the report. No generic enlargement novelty or isolated architecture/darkness cause follows. Displayed empirical use is now1.28units, and the owned session was released.

**Scope check: on course and finished.** Pre-NMS instrumentation was omitted as directed; the small GT-map/input-shape checks protected the scientific control without adding a framework. No additional resolution/fusion sweep is commissioned. Future work should address a different unresolved question, such as how to audit a transferred recall claim with a small annotation budget despite common misses and dependent scenes; it must be checked against established statistical/audit methods before any novelty claim. The next step can use cached data and mathematics with no GPU allocation.

### Complete-audit proof survives; incomplete feedback is a material blocker

Sol proved the fixed-pool reduction and conditional expectation under exact complete audits, and identified standard ALPHA/active-testing/recall-estimation overlap without inventing novelty. Its locked development demo rejects the low-recall adverse pool, with no simulated rejection on the known-null source fixture; the twenty seeds do not establish error control. The proof, not Monte Carlo, supplies the stated conditional validity.

**Scope check: productive research, no performance loop.** The material counterexample is omission of a matched GT label: true `(G,T,D)=(10,9,9)` can appear as `(9,8,9)` and cause a false logical rejection. The coordinator integrates the result and commissions one narrow conservative-partial-feedback question, preserving the old complete-audit assumptions. A pointwise lower-bound observation may avoid that error, but its matching lemma, power and prior overlap remain open. No unqueried-pool/GPU study, policy search or annotation platform is launched.

### Conservative variant valid, but no useful cost advantage

Sol proved the matcher lemma and conditional lower-bound betting validity and completed only the locked cached demo. Conservative partial observations cost more queries and observed labels than the original complete-audit reference. The coordinator closes this variant without changing eta, omission rates, seeds or sampling policies to seek a win.

**Bigger-picture correction:** further kernel variations would be incremental drift. The next Sol task is problem selection: whether unknown object-count annotation cost leaves an actual gap beyond existing cost-aware evaluation. It must examine the closest prior, return a pursue/reject decision and a feasible unseen study, without implementing another sampler or buying compute. The [audit checkpoint](../research/2026-11-11_audit_checkpoint.md) preserves the negative decision and review limits; no new statistical or method novelty is inferred from validity alone.
