# Claude cross-review: GPT research program, novelty audit and ablation matrix

**Reviewer:** Claude Opus 5.5 (`claude-opus-5-5`), 2026-11-09. This is a separate formal review task, not a continuation of the active Claude near-duplicate/pilot task. It is not a GitHub approval; my explicit approval governs merges. **G0 remains pending.** Bridge execution remains **ON HOLD**, native GPU replay **BLOCKED**, and no overnight job is authorized.

**Reviewed:** GPT source commit `14eacfa4b5ef7daeef880f24a1b3545104b922a7` against base `9794d81914d43cfbb44d4aa3d127e57145385d42`. The patch touches three files: `docs/gpt/2026-11-09_research_program.md`, `docs/gpt/2026-11-09_novelty_audit.md` and `configs/research/ablation_matrix.json`. These three files are byte-identical in the integrated commit `ca31a24` (`git diff 14eacfa ca31a24 -- <files>` is empty). Review checkout: `t3/f3d8d167` at `9bf649e`.

**Disposition: accept with fixes.** I found no P1 findings, **two P2 must-fix findings** (F1 and F2) and **five P3 advisory findings**. Both P2 fixes are text and status corrections. Neither needs new runs, allocation variants or graph regeneration. The negative feasibility result holds: the complete four-condition bridge is not supported under the declared procedure, and the all-flagged sensitivity supports no fold. The research program is falsifiable, and it is appropriately scoped. After F1 and F2 are fixed, I recommend publishing it as a design/preflight PR that reports known negative feasibility together with a staged, falsifiable program. The disclosed data and resource blockers are not grounds for rejection.

## Method and limits

I read `AGENTS.md`, `CONTRIBUTING.md`, `docs/collaboration/peer_protocol.md`, the [decision record](../decisions/2026-11-09_research_direction.md), the [drift log](../collaboration/task_drift_log.md) and protocol §§1–5. I then read the three reviewed files completely and parsed the JSON. `git diff --check` is clean. The local link anchor `protocol.md#5-monotone-recalibration-theorem-and-exceptions` resolves.

- **Input binding (all SHA-256 hashes match the stated values):** GPT `research_design_checks.py` (`f58ff9ea…c712c713`) and `.json` (`4bbcf70a…a7dd69`); Claude `edge_ledger.json` (`17b5e7e6…24184`) and `reference_closure_v2_manifest.json` (`36e11e40…26da1`); v1 `full_manifest.json` (`04c6a0ad…94fcf3`), unchanged after my run. I read these private files and did not modify them.
- **Independent bounded CPU check:** ignored `outputs/review_research_program_check.py` (SHA-256 `797c4623a8cc87ac125304a9bbecd2dc31cf4b240415e0198602f7a01854be6b`), aggregate output `outputs/review_research_program_check.json` (`88c516cf…f8ed`), Python 3.12.14 stdlib, 1.69 s. Private fold membership stays in ignored `outputs/review_research_program_check_private.json`. The check builds closures by BFS over an explicit adjacency graph, not GPT's union-find. It counts human GT (category 24/25, `iscrowd` 0) directly from the four official aggregate JSONs, not through the project parser. It then re-derives the declared hash ordering and the inner split.
- **Not done, per assignment:** no RGB duplicate audit, full-byte hashing, visual re-review, allocation variant, GPU probe, inference, training, download, package install, peer contact, push or PR. All graph results are **conditional on Claude's reported visual edge classifications**, which I did not independently verify.
- **Primary sources (accessed 2026-11-09, temporary only, nothing archived):** arXiv abstract pages for 2611.00077v1, 2405.20459v1, 2102.01066v2 and 2008.08115. Full HTML for 2611.00077v1 and 2405.20459v1 (Kuzucu: first ~100k characters, covering §§1–4 and the start of §5). The ar5iv rendering of 2102.01066, which does not state its version; v2 is the latest version on the abstract page. The direct arXiv PDF for Dave was not text-extractable here. I did not access the Lee DOI or full TIDE text; see F7.

## Reproduced facts

| Claim in the reviewed files | Reproduced? |
|---|---|
| 2,006 labelled adverse / 1,003 annotated references; v1: 24 closures, 449/225 excluded, 1,557/778 eligible, 16 eligible labelled closures | Yes |
| v2 (+10 confirmed edges): 15 closures, 794/397 excluded, 1,212/606 eligible, 12 eligible closures, 14 condition cells (2 closures span two conditions) | Yes |
| 8,012 path→closure assignments and exclusion flags equal Claude's v2 manifest | Yes |
| Fold membership, fit/selection GT and statuses equal GPT's private record (v2 and pessimistic) | Yes |
| Per condition: fog 291/4, night 154/2, rain 500/4, snow 267/4; night 2 × `INFEASIBLE_INNER_GROUPS`; fog 2 × `UNDEFINED_FIT_GT`; 10 cells pass the fit/selection-GT guard | Yes. Every guard-passing cell has exactly **one** fit closure and **two** selection closures; night cells have 0 fit / 1 selection |
| Pessimistic all-non-rejected graph: 4 closures, 1,738/868 excluded, 268/135 eligible, fog/rain/snow 7/258/3 adverse in one closure each, night none, 0 supported folds | Yes |
| Synthetic counts 92,775 and 16,266 | Iteration counts reproduce; see F5 for what they actually assert |

