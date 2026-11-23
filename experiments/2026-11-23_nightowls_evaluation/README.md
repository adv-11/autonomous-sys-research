# First frozen NightOwls evaluation (GPT Sol)

This experiment scores the saved A/B/C candidates on CPU. It implements the
merged 2026-11-17 contract with the superseding 2026-11-18 v2 amendment. It
does not load models, perform inference, change a policy, or allocate compute.
G0 remains pending. Independent review is a separate coordinator task.

Run from the repository root in PowerShell, with the existing interpreters:

```powershell
$cpuPython = 'C:/Users/Advait/ar-work/venv-rtdetrv2/Scripts/python.exe'
$plotPython = 'C:/Users/Advait/autonomous-sys-research/tmp/pdfs/venv/Scripts/python.exe'
$canonicalBase = 'C:/Users/Advait/autonomous-sys-research'
$experiment = 'experiments/2026-11-23_nightowls_evaluation'
& $cpuPython -u "$experiment/evaluate.py" --base $canonicalBase
& $cpuPython -u "$experiment/uncertainty.py" --base $canonicalBase
& $cpuPython "$experiment/verify.py" --base $canonicalBase
& $plotPython "$experiment/figures.py"
& $cpuPython "$experiment/package_aggregates.py"
```

The committed report was curated separately; `finalize_report.py` filled its
initial pending markers once. That editorial step is not needed to reproduce
the numerical artifacts above.

No installation is required. Scoring uses Python/NumPy plus the unchanged
`ReferenceEvaluator` and BDD `evaluate_transfer.py`; the existing CPU environment
supplies NumPy. Matplotlib is used only by the plot interpreter. Actual versions
and code/input hashes are in the result receipt. Private outputs and trusted
local pickle caches remain under the canonical ignored
`outputs/nightowls_evaluation_20261123/`. Do not load a pickle from an untrusted
source. No image archive extraction is needed: only its ZIP index is read.

`evaluate.py` verifies annotation, pilot and prediction hashes, exact coverage,
the published BDD thresholds and decisive BDD reference points. The target
fast path checks all reported thresholds and oracles against the unchanged
reference on a fixed 1/17 image sample plus every zero-area-candidate image,
for every arm/setup/profile. All evaluated images remain in point estimates.
These are checks on actual saved predictions, not synthetic detector results.

The 1,000 shared bootstrap draws use seed 20261117, in the order recorded in
`uncertainty.json.gz`. Source-selection and clear-reference image draws are
independent of target draws. The primary target bootstrap draws five known
recording keys; pooled unkeyed weights are fixed at one. Known-only reuses
those recording draws with unkeyed weights zero. Dominant-out independently
draws the four remaining known keys and fixes unkeyed weights at one. The IID
sensitivity draws all images with replacement. Every model, policy, eligibility
setup, ignore profile and height bin reuses the relevant paired draw. Source
thresholds and target oracles are reselected on their respective draws.

All ordinary transfer intervals remain undefined for an observed infeasible
source policy, while bootstrap source feasibility is still counted. Oracle
intervals use only feasible target replicates and retain infeasible/zero-GT
counts. Height-bin intervals use full-population GT assignments, not separate
matching. Per-recording tables are point estimates; sequence-majority claims
are not made. No optional target-only-at-fixed-threshold interval was added.

The public results contain counts, scores, ratios, hashes and anonymous R1–R5
labels. Five CSVs provide readable point summaries and paired contrasts. Complete counts-only JSON
is losslessly compressed with deterministic gzip to keep the review diff small;
the manifest records both raw and compressed hashes. For example:

```python
import gzip, json
from pathlib import Path
p = Path('docs/research/2026-11-23_nightowls_evaluation/aggregate.json.gz')
result = json.loads(gzip.decompress(p.read_bytes()))
```

The scripts first persist completed point estimates with uncertainty explicitly
pending. A bootstrap interruption leaves those estimates and partial uncertainty
in private outputs; it must not be reported as complete. The final validation is
one bounded accounting/equivalence/privacy pass, not an independent review or
an empirical validation of bootstrap coverage.
