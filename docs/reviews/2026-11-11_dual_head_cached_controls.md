# Two bounded cached interpretation diagnostics

**GPT Sol, 2026-11-11; post-hoc interpretation only. Primary full-source H4 remains SUPPORT, unchanged.** No new primary hypothesis, threshold replacement or favorable source-subset selection was introduced.

Night target-oracle points maximize TP over whole observed tied-score prefixes at each FP ceiling. On equal TP, choose fewer FP, then the highest boundary. Actual FP may fall below budget; no fractional ties or interpolated points are used. Thresholds below preserve retained score precision.

| FP ceiling / 74 images | Head | TP / actual FP | Oracle threshold |
|---|---|---:|---:|
| 37 (.500 FPPI) | O2O | 42 / 32 | 0.061810001730918884 |
| 37 (.500 FPPI) | O2M | 37 / 28 | 0.10479424148797989 |
| 58 (.784 FPPI) | O2O | 48 / 55 | 0.04165162518620491 |
| 58 (.784 FPPI) | O2M | 44 / 54 | 0.058131467550992966 |

These use target GT and are **NONDEPLOYABLE**. The difference is5TP or4TP under common FP ceilings, compared with11TP at the original source-selected points. Realized FP counts differ. Neither exact-FP equality nor dominance of the entire frontier is established. The original larger gain carries a material FP cost; these two points retain a smaller finite-panel head-pipeline difference without identifying its cause or rescuing H4.

Paired leave-one-SOURCE-image-out deletes each of all256original selection images from both heads, reselects .90 and evaluates unchanged reference/night caches. Fixed per-image matching rows and observed score groups are reused: deletion cannot change another image's matches. No256full rematching runs, resampling, recalibration or inference occurs.

| Deletion diagnostic | Result |
|---|---:|
| Source feasible, O2O / O2M / jointly | 256 / 256 / 256 |
| Reference clause / night clause / entire H4 screen | 256 / 256 / 256 |
| Signed reference gap min / median / max (pp) | 0.568 / 1.515 / 1.894 |
| Signed night gap min / median / max (pp) | 6.667 / 10.476 / 10.476 |
| Changed boundary O2O / O2M / either | 37 / 36 / 39 deletions |
| Changed reference / night gap | 26 / 14 deletions |

The two minimum-night-gap deletions remove8and13eligible source GT; both produce44versus37night TP. Night TP/FP ranges are O2O44–48/38–62 and O2M37–39/35–39. Exact threshold frequencies/ranges and reference counts are in the [aggregate](2026-11-11_dual_head_cached_controls.json). Single-image influence changes magnitude but never the locked screen in this sensitivity. This is deterministic sensitivity, **not** a bootstrap CI, p-value, independent replicate or evidence about other source samples. Passing still establishes neither novelty nor architecture causality.

Reproduce with existing Python and `-B experiments/2026-11-11_dual_head_cached_controls.py ROOT PRIVATE_OUTPUT`. ROOT is the retained `outputs/colab/dual_head_20261111/`; private output is `outputs/colab/dual_head_review_20261111/`. The [stdlib script](../../experiments/2026-11-11_dual_head_cached_controls.py) writes public aggregates only; IDs, fixed matching rows and256deletion traces remain private. Final reproduction completed in about6.5seconds on CPU with no new data or inference.
