"""GPT Sol: locked, CPU-only partial-feedback development audit; no inference.

Reuse the complete audit's private counts/runs and unchanged native matcher.
Only omissions are simulated. Labels are a cost proxy, not annotation time.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import random
from statistics import median

REPO = Path(__file__).resolve().parents[1]
ROOT = Path("C:/Users/Advait/autonomous-sys-research/outputs/colab")
BASE = "f825d50f8c9203e4f0944329c5d4df2e332b54f6"
HASH_SEED = "sol-partial-audit-2026-11-11-v1"
REGIMES = ("complete", "hash_half", "omit_one_matched_per_image")


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


complete = load_module("complete_audit", "2026-11-11_recall_audit.py")
pilot = load_module("completed_pilot", "2026-11-10_transfer_pilot.py")


def audit(detections, reveal, policy, seed, max_queries=None):
    """Sampler receives only frozen D and queried (eligible-label count, FN LB).

    Images are drawn once; latent complete outcomes never enter this function.
    Exact integer draws and rational wealth match the complete-audit settings.
    """
    remaining = sorted(detections)
    rng = random.Random(seed)
    c, s, labels = sum(detections.values()), 0, 0
    wealth, trace, reason = Fraction(1), [], None
    limit = len(remaining) if max_queries is None else max_queries
    assert isinstance(limit, int) and limit >= 0
    while remaining and len(trace) < limit:
        weights = complete.sampling_weights(remaining, detections, policy)
        total_weight = sum(weights)
        draw = rng.randrange(total_weight)
        for index, weight in enumerate(weights):
            draw -= weight
            if draw < 0:
                break
        image, p = remaining[index], Fraction(weights[index], total_weight)
        budget = c - s  # pre-draw observed lower-bound budget
        assert budget >= 0
        g, f = reveal(image)
        assert isinstance(g, int) and isinstance(f, int) and 0 <= f <= g
        y = 9 * f
        if budget > 0:
            wealth *= Fraction(1, 2) + Fraction(1, 2) * y / (p * budget)
        s += y
        labels += g
        remaining.pop(index)
        if s > c:
            reason = "logical_budget_exceeded"
        elif wealth >= 20:
            reason = "wealth_crossing"
        # Either rejection implies a positive verified FN, hence positive GT.
        trace.append(dict(image_id=image, p=str(p), budget_before=budget,
                          observed_gt=g, f=f, y=y, s=s, wealth=str(wealth)))
        if reason:
            break
    return dict(seed=seed, queries=len(trace), observed_gt=labels,
                rejected=reason is not None, reason=reason or "non_rejection",
                exhausted=not remaining, trace=trace)


def boundary_checks():
    """Two synthetic matcher examples and the nonpositive-budget boundaries.

    These check proof boundaries, not empirical performance or nominal error.
    """
    def gt(identifier, box):
        return dict(annotation_id=identifier, image_id="i", category="human",
                    bbox=box, ignore=False, iscrowd=False)

    def pred(identifier, box, score):
        return dict(candidate_id=identifier, image_id="i", category="human",
                    bbox=box, score=score)

    def point(gts, preds):
        panel = dict(schema_version=pilot.PY_SCHEMA, provenance={},
                     images=[dict(image_id="i", width=100, height=10)], annotations=gts)
        raw = dict(predictions=preds, provenance=dict(evaluated_image_ids=["i"]))
        return pilot.pilot_evaluator(panel, raw).operating_point()

    # Earlier .90-null counterexample: omit exactly one TP, retain the one FN.
    gts = [gt(str(i), [4 * i, 0, 2, 2]) for i in range(10)]
    preds = [pred(str(i), g["bbox"], .9) for i, g in enumerate(gts[:9])]
    full, partial = point(gts, preds), point(gts[1:], preds)
    assert (full["tp"], full["fn"], partial["tp"], partial["fn"]) == (9, 1, 8, 1)
    assert 9 * partial["fn"] == 9  # conservative Y=C
    assert 9 * partial["fn"] + 9 - partial["tp"] == 10  # INVALID naive X>C
    # Deletion PLUS changing a retained tie ID violates the lemma's premise.
    a, b, c = gt("b", [0, 0, 2, 2]), gt("a", [1, 0, 2, 2]), gt("c", [10, 0, 2, 2])
    preds = [pred("p1", [.5, 0, 2, 2], .9), pred("p2", a["bbox"], .8),
             pred("p3", c["bbox"], .7)]
    assert point([a, b, c], preds)["fn"] == point([a, b], preds)["fn"] == 0
    assert point([a, {**b, "annotation_id": "z"}], preds)["fn"] == 1
    assert audit({}, lambda _: (0, 0), "uniform", 0)["queries"] == 0
    assert audit({"i": 0}, lambda _: (1, 1), "uniform", 0)["reason"] == "logical_budget_exceeded"
    assert not audit({"i": 0}, lambda _: (0, 0), "uniform", 0)["rejected"]
    assert audit({"i": 1}, lambda _: (0, 0), "uniform", 0, 0)["queries"] == 0
    # B reaches zero; later positive Y must reject without division by zero.
    checked = audit({"a": 9, "b": 0}, lambda _: (1, 1), "uniform", 1)
    assert checked["queries"] == 2 and checked["reason"] == "logical_budget_exceeded"
    return dict(kind="synthetic_proof_boundaries", omitted_tp=dict(c=9, complete_x=9,
                conservative_y=9, invalid_naive_partial_x=10), changed_tie_id_fn=[0, 1],
                zero_budget_and_exhaustion="passed")


def summarize(runs):
    return dict(non_rejections=sum(not r["rejected"] for r in runs),
                reasons=dict(Counter(r["reason"] for r in runs)),
                **{key: dict(min=min(values), median=median(values), max=max(values))
                   for key in ("queries", "observed_gt")
                   for values in [[r[key] for r in runs]]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--complete-cache", type=Path,
                        default=ROOT / "recall_audit_20261111/private_runs.json")
    parser.add_argument("--private-output", type=Path,
                        default=REPO / "outputs/colab/partial_audit_20261111/private_runs.json")
    parser.add_argument("--aggregate", type=Path,
                        default=REPO / "docs/gpt/2026-11-11_sol_partial_audit_aggregate.json")
    args = parser.parse_args()
    checks = boundary_checks()
    reference_path = REPO / "docs/gpt/2026-11-11_sol_recall_audit_aggregate.json"
    reference, cached = pilot.read(reference_path), pilot.read(args.complete_cache)
    manifest_path = args.root / "empirical_20261110/packet/manifest.json"
    raw_path = args.root / "resolution_20261110/results/yolo11s_maximal.json"
    hashes = dict(manifest=pilot.sha(manifest_path), native1280=pilot.sha(raw_path),
                  pilot_evaluator=pilot.sha(pilot.__file__),
                  reference_evaluator=pilot.sha(REPO / "src/threshold_transfer/metrics.py"))
    assert hashes == reference["input_sha256"]
    manifest, raw = pilot.read(manifest_path), pilot.read(raw_path)
    raw = {**raw, **{key: [p for p in raw.get(key, []) if p["score"] >= complete.THRESHOLD]
                     for key in ("predictions", "degenerate_predictions")}}
    adverse = [manifest["panels"][k] for k in ("fog", "night", "rain", "snow")]
    panels = dict(source_selection=manifest["panels"]["source_selection"],
                  pooled_adverse={**adverse[0], **{key: [r for p in adverse for r in p[key]]
                                                 for key in ("images", "annotations")}})
    public = dict(researcher="GPT Sol", base=BASE, g0="PENDING",
                  status="already-seen development panels; no nominal-error validation",
                  threshold=complete.THRESHOLD, alpha=complete.ALPHA, eta=complete.ETA,
                  seeds=list(complete.SEEDS), policies=list(complete.POLICIES),
                  regimes=list(REGIMES), hash_seed=HASH_SEED, checks=checks,
                  input_sha256={**hashes, "complete_cache": pilot.sha(args.complete_cache),
                                "complete_reference": pilot.sha(reference_path)}, panels={})
    private = {}
    for name, panel in panels.items():
        exact = cached[name]["per_image"]
        ds = {i: r["d"] for i, r in exact.items()}
        # Recover match IDs for the omission stress fixture, not new baselines.
        full_rows = pilot.pilot_evaluator(panel, raw).rows
        assert Counter(r["image_id"] for r in full_rows) == Counter(ds)
        matched = {}
        full_ts = Counter()
        for row in full_rows:
            if row["outcome"] == "TP":
                full_ts[row["image_id"]] += 1
                matched.setdefault(row["image_id"], []).append(row["annotation_id"])
        assert all(full_ts[i] == r["t"] for i, r in exact.items())
        omitted = {min(ids) for ids in matched.values()}
        eligible = {a["annotation_id"] for a in panel["annotations"]
                    if a["category"] == "human" and not (a["ignore"] or a["iscrowd"])}
        full_gs = Counter(a["image_id"] for a in panel["annotations"] if a["annotation_id"] in eligible)
        assert all(full_gs[i] == r["g"] for i, r in exact.items())
        public["panels"][name] = dict(images=len(ds), c=sum(ds.values()),
            complete_fn=sum(r["g"] - r["t"] for r in exact.values()),
            complete_x_reference={policy: summarize(cached[name]["runs"][policy])
                                  for policy in complete.POLICIES}, regimes={})
        # Check reused reference summaries rather than rerunning complete-X.
        for policy in complete.POLICIES:
            old = reference["panels"][name]["policies"][policy]
            new = public["panels"][name]["complete_x_reference"][policy]
            assert new["non_rejections"] == old["non_rejections"]
            assert new["queries"] == old["queries_all_runs"]
            assert new["observed_gt"] == old["observed_gt_all_runs"]
        private[name] = {}
        for regime in REGIMES:
            if regime == "complete":
                outcomes = {i: (r["g"], r["g"] - r["t"]) for i, r in exact.items()}
                retained_ids = eligible
            else:
                retained_ids = {i for i in eligible if (
                    hashlib.sha256((HASH_SEED + "\n" + i).encode()).digest()[0] < 128
                    if regime == "hash_half" else i not in omitted)}
                # Keep every ignored/other-class row and every retained GT field.
                partial = {**panel, "annotations": [a for a in panel["annotations"]
                           if a["annotation_id"] not in eligible or a["annotation_id"] in retained_ids]}
                rows = pilot.pilot_evaluator(partial, raw).rows
                assert Counter(r["image_id"] for r in rows) == Counter(ds)
                gs = Counter(a["image_id"] for a in partial["annotations"]
                             if a["annotation_id"] in retained_ids)
                ts = Counter(r["image_id"] for r in rows if r["outcome"] == "TP")
                outcomes = {i: (gs[i], gs[i] - ts[i]) for i in ds}
            assert all(0 <= f <= exact[i]["g"] - exact[i]["t"] for i, (_, f) in outcomes.items())
            stats = dict(eligible_labels=len(retained_ids), total_f=sum(f for _, f in outcomes.values()),
                         total_y=sum(9 * f for _, f in outcomes.values()), policies={})
            private[name][regime] = dict(retained_ids=sorted(retained_ids), outcomes=outcomes, runs={})
            for policy in complete.POLICIES:
                runs = [audit(ds, outcomes.__getitem__, policy, seed) for seed in complete.SEEDS]
                private[name][regime]["runs"][policy] = runs
                stats["policies"][policy] = summarize(runs)
            public["panels"][name]["regimes"][regime] = stats
    pilot.write(args.private_output, private)
    pilot.write(args.aggregate, public)
    print(json.dumps(public, indent=2))


if __name__ == "__main__":
    main()
