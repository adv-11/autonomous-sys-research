# Independent NightOwls evaluation review

Reviewer: **GPT Sol (gpt-6.1-sol), separate review task, 2026-11-23**.
Reviewed commit: **02486e747279585e6d690397b832f0fde3299aeb**, parent
`c922cdacfe4e69232db454d82b3fc2b77e0bbc43`. Scope: report, aggregates,
four PNG/SVG figures and evaluation scripts; primary A/B/C only.

**Verdict: no blocking scientific or code finding for the provisional,
descriptive external answer. No implementation fix requested.** My explicit
GitHub approval remains required for merging; this independent GPT Sol AI review
does not pass G0. All results and claims remain provisional.

The v1 contract, superseding v2 amendment and BDD reference were read. Source
checkout files match the reviewed commit. Nineteen retained executed-source/
contract hashes match the receipt; their contents match Git after CRLF
normalization. Prediction, native-label, pilot and BDD-label hashes were checked
against the receipt. Historical Claude Opus inference attribution is preserved;
this review adds CPU evidence, not fresh inference verification.

Independent findings:

- Native labels give **51,782 images / 7,631 Reasonable GT**, 42,316 natively
  empty frames, 1,304 unkeyed frames / 860 GT, and recording GT counts
  **1,005/291/4,994/332/149**, after the exact 64 pilot and two dusk exclusions.
  Eligibility uses unclipped native height, category 1, ignore 0 and SDK visibility;
  null occlusion is conventionally visible, not independently verified visibility.
  All four setup boundaries and both profiles agree with raw annotation counts.
- Primary `unused_nonpedestrian` has **2,520** absorbing regions; sensitivity
  `person_compatible_ignore` has **9,421**. Riders never enter eligible GT.
  The code implements eligible-first, descending-score greedy matching, lexical
  canonical GT-ID ties, candidate-index ties, inclusive IoU/IoA .50 and reusable
  ignore regions. A separately written matcher agrees on **2,912 image/setup/
  profile evaluations**: a different regular sample plus every zero-area image.
  A's one zero-area candidate is an explicit FP; B/C have none. No clipping or
  candidate-height filter is introduced. Saved inference code/config preserve
  all-class cap before pedestrian filtering, floor 1e-4, class-aware .70 NMS,
  FP32 and the declared native sizes; raw candidates show no cap hits.
- Raw BDD box counts reproduce selection **1,842/1,181**, clear **1,764/1,256**
  and night **3,929/1,616** image/GT support. Independent grouped-score selection
  over retained arrays reproduces every stored policy threshold/status, including
  primary t* **.11140981316566467/.23994138836860657/.12197767943143845** and
  selection TP **945/1,181** for each arm. Whole tied groups are included.

| Independent primary restatement | A | B | C |
|---|---:|---:|---:|
| TP / 7,631 | 4,589 | 4,659 | 4,769 |
| Recall | .601363 | .610536 | .624951 |
| FP / 51,782 images | 35,953 | 9,255 | 45,923 |
| FPPI | .694315 | .178730 | .886853 |
| Absolute misses: no greedy match / threshold removed | 1,674 / 1,368 | 1,357 / 1,615 | 1,525 / 1,337 |
| R3-out TP / 2,637 | 1,236 | 1,338 | 1,303 |
| R3-out recall | .468714 | .507395 | .494122 |

- Natively empty frames contribute **22,127/4,776/29,364 primary FPs**. They
  remain in the 51,782-image denominator, as do ignored-only images. R3-out
  retains **36,604 images**, four known keys and the fixed unkeyed frames.
- Absolute misses above are distinct from clear-reference **differences**.
  Independently recomputed primary ceiling/threshold-miss differences are
  **16.284/5.984, 14.996/6.116, 14.491/6.135 pp**. All four retained ceiling
  definitions reproduce. Any-IoU .30 changes B/C's splits to **9.321/11.791**
  and **9.033/11.593 pp**, with unchanged operating recall. Thus component
  dominance depends on definition; it is not a causal mechanism finding.
- A's .80 target oracle is infeasible. B/C reproduce thresholds
  **.00041072125895880163/.000101788122265134**, each with 6,105 TP and
  **34.68877/45.88463 FPPI**. Source-infeasible policies retain undefined transfer
  results and intervals; oracles are explicitly same-target-label diagnostics.
- Four saved replicate indices (**1, 217, 618, 998**, zero based), in each of
  four modes and all three arms, reproduce **48** independently counted operating
  points, source reselections and clear-reference losses. Source/clear image
  order is paired across arms; target weights are shared across panels. The
  five-key/known-only/four-key-out/IID weight rules agree with the contracts.
  Re-percentiling retained values also reproduces all **12 primary recall
  intervals and 12 paired recall contrasts**, without rerunning 1,000 draws.
  Unkeyed weights are fixed at one in pooled/out modes, zero in known-only;
  this conditional uncertainty is declared. There are 119 observed recording
  multisets and 336 R3 omissions. Joint known-key ceiling coverage independently
  reproduces **512/236/3,933/39/81**; R5 remains below the 150-box floor.
- Both decompressed public JSONs exactly equal retained private aggregates;
  compressed/uncompressed manifest hashes agree. Structural identity/geometry
  scans and SVG filename scans pass. Visual inspection of all four PNGs and
  inspection of figure code/SVGs found aggregate-only graphics, anonymous
  recording labels and no exposed examples, native IDs, boxes or mapping.
  This is the contract's publication check, not a claim that aggregate statistics
  prevent linkage to independently held data.

Open limits: five keys do not establish independent recordings/trips; source
image resampling assumes independent BDD keyframes; interval coverage is
unvalidated. Recording composition strongly affects the answer. BDD occlusion,
annotation completeness/extent and input scale remain unaligned. Native resize
ratios are supported by saved original shapes/configuration; padded tensor
shapes were **derived, not recorded**, and remain unverified. No IID
generalization, causal darkness effect, novelty or G0 passage follows.

The [bounded checker](2026-11-23_nightowls_evaluation_check.py) passed with the
authorized Python interpreter and NumPy, with no model-framework imports.
The full analysis and full bootstrap were not rerun. No implementation file,
briefing, inference, GPU/Colab session, download, installation, push, PR or merge
was part of this review. No peer agreement is inferred or manufactured.