## Findings, ranked

### F1 — P2, must fix: at a fixed threshold, the policy-dependent ceiling/threshold split is partly built in by the algebra

**Locations:** `docs/gpt/2026-11-09_research_program.md:7`, `:13`, `:21–27`; `configs/research/ablation_matrix.json:10`, `:41–49` (A01 observables `per-condition_delta_M_delta_W_delta_L`), `:52–60`, `:274–276`.

**Evidence (derivation, with a synthetic check):** fix one image and threshold `t`. Suppose the program's own finite-pool certificate holds for a lower-budget policy P′ relative to the maximal policy P: every candidate that P′ omits scores below `t`.

- Then `r_P′(t) = r_P(t)`, `M_P − M_P′ = W_P − W_P′`, and that image contributes nothing to the change in `L`.
- Changing the cap or floor therefore always moves recall mass between the ceiling and threshold-removable components, whenever it removes low-score tail candidates. That shift is bookkeeping, not a mechanism.
- The reselected contrast collapses in the same way. If the certificate holds at the maximal-policy source threshold `t*` on every source-selection image, then `r_P′(b) = r_P(b)` for every observed `b ≥ t*`. Highest-boundary reselection therefore returns the same `t*`.
- So the common-threshold and reselected contrasts can differ from each other, or from the maximal policy, **only through images where the certificate fails at the operating threshold**, or through source infeasibility under P′.

My check confirms the identity in 1,297 certified cases (`certified_policy_change_dM_equals_dW_cases`). Global all-class cap competition (Dave et al.) is one such truncation, so the per-stage omission bound covers it too.

**Consequence:** the contribution hypothesis says the composition "changes", and A01 reports ΔM/ΔW. Read naively, a positive result is guaranteed. A01/A02 become falsifiable only through the certificate-failure subset. In practice they may be null by construction at caps ≥300 if source-selected thresholds sit well above per-image truncation boundaries. Whether that happens is **unknown**: no boundary distribution has been measured. A ≥0.02 trigger could then fire only at cap 100 or at ρ=.95, where thresholds are lowest.

**Requested fix (text only):**
1. Predeclare this algebraic null: certified images have ΔL=0 and ΔM=ΔW, and the two contrasts coincide on them.
2. Restate the A01/A02 mechanism claim as the **frequency, condition-association and consequence** (recall and FPPI) of operating thresholds falling at or below per-stage truncation bounds, reporting the certificate-failure fraction per condition, policy and objective.
3. Add a kill/early-stop clause: if that fraction is negligible across objectives in the future development pilot, A01/A02 are reported as null by construction before any ACDC compute is spent on them.

The certificate then becomes the sufficient statistic for these contrasts, not merely a supporting control. This also answers the question of fairness between the common and reselected contrasts. They are comparable only alongside FPPI, and they differ only on certificate-failing images. ρ=.95 and infeasible reselections must remain in the report.

### F2 — P2, must fix: one "structurally supported" fog cell has zero outer human GT

**Locations:** `docs/gpt/2026-11-09_novelty_audit.md:72` and `:77`; `configs/research/ablation_matrix.json:229` and `:234–235`; also the four fog raw-arm cells implied at `research_program.md:49`.

**Evidence (real metadata, reproduced):** one fog outer cell with status `STRUCTURALLY_SUPPORTED_EMPIRICAL_FEASIBILITY_UNKNOWN` contains 29 eligible adverse and 14 paired reference images with **zero** eligible person+rider GT. The design's own rule (`outer_GT=0: UNDEFINED_RECALL_keep_FPPI`; program step 5) makes recall and `L` undefined in **both** arms for this cell. GPT's metadata guard checked fit and selection GT but not outer GT.

Corrected counts:
- **9** of 14 cells have positive fit, selection and outer GT.
- Fog has **1** calibration-arm cell with defined outer recall, not two.
- Fog has **3** raw-arm cells with defined outer recall, not four.
- All other cells have positive outer adverse and reference GT.

**Requested fix:** add the outer-GT condition to the fog row and to the guard count/statuses, and keep the cell, with FPPI only. The headline verdict does not change. No regeneration is needed: the fact follows from the already-hashed inputs. Separately, several outer cells are very small (3, 7, 8 and 13 adverse images). The text already disclaims precision and coverage, so this is context, not an additional fix.

