# Head contrast: shift × boundary density, not a night-specific ranking signal

**Claude Opus 5.5, 2026-11-13.** Posthoc CPU diagnosis of earlier GPT Sol Stage A outputs (zero inference), plus one direction and scoped-G0 proposal. G0 stays pending. This note claims no novel method, causal darkness effect, generalisation or gate pass, and it has not yet been independently reviewed.

## Question and method

Under one common bundle, does O2O rank the night GT that *both* heads can detect earlier than O2M, and is that night-specific? The existing evaluator's greedy prefix matching gives each GT an **entry score**: the GT is a TP at threshold *t* exactly when its entry score is at least *t*. Two frozen maps put each head on a common scale:

- *r*: source recall at that score. It comes from the COCO `source_selection` panel only, is monotone and involves no reselection, so no single-head operating set changes.
- *f*: target-panel FPPI at that score. It is descriptive only.

The direct head TP gap at the original thresholds (.0383/.0757) splits exactly into **ranking** and **availability**. Ranking counts jointly ceiling-covered GT that one head admits and the other covers only below its threshold. Availability counts GT absent from the other head's ceiling. All 80 saved Stage A TP/FP/ignored counts reproduce, and the identity is asserted for every panel.

![Measured diagnosis](2026-11-13_opus_cached_mechanism.png)

## Result (common N; the [aggregate](2026-11-13_opus_cached_mechanism.json) adds K, native and all normal references)

| Panel | GT | Jointly covered | O2O−O2M TP = rank + avail | Earlier *r* O2O : O2M (ties) | Median *r* O2O / O2M | Lower *f* O2O : O2M (ties) | Median *f* O2O / O2M |
|---|---:|---:|---:|---:|---:|---:|---:|
| COCO ref | 528 | 496 | 7 = 9 − 2 | 276 : 209 (11) | .587 / .582 | 308 : 133 (55) | .102 / .090 |
| Fog | 46 | 42 | −1 = 0 − 1 | 34 : 8 (0) | .623 / .642 | 7 : 7 (28) | 0 / 0 |
| **Night** | 105 | 70 | **11 = 10 + 1** | 47 : 20 (3) | .829 / .877 | 28 : 18 (24) | .155 / .358 |
| Rain | 102 | 83 | −2 = −2 + 0 | 53 : 29 (1) | .803 / .788 | 29 : 31 (23) | .206 / .132 |
| Snow | 98 | 90 | 4 = 4 + 0 | 66 : 21 (3) | .692 / .710 | 39 : 17 (34) | .022 / .044 |
| Night-normal | 199 | 149 | 7 = 6 + 1 | **121 : 27** (1) | .667 / .710 | 52 : 35 (62) | .024 / .049 |

1. **Ranking, not availability, drives the night gap.** Under N, 10 of 11 night TP come from jointly covered GT that O2O admits and O2M covers only below its threshold; the reverse count is zero. K gives 8 = 8 + 0 and native 11 = 10 + 1.
2. **The earlier rank is not night-specific.** O2O ranks jointly covered GT earlier in every ACDC panel (65–82% of non-tied pairs), against 57% on the COCO reference. The paired daytime references show it at least as strongly: night-normal 121 : 27 versus night 47 : 20.
3. **Boundary density turns that shift into night's larger gap.** Night's jointly covered GT have the highest median ranks: O2M sits at .877, just below its .902 boundary, while night-normal and COCO sit at .71 and .58. A similar per-object shift therefore moves more night GT across the boundary.
4. **Target FP cost is mixed.** Under N, O2O admits night GT at lower FPPI (28 : 18), and the COCO reference agrees (308 : 133), but rain reverses (29 : 31). Under K, the 75 : 1 count reflects O2M's 461-FP inflation. Matched-FPPI improvement is not supported.

**Conditioning limits.** Joint coverage excludes 35 of the 105 night GT. Entry scores depend on greedy neighbour competition and on each cell's candidate set. *r* resolves only to source-entry steps, so a rank-only count finds 8 of the 10 exact gains. The 74 night images come from overlapping ACDC recordings: there are no IID intervals and no independent-scene confirmation. The shift appearing in paired normal references argues against a darkness-specific account but cannot establish any causal account.

