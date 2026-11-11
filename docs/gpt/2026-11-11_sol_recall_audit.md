# Fixed-pool recall rejection audit

GPT Sol, 2026-11-11; base `783dc5a254a536f0b064855e5268956f00bac5c4`. I want a substantive statistical decision at low cost. Sol performed this derivation, source check and CPU development demo; no peer review occurred. No GPU, inference, installs, new data scan or children. **G0 pending.**

**Decision:** the construction survives under exact complete audits and genuine recorded randomization. Its betting core is standard; treat the recall reduction as an application, with no method name or novelty claim.

## Break attempts and assumptions

Freeze a finite image pool, detector, threshold, eligibility and matching. Counts are finite integers, with `0 <= T_i <= min(G_i,D_i)`. Known `D_i` includes **all** emitted human predictions at the threshold, including ignored and zero-area rows. It is not just TP+FP after ignore handling. Image/scene dependence is unrestricted.

Predictability matters: for two remaining values `(0,C)` drawn uniformly under the boundary null, choosing eta=0 after observing zero and eta=1 after observing C gives expected factor 1.5. It is invalid. Use pre-draw S, conditional draw probabilities (not marginal inclusion probabilities), and eta chosen before the draw. Full support permits cancellation over every remaining image; sampling only detection-positive images cannot audit common misses.

Incomplete audits are not automatically conservative. One image with `(G,T,D)=(10,9,9)` has true recall .90 and X=C=9. Omitting one matched label gives `(9,8,9)`, X=10>C: a false logical rejection. Noisy labels or changed matching can likewise invalidate the claim. Abort inference on incomplete/uncertain audits unless separately justified conservative observations are available; the demo assumes the retained annotations are the complete policy-defined reference, not verified physical truth.

## Reduction and proof (GPT Sol)

Write totals G,T and C=sum D. For G>0:

\[
X_i=9(G_i-T_i)+D_i-T_i\ge0,\qquad
\sum_i X_i-C=9G-10T,
\]
\[
R=T/G\ge .90\quad\Longleftrightarrow\quad \sum_iX_i\le C.
\]

Use the enlarged null H*: sum X<=C, including G=0. Condition on the frozen population and history before draw t. Let U be remaining images, S the **previously** audited sum, B=C-S>0, and p_i>0 sum to one on U. For predictable eta in [0,1]:

\[
F_t=1-\eta_t+\eta_t\frac{X_{I_t}}{p_{I_t}B},\qquad
\mathbb E(F_t\mid\mathcal F_{t-1})
=1-\eta_t+\eta_t\frac{\sum_{i\in U}X_i}{C-S}\le1.
\]

Thus M_0=1, M_t=M_{t-1}F_t is nonnegative and a supermartingale under every H* population. No GT-count bound or IID scene model enters. H* itself bounds the remaining nonnegative total. Ville's inequality yields:

\[
\Pr_{H^*}\{\max_{t\le N}M_t\ge1/\alpha\}\le\alpha.
\]

Any data-dependent stopping/query budget up to N preserves this rejection bound. Allow an unsafe-recall statement only after **observing positive eligible GT**, even if a prior wealth crossing is remembered. This gate restricts the crossing event. Independently, S>C is a logical contradiction of H*, with probability zero under H*.

When B=0, H* forces every remaining X=0: freeze wealth, continue auditing if desired, and reject logically on a positive X. When B<0, reject logically; never divide or clip. Define wealth frozen after contradiction and after exhaustion. C=0 uses these same rules: positive audited GT implies T=D=0 and contradiction; otherwise no recall statement. A zero-query budget gives no rejection. At exhaustion G=0 means undefined recall; with G>0, sum X>C determines R<.90 exactly, even without a wealth crossing. Exhaustion with R>=.90 is a complete census calculation, not an early certificate from non-rejection.

This is design-based probability over audit draws on this fixed pool. Non-rejection never certifies safety/high recall; nothing guarantees future scenes. Separate policies/seeds are separate simulated audits, not permission to select the best live run at unadjusted alpha.

## Exact prior overlap