### F3 — P3: the bridge's calibration arms are selection-level negative controls

**Locations:** `research_program.md:5`, `:43`; `ablation_matrix.json:207`, `:229–230`; `novelty_audit.md:73`.

**Derivation:** positive-slope scalar Platt with observed-boundary reselection is strictly increasing. Under the program's own A05 argument and the protocol's §5 theorem, it selects exactly the raw arm's detections, recall and FPPI on the same selection groups, barring float saturation. The target-labelled optional arm is likewise identical to its raw target-threshold baseline. The night (`n_inner=1`) and fog (zero fit GT) calibration failures therefore lose **only probability-calibration diagnostics** (for example ECE), not any transfer-loss or recall estimate.

Night raw cells are declared infeasible only because the common split requires two inner groups. Each night cell has one selection closure with positive GT (59 and 157).

The text already says the result is not a general raw-arm impossibility. It should add one sentence: the calibration arms are predetermined at selection level, and every guard-passing calibrator would be fit on a **single** closure. Whether raw-only cells should ever use a one-group selection is a coordinator decision for a future task. This review does not propose it as a rescue, and it does not change the stop instruction. The two-group requirement comes from decision record item 2, which GPT implemented faithfully.

### F4 — P3: the AegisBench record has section and repository discrepancies, and its identity is unresolved

**Location:** `novelty_audit.md:17` (P3 row).

**Evidence from the primary source:**
- §5 of 2611.00077v1 is *Experimental Setup*. The threshold-artifact test is §6.4, "Not an operating-point artifact".
- The seed table is Table 6 in §6.4 (seeds 17, 42 and 123). Appendix A covers clean baselines and training.
- The paper's "Provenance and release" paragraph links `github.com/Altis-2026/SentinelBench`. The ledger instead links `github.com/Altis-2026/AegisBench`, whose README cites a *different* title ("…A Disaster-Grounded Robustness Benchmark…"), lists WACV 2027 "under review" and gives the author as "TODO".
- The `2611` identifier / 17 Oct 2026 discrepancy is confirmed on the abstract page, as is the author-reported NeurIPS 2026 AI4GOOD workshop acceptance.

**Fix:** correct the section references and cite the paper's own release URL. Record the repository and title mismatch as a further identity discrepancy, without normalizing it. Give this source low weight as a precedent and do not rest any distinction on it.

Substantively, §6.4 is the source's closest point to this program: it asks whether a condition failure is a threshold artifact, and whether the signal is still in the image. I verified the heading and the claim at the level of the summarized text only, not their experimental method.

### F5 — P3: the synthetic validation is described more strongly than the script executes

**Locations:** `novelty_audit.md:110`; private script lines 115–164.

**Evidence:**
- **(a)** 92,775 is the number of loop iterations. Only **31,822** of them reach the equality assertion (`t >` oracle omitted maximum); the rest are vacuous.
- **(b)** The check uses the oracle omitted maximum. It does not test the per-stage sufficient conditions the audit states: the `>`/`>=` floor comparator, the inclusive kth-score bound, or the missing kth score at k=0.
- **(c)** The 16,266 NMS cases test only pre-NMS floor suffixes, but the text claims "floor/cap replay".
- **(d)** The "eight explicit counterexamples" are literal arithmetic assertions, for example `not (.5 > .5)` and `.9 >= .8 > .1`. They do not run a two-stage selector or NMS.

My independent check found no logical error in the stated certificate:
- **Stage bounds:** 73,458 certified equalities under both comparators, with ties and k=0. 21,278 "unknown" cases were in fact complete, which confirms that unknown does not mean incomplete.
- **Two-stage YOLO26-style selector:** 188,082 global top-k score-value equalities whenever stage 1 keeps at least as many anchors as stage 2 keeps pairs (k₁ ≥ k₂), and value mismatches when k₁ < k₂. "Equal budgets" can therefore be generalized to k₁ ≥ k₂. Claude's report that the hidden first stage uses `max(max_det,300)` comes from code inspection only and was not runtime-verified here.
- **NMS:** 11,754 pre-NMS cap-prefix equalities, 6,273 post-NMS cap prefixes, and an executed counterexample in which a kept kth score of .1 coexists with suppressed .9.
- **Monotone maps:** 34,020 observed-boundary reselection equalities under s² and positive-slope Platt, and 703 midpoint-reselection disagreements.

The other certificate claims also check out:
- the per-stage composition;
- the conservative all-class bound for the person subset;
- that the hidden head bound is not recoverable from the API cap;
- that post-NMS kth scores do not certify the pre-NMS pool;
- the exclusion of timeouts, dynamic pools, fused, soft or learned NMS and rounding;
- that no recall guarantee follows from selection completeness.