## Decision

Recommendation: stop pursuing a night-specific head-ranking signal as a method direction. The evidence indicates a domain-general source-rank shift whose recall consequence depends on where target GT sit relative to the source boundary. The scoped, falsifiable claim describes a frozen checkpoint rather than a method:

> Under common N, O2O places jointly covered adverse-domain GT earlier than O2M on each head's frozen source-recall scale, and the original-threshold TP gap is ranking-dominated.

## One decisive experiment (conditional)

The experiment is a frozen replication on NightOwls validation. GPT Sol established that the official public validation JSON (10.7 MB) and image ZIP (57.5 GB) links exist. No terms have been accepted, and no payload, schema, sequence IDs or counts have been inspected. Acceptance is pending through the coordinator, so the experiment is **not yet available**.

- **Roles:**
  - Source: the unchanged COCO `source_selection` panel. It supplies the thresholds and the *r* maps.
  - Fit and selection: none.
  - Test: NightOwls validation night frames, grouped by recording sequence.
  - References: COCO and ACDC, already seen and never used as test.
- **Baseline and closest prior work:** O2M with N at its original threshold. Opus recalls that YOLOv10's consistent dual assignments and H-DETR's hybrid matching already study O2O/O2M head relationships; this was not verified against primary sources here. This experiment tests threshold transfer, not head design.
- **H1:** pooled O2O-earlier exceeds O2M-earlier among jointly covered eligible pedestrians, and does so in a majority of sequences that have at least 10 such GT. **H2:** the direct TP gap is positive and its ranking part is at least the absolute availability part. Failing either one falsifies the claim, and failing H1 closes the head-contrast direction for this checkpoint.
- **Stop:** one frozen pass with every outcome reported, nulls included. No NightOwls reselection, tuning or second pass. *f* is secondary because people under 50 px are unannotated.

### Scoped G0 proposal (this claim only)

```json
{"claim":"frozen-checkpoint descriptive head contrast; not a method","checkpoint_sha256":"646f8bc3…db384a1b","ultralytics":"8.4.197",
 "cells":["o2o_N","o2m_N"],"thresholds":{"o2o":0.0383278951,"o2m":0.0756601393},"rank_map_source":"manifest_A cd966fb7… source_selection",
 "test":"NightOwls val, night frames, >=1 eligible GT","primary_GT":"pedestrian; riders secondary pending extent audit",
 "unit":"recording sequence","minimum":{"eligible_GT":150,"sequences":5},
 "controls":["exact native replay first batch","evaluator fa58a9e2…","JSON SHA pinned before images"],"G0":"PENDING"}
```

**Blocking prerequisites for this claim:**

1. My licence acceptance, recorded through the coordinator.
2. A CPU audit of the JSON (sequence IDs, night selection, classes, ignore regions), with all rules frozen before any images arrive.
3. A verified image-acquisition route. The JSON alone does not allow inference.
4. A coordinator-owned, bounded allocation for the two N cells.

**Historical blockers that do not apply:** BDD revised-label provenance (the original primary study), RTX 5060 training smoke tests and ACDC independent-scene confirmation. The only owner input needed is the already-requested licence acceptance and, if the JSON audit passes, an approved acquisition size.

## Exchange and provenance

The [exchange record](2026-11-13_opus_direction.exchange.json) holds the actual messages: the Opus data-contract question and Sol's two findings. Opus adopted the findings as a conditional dependency. To reproduce, run `python -B experiments/2026-11-13_opus_cached_mechanism.py ROOT` with `PYTHONPATH=src` and ROOT set to the private `head_policy_20261113` root; the run takes 8.6 CPU seconds. The JSON records the SHA256 of the script, evaluator, manifest, evidence and private rows, and per-GT rows stay under the ignored `outputs/opus_cached_mechanism_20261113/`. No GPU, download, install or paid compute was used.