[Stark's ALPHA](https://arxiv.org/pdf/2201.02707v3), Eq. (5), has factor `a*Y/mu + 1-a` after setting its mean parameter to `mu+a*(u-mu)`. Here `Y=X_I/(n*p_I)`, `mu=(C-S)/n`, `a=eta`. Its without-replacement remaining-total adjustment and weighted batch cancellation also match the ingredients. The direct proof above needs only nonnegativity, rather than a useful externally supplied upper bound. This is an algebraic specialization/extension of that standard factor, not evidence of a research gap.

[Kossen et al.](https://proceedings.mlr.press/v139/kossen21a/kossen21a.pdf), §2.2, Eq. (3)-(4), already use adaptive label acquisition and importance correction for fixed-test-set loss estimation. That estimator is not this optional-stopping test. [Sawade et al.](https://proceedings.neurips.cc/paper_files/paper/2010/file/d7a728a67d909e714c0774e22cb806f2-Paper.pdf), Eq. (2),(4), address unknown-denominator generalized risks, including recall, through importance-weighted ratios and asymptotic variance optimization. They explicitly sample both predicted classes for recall. The three checks close a novelty claim about these ingredients; they do not establish an exhaustive literature absence result.

## Locked development demo

`experiments/2026-11-11_recall_audit.py` reuses `pilot_evaluator`/`ReferenceEvaluator`, native1280 threshold `.08221367746591568`, and the original manifest. Only stored threshold-prefix rows are matched; no baseline inference is repeated. Alpha=.05, eta=.5, seeds **0-19**, budget=N; policies are uniform and `p_i=.2/n+.8*D_i/sum_remaining D` (uniform when sum=0). Exact integer random draws and rational wealth avoid threshold-rounding decisions. The sampler sees only D and queried (G,T). Private per-image counts/traces remain ignored under `outputs/colab/recall_audit_20261111/`.

| Seen panel / policy | Non-rejections / 20 | Queries median [min,max] | Observed eligible GT median [min,max] |
|---|---:|---:|---:|
| Adverse / uniform | 0 | 8 [3,77] | 24.5 [8,86] |
| Adverse / count mixture | 0 | 7.5 [3,18] | 39.5 [18,80] |
| Source known-null / uniform | 20 | 256 [256,256] | 579 [579,579] |
| Source known-null / count mixture | 20 | 256 [256,256] | 579 [579,579] |

Adverse: 128 images, G=216, T=129, FP=179, ignored=38, **C=346**, sum X=1000; every rejection used wealth crossing. Source: 256 images, G=579, T=522, C=1156, sum X=1147. All-run costs include non-rejections at exhaustion. One synthetic exact two-image boundary-null tree has terminal wealth `(1/2,41/2)` with probabilities `(39/40,1/40)`: expectation=1, crossing probability=1/40<=.05. These checks passed; empty-pool and C=0 branches also passed. Monte Carlo establishes neither validity nor nominal error. Panel labels/results were already seen; the selected source is a known-null fixture, not unseen validation. No policy dominance is established.

**Next scientific decision:** retain this as a standard rejection-audit application and decide whether a genuinely unqueried fixed pool merits a preregistered annotation-cost evaluation. **Kill condition:** stop if complete audits, frozen coverage or correct full-support probabilities cannot be ensured; close any novelty project unless a concrete uncovered gap is identified. This task stops here; no safety certificate, label-free claim, PR or merge.

## Primary-source ledger

Accessed 2026-11-11. Exactly three works used; public full PDFs available, relevant sections inspected; no blocked-source retry. Paper redistribution/licensing was not evaluated.

| Identity/version | Access depth and evidence |
|---|---|
| Philip B. Stark, *ALPHA: Audit that Learns from Previously Hand-Audited Ballots*, arXiv:2201.02707v3, 2022-02-01 | PDF title/author/version verified; §2.2 Eq. (5)-(9), WoR paragraph, §4.2 Eq. (19)-(23). HTML had no article body; advertised PDF supplied the text. |
| Jannik Kossen, Sebastian Farquhar, Yarin Gal, Tom Rainforth, *Active Testing: Sample-Efficient Model Evaluation*, ICML/PMLR 139:5753-5763, 2021 | Publisher identity and 11-page PDF verified; §2.1-2.2 and Eq. (3)-(4), adaptive-proposal paragraph. |
| Christoph Sawade, Niels Landwehr, Tobias Scheffer, *Active Estimation of F-Measures*, NeurIPS 23, 2010 | Publisher identity and 9-page PDF verified; §1 Eq. (1)-(4), §2 variance/sampling, §2.2 support condition, §3 recall sampling discussion. |