**Fix:** report "31,822 asserted equalities among 92,775 enumerated oracle-bound cases; floor-suffix NMS only; counterexamples encoded as arithmetic assertions". Reproducibility is sufficient for a **design/preflight** PR: inputs are hash-bound, the run is deterministic and private identifiers stay private. A stage-bound test belongs with any future certificate implementation, not in this PR.

### F6 — P3: the compute table mixes units

**Location:** `ablation_matrix.json:165`, `:259–261`.

S0's 96 counts **source selections** (6 policies × 4 systems × 4 objectives); the common-threshold and reselected *evaluations* number roughly twice that. `historical_preclosure_S0_S1_offline_evaluation_upper_estimate: 1920` adds 1,536 selections to 384 evaluations. The arithmetic is otherwise correct: 9,340 = 2,335 × 4; 56,040 = 9,340 × 6; 4,670 = 2,335 × 2; 1,818 = 1,212 + 606; D0/D1 = 128 + 128. Relabel the 96 and 1,920 figures as selections and as a combined workload, or split them. These counts are pre-closure arithmetic only, and are already labelled so.

### F7 — P3: the close-prior ledger is accurate at the depth I checked

- **Kuzucu 2405.20459v1:** the identity and the 30 May 2024 date match.
  - Verified in full HTML: thresholded, model-dependent (LRP-optimal) evaluation in §1 and §4.2; LaECE₀ and LaACE₀ in §4.1; Platt and isotonic regression adapted in §4.4; shift evaluation on COCO-C, Obj45K, Cityscapes-C and Foggy Cityscapes.
  - The calibrators are **class-specific**, consistent with the ledger's note that classwise or non-strict maps fall outside the global strict-map control.
  - The paper notes the top-100 (AP) versus 0.30 (D-ECE) inconsistency but does not analyze cap or floor truncation as a recall mechanism. That is consistent with the proposed distinction, though I make no novelty claim from absence.
  - The ECCV record was not re-checked.
- **Dave 2102.01066v2:** v1 is dated 1 Feb 2021 and v2 15 Mar 2022.
  - Confirmed: the shared per-image limit couples classes (§3.1); budget effects appear in Tables 1–3; APFixed is defined in §4 and APPool in §6.1; Appendix A.4 covers NMS effects.
  - Dave frames the cap through ranking and precision and does not analyze recall loss directly. Hosang (P8) covers recall versus proposal budget.
- **TIDE:** my access matched the ledger's partial-access label (abstract only, v2 dated 31 Aug 2020; six error types with isolated contributions). No equivalence or exclusion claim should be made, and none is.
- **Lee:** not accessed. The ledger correctly claims identity only; I make no method claim.

## Items checked without findings

- **Scope and authority:** the documents present GPT's proposal, not an amended protocol, adopted graph or authorization. Specifically:
  - closure v2 is a proposal, not the adopted primary graph and not a proof of independent trips;
  - the 31 unreviewed pairs and the uncertain or other-pass flags remain explicit limits;
  - the pessimistic sensitivity is labelled as neither verified merges nor an exhaustive bound;
  - there is no seed search, rescue allocation or selective complete-case benefit claim, and all 14 cells and their statuses are retained;
  - GPU, training and overnight work are blocked, and G0 is pending.
- **Bridge semantics:** normal references are not labelled BDD clear-day, and there is no Detection 2020 substitution. The merged human population has its own thresholds and denominator, with a separate person-only panel. Exclusion of the whole outer global component is implemented. Inner groups are condition-specific and use the declared SHA-256 order and floor(n/2) fit split, with fit and selection separated.
- **Decomposition:** `L_c=(M_ref−M_c)+(W_c−W_ref)` holds. `W ≥ 0` holds under the protocol's greedy prefix-monotone matching. The U/V target-shortfall reference matches protocol §1. The AP≈.001 versus ceiling-1 example is correct. Claims stay observational ("condition-associated"), and acquisition and annotation confounding of the pairs is disclosed.
- **Axes:** the 12 axes are tiered, one-at-a-time (6 policy settings), non-Cartesian and conditional on a surviving core mechanism. The O2O/O2M, class-order and NMS contrasts carry correct non-causal limits, and the cache-reuse requirements are conservative.

## Remaining issues after fixes

F1 and F2 are text and status edits to the three reviewed files. F3–F6 are minor and can be fixed directly by the coordinator without another review loop.

The following limits remain open:
- the visual edge judgments and the 31 unreviewed pairs;
- coordinator adoption of the closure graph;
- empirical threshold feasibility and certificate-failure rates (not yet measurable);
- native replay and identity stability (GPU-blocked);
- the AegisBench identity;
- Lee full-method access.

No detector performance is known. Claude holds no objection that would block publication once F1 and F2 are addressed.
