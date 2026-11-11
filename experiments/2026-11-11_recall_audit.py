"""GPT Sol: bounded CPU development demo of a fixed-pool recall rejection audit.

No inference, installs, policy search, or population generalization. Labels are
available to an oracle only; the sampler receives D and queried (G,T). Seeds,
alpha, eta and policies below are declared before the development run.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import importlib.util
import json
import math
from pathlib import Path
import random
from statistics import median

ALPHA, ETA = .05, .5
SEEDS = tuple(range(20))
POLICIES = ("uniform", "count_mixture")
REPO = Path(__file__).resolve().parents[1]
THRESHOLD = .08221367746591568
BASE = "783dc5a254a536f0b064855e5268956f00bac5c4"
DEFAULT_ROOT = Path("C:/Users/Advait/autonomous-sys-research/outputs/colab")


def sampling_weights(remaining, detections, policy):
    """Integer weights give exact declared probabilities using only frozen D."""
    n = len(remaining)
    total = sum(detections[i] for i in remaining)
    if policy == "uniform" or not total:
        return [1] * n
    if policy != "count_mixture":
        raise ValueError(policy)
    return [total + 4 * n * detections[i] for i in remaining]


def audit(detections, reveal, policy, seed):
    """Finite population, without replacement; complete exact audit oracle.

    At B=0 freeze wealth and check later X for logical contradiction. At B<0
    reject logically. Never divide by or clip a nonpositive budget. Keep any
    wealth crossing but require observed positive eligible GT before rejection.
    """
    remaining = sorted(detections)
    rng = random.Random(seed)
    c = sum(detections.values())
    s = observed_gt = observed_tp = 0
    wealth, crossed, trace = Fraction(1), False, []
    reason = None
    while remaining:
        weights = sampling_weights(remaining, detections, policy)
        total_weight = sum(weights)
        draw = rng.randrange(total_weight)
        for index, weight in enumerate(weights):
            draw -= weight
            if draw < 0:
                break
        image, p = remaining[index], Fraction(weights[index], total_weight)
        budget = c - s  # BEFORE this draw
        assert budget >= 0
        g, t = reveal(image)
        assert isinstance(g, int) and isinstance(t, int) and 0 <= t <= min(g, detections[image])
        x = 9 * (g - t) + detections[image] - t
        if budget > 0:
            wealth *= Fraction(1, 2) + Fraction(1, 2) * x / (p * budget)
            crossed |= wealth >= 20  # exact eta=.5 and alpha=.05
        s += x
        observed_gt += g
        observed_tp += t
        remaining.pop(index)
        if observed_gt > 0:
            if s > c:
                reason = "logical_budget_exceeded"
            elif crossed:
                reason = "wealth_crossing"
        trace.append(dict(image_id=image, p=str(p), budget_before=budget, x=x,
                          g=g, t=t, s=s, log_wealth=math.log(wealth)))
        if reason:
            break
    return dict(seed=seed, queries=len(trace), observed_gt=observed_gt,
                observed_tp=observed_tp, rejected=reason is not None,
                reason=reason or ("undefined_recall" if observed_gt == 0 else "non_rejection"),
                exhausted=not remaining, trace=trace)


def tiny_check():
    """One exact null tree: D=(9,0), G=(9,1), T=(9,0); recall=.90.

    X=(0,9), C=9. Terminal wealth is 1/2 or 41/2; expectation=1.
    A .05 crossing has exact probability 1/40. The boundary X=0 after
    the first X=9 freezes wealth. This checks arithmetic, not general validity.
    """
    f = Fraction
    first_p = (f(39, 40), f(1, 40))
    xs, c = (0, 9), 9
    mean_first = sum(p * (f(1, 2) + f(1, 2) * x / (p * c))
                     for p, x in zip(first_p, xs))
    terminals = []
    for i, (p, x) in enumerate(zip(first_p, xs)):
        wealth = f(1, 2) + f(1, 2) * x / (p * c)
        budget = c - x
        if budget:
            wealth *= f(1, 2) + f(1, 2) * xs[1 - i] / budget
        else:
            assert xs[1 - i] == 0  # no 0/0
        terminals.append(wealth)
    assert mean_first == 1 and terminals == [f(1, 2), f(41, 2)]
    assert sum(p * w for p, w in zip(first_p, terminals)) == 1
    assert sum(p for p, w in zip(first_p, terminals) if w >= 20) == f(1, 40)
    return dict(kind="synthetic_exact_arithmetic", first_expectation="1",
                terminal_wealth=[str(w) for w in terminals], terminal_expectation="1",
                crossing_probability="1/40")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--private-output", type=Path,
                        default=REPO / "outputs/colab/recall_audit_20261111")
    parser.add_argument("--aggregate", type=Path,
                        default=REPO / "docs/gpt/2026-11-11_sol_recall_audit_aggregate.json")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        "completed_pilot", Path(__file__).with_name("2026-11-10_transfer_pilot.py"))
    pilot = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pilot)
    manifest_path = args.root / "empirical_20261110/packet/manifest.json"
    raw_path = args.root / "resolution_20261110/results/yolo11s_maximal.json"
    manifest, raw = pilot.read(manifest_path), pilot.read(raw_path)
    # Retain the identical score prefix before matching; later lower-score rows
    # cannot change earlier greedy matches. Include ignored and zero-area D.
    raw = {**raw, "predictions": [r for r in raw["predictions"] if r["score"] >= THRESHOLD],
           "degenerate_predictions": [r for r in raw.get("degenerate_predictions", [])
                                      if r["score"] >= THRESHOLD]}
    members = [manifest["panels"][k] for k in ("fog", "night", "rain", "snow")]
    panels = dict(source_selection=manifest["panels"]["source_selection"],
                  pooled_adverse={**members[0],
                                  "images": [i for panel in members for i in panel["images"]],
                                  "annotations": [a for panel in members for a in panel["annotations"]]})
    public = dict(researcher="GPT Sol", base=BASE, g0="PENDING",
                  status="seen development panels; source is a known-null fixture",
                  threshold=THRESHOLD, alpha=ALPHA, eta=ETA, seeds=list(SEEDS),
                  policies=list(POLICIES), tiny_check=tiny_check(),
                  input_sha256={"manifest": pilot.sha(manifest_path),
                                "native1280": pilot.sha(raw_path),
                                "pilot_evaluator": pilot.sha(pilot.__file__),
                                "reference_evaluator": pilot.sha(REPO / "src/threshold_transfer/metrics.py")},
                  panels={})
    private = {}
    for name, panel in panels.items():
        ev = pilot.pilot_evaluator(panel, raw)
        rows = ev.operating_point(THRESHOLD)["matches"]
        counts = Counter(r["image_id"] for r in rows)
        gs = Counter(a["image_id"] for a in panel["annotations"]
                     if a["category"] == "human" and not (a["ignore"] or a["iscrowd"]))
        ts = Counter(r["image_id"] for r in rows if r["outcome"] == "TP")
        ds = {i["image_id"]: counts[i["image_id"]] for i in panel["images"]}
        oracle = {i: (gs[i], ts[i]) for i in ds}
        point = ev.operating_point(THRESHOLD)
        # Small fixture anchors only, not repeated native/baseline qualification.
        assert (len(ds), sum(gs.values()), sum(ts.values()), point["fp"]) == (
            (256, 579, 522, 405) if name == "source_selection" else (128, 216, 129, 179))
        stats = dict(images=len(ds), eligible_gt=sum(gs.values()), tp=sum(ts.values()),
                     fp=point["fp"], ignored=point["ignored"], emitted_d=sum(ds.values()),
                     total_x=sum(9 * (gs[i] - ts[i]) + ds[i] - ts[i] for i in ds), policies={})
        private[name] = dict(per_image={i: dict(d=ds[i], g=gs[i], t=ts[i]) for i in ds}, runs={})
        for policy in POLICIES:
            runs = [audit(ds, oracle.__getitem__, policy, seed) for seed in SEEDS]
            private[name]["runs"][policy] = runs
            def summary(key):
                values = [r[key] for r in runs]
                return dict(min=min(values), median=median(values), max=max(values))
            stats["policies"][policy] = dict(
                rejections=sum(r["rejected"] for r in runs),
                non_rejections=sum(not r["rejected"] for r in runs),
                reasons=dict(Counter(r["reason"] for r in runs)),
                queries_all_runs=summary("queries"), observed_gt_all_runs=summary("observed_gt"))
        public["panels"][name] = stats
    pilot.write(args.private_output / "private_runs.json", private)
    pilot.write(args.aggregate, public)
    print(json.dumps(public, indent=2))


if __name__ == "__main__":
    main()
