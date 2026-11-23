# Independent review: threshold-transfer synthesis

**Claude Opus (independent review task), 2026-11-23**, standing in for GPT Sol, which is out of credits. I did not write the synthesis. This was a read-only review: no edits, commits, pushes or GPU use.
Reviewed: `origin/claude-threshold-synthesis-20261123` at `dbb783c` (base `2644c85`). The review covered the paper, four PNGs and the figure script, checked against the merged PR #13/#14/#15/#17 reports, their reviews and their aggregates.

**Verdict: ready after fixes.** No number I checked is wrong, and the main hedges are all present: erratum absolute vs difference, seed-pair disagreement, calibration targets rather than guarantees, ACDC descriptive only, R3 dominance, and preregistered vs exploratory labels. Findings 1–3 are fixes to the text and a caption. None needs new computation.

## Findings, ranked by severity

1. **P2. The Figure 3 caption describes the black tick backwards.** In `docs/research/2026-11-23_threshold_transfer_synthesis.md:93` the caption says the tick's "distance from the red segment's left edge is the ceiling difference". The script draws the tick at x = 1 − (M_clear − M_night) (`scripts/reports/threshold_transfer_synthesis_figures.py:241`). The red segment starts at M_night. The tick-to-left-edge distance is therefore 1 − M_clear (the clear-day unmatched share), and the ceiling difference is the distance from the tick to x = 1. Check for B: M_night 0.830 and M_clear 0.897 put the tick at 0.933. That is 0.103 from the left edge (= 1 − M_clear) and 0.067 from the right end (= the ceiling difference). The legend entry "clear-day unmatched share (1 − M_clear)" (`:248`) also reads as a position, which it is not. **Fix:** say that the tick splits the red segment into the clear-day-level unmatched share (left) and the excess over clear day (right, the ceiling difference). Alternatively, move the tick to x = M_night + (1 − M_clear) and keep the caption. The two are the same point, so only the wording needs to change.

2. **P2. The compute paragraph leaves out the RT-DETR allocation spend and the balance anomaly without saying why.** `...synthesis.md:184` totals 60.9 CU of "Claude-owned" spend. The RT-DETR stage total of about 0.3 CU appears only in §6 (`:177`), and the paragraph does not say whether it is included. That figure comes from the unmerged branch `rtdetr-night-transfer-paused`, ledger in `2756dbd`: `stage_total_charged_CU: 0.3`. The same ledger records that Claude's two attempts charged 0 CU, so the 0.3 CU is from the earlier GPT-operated attempts. The paragraph also omits:
   - the unexplained 262.56 → 200.00 CU balance drop between stages, which [R] line 151 and the [R-rev] compute note both flag;
   - that the 5.06 CU predates the YOLO11s study, although the sentence implies it belongs to "the completed YOLO11s study".

   **Fix:** state that the RT-DETR ~0.3 CU is excluded because it is outside the YOLO11s study and not Claude-charged, and cite the branch and commit. Mention the 62.56 CU anomaly as unverified. Reword the 5.06 CU as earlier project spend.

3. **P2. The RT-DETR status is cited from unmerged work, which breaks the "merged results only" scope.** `:3` says the synthesis covers PRs #13–#17 only. `:177` states facts from an unmerged branch with no citation: "four failed requests, about 0.3 CU", contract frozen, and L4 allocation blocked. **Fix:** label the sentence as unmerged and uncited status, with the branch and `2756dbd`, or reduce it to "paused; see branch".

4. **P3. The §4 claim table goes beyond the sensitivity analysis for B2.** `:151` says both components are positive "across A/B/C/B2 … and all sensitivity definitions". `sensitivity_F1.json` (PR #13) contains only A/B/C, and B2 was evaluated under the reported definition only. **Fix:** say "A/B/C for the definition sensitivity; B2 at the reported definition".

5. **P3. The §3.6 table mixes sign conventions in adjacent columns.** At `:135–139`, "Loss vs BDD ≥50 clear day" is clear − NightOwls (positive = loss), but "vs BDD ≥50 night" is NightOwls − night. For example, A −1.99 pp means NightOwls is lower, and C +1.67 means NightOwls is higher, as in [N]. A reader taking the second column as a loss would get the direction wrong. **Fix:** relabel it "NightOwls − BDD ≥50 night".

6. **P3. The populations caveat is weaker than in the source.** `:141` says NightOwls recall is "close to BDD ≥50 px night recall", and Fig. 1c places the two side by side. [N] immediately adds "These populations are not interchangeable" (occlusion, annotation and scale differences). The synthesis puts this caveat in §5 but not next to the comparison. **Fix:** add the clause at `:141`, or in the Fig. 1 caption. Fig. 1c also shows intervals only for NightOwls pooled, not for the BDD ≥50 points or R3-out. That is acceptable, but the caption should say so.

7. **P3. The darkness wording is carried over from the source unchanged.** `:66` says "darkness rather than night precipitation carries the effect". This is [T]'s wording, but the clear-weather-night check only rules out precipitation. It does not separate darkness from other differences at night, such as pedestrian density, scale or scene mix. §4 already denies a causal darkness effect for NightOwls. For consistency, prefer "precipitation does not explain the night effect".

8. **P4. Minor items:**
   - [P] is listed in the sources table (`:17`) but never cited.
   - Fig. 1b has no y-axis label, because the panels do not share the y-axis.
   - Fig. 2a's "BDD val clear day" curve is `clear_curve` from `remedies_trainnight_B.json`. The label is plausible, but the JSON key does not say whether this is the test or the selection split, so it is worth confirming.

## Checks performed

**Numbers.** 40+ numbers spot-checked, all matching:
- **§2 Setup:** 12,477 / 10,635 / 1,842 / 2,376; strata 1,764/2,450 and 3,929/2,843; 51,782 / 7,631 / 42,316.
- **§3.1:** A/C/B/B2 ceilings 0.770/0.762/0.883/0.880; B and B2 rows, including t\* 0.0149 [0.0070, 0.0253], 0.0105, CIs, and night loss 0.132/0.119.
- **§3.1 other strata:** cloud/rain/snow 0.015/0.023/0.013; dawn 0.030 [0.004, 0.055]; 16.19 FPPI.
- **§3.1, ≥50 px:** the full H50 table; t\* 0.1114/0.2399/0.1220; 945/1,181; 0.906/0.773; ≥32 px 0.826/0.634.
- **§3.2:** the full composition table against [R] lines 29–38. 1 − M_night 0.293/0.170/0.275/0.177; ceiling differences 0.088/0.067/0.062/0.068.
- **§3.2 sensitivity:** 0.042/0.090, 0.089/0.043, minimum 0.030, 30–45%.
- **§3.3:** +0.094 [0.075, 0.113], +0.113 [0.093, 0.134], +0.001, +0.008, −0.027 [−0.053, −0.005]; C − A −0.026 / +0.028 at L1; B2 − B +0.001 / −0.033 / −0.034.
- **§3.4:** equal-FPPI 4.79 (4.34), +0.044 [0.031, 0.062], 66%/29%; 0.033–0.068; 53–75%; 17–31%; 0.04–0.46.
- **§3.4, continued:** equal-recall 0.813/20.96, +0.133 [0.086, 0.170], 862 = 1000 − 138, up to +0.139, B2 0.796/17.22; Platt +0.009, ≤0.012; 232/1,000.
- **§3.5 ACDC:** 0.48–0.75; 0.54–0.63; night B 0.477 vs 0.595 and B2 0.542 vs 0.625; 3,009 images.
- **§3.6 NightOwls:** every table cell; 16.28/15.00/14.49 and 5.98/6.12/6.14; any-IoU 0.3 9.32/11.79 and 9.03/11.59 (correctly paired); 34.69/45.88; 4,994 (65.4%); R3-out 46.87/50.74/49.41.
- **§3.6, continued:** interval widths 26–30 points; 336/1,000; 126 multisets; IID 57.66–62.48; A − C −2.36 [−4.35, −0.98]; Reasonable_small reversal.
- **Compute:** 5.06 + 32.38 + 23.48 = 60.92.

**Claims vs. reviewed sources.**
- The erratum distinction is handled correctly at `:41`, `:80` and `:153`.
- The disagreement between the seed pairs is stated (`:101`, `:155`), and the earlier A/B-only claim is noted as withdrawn.
- Remedies are called calibration targets, with test values and budget exceedances shown (`:111`, `:157`).
- ACDC is labelled descriptive, with no intervals (`:129`, `:158`).
- R3 dominance and unvalidated coverage are stated (`:143`, `:160`).
- The preregistered/exploratory table (`:43–49`) matches [T] and [N]. B is correctly attributed to amendment 1, and the ≥50 px reselection is labelled post hoc on BDD.

**Figures.** I ran the script on a scratch copy of the committed aggregates with `tmp/pdfs/venv`. All four PNGs regenerated **byte-identically** (SHA-256 prefixes f9cc7fc3…, 9a2ca107…, 945ea95c…, 65494fef…). The Fig. 1c NightOwls bars use `cluster_conditional_unkeyed_recall_*`, which equals the five-key primary interval (37.93–67.26% for A). R3-out uses `dominant_out` (2,637 GT). Fig. 2b correctly skips A/C at t\*(0.80). I inspected all four images. The axes and limits contain every plotted point and nothing is clipped. The only material figure issue is finding 1.

**Threats to validity.** §5 covers:
- the unverified mirror and the legacy labels (`:167`);
- one architecture (`:165`);
- two seeds (`:166`);
- input-scale mismatch (1.25×) and occlusion mismatch (`:170`);
- R3 and recording independence (`:168`).

**Restricted data.** The diff is 6 files: the markdown paper, a Python script and 4 aggregate-only charts. The script reads only committed counts-only aggregates. I found no images, boxes, per-image or recording IDs, or predictions.

**Limits of this review.** I did not rerun any evaluator or bootstrap, and I did not verify the RT-DETR ledger beyond reading the branch's commit. AI review is not the owner's merge approval, and G0 remains pending.
