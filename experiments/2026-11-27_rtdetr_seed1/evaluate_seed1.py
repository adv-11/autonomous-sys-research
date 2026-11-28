"""Claude Opus: evaluate seed-1 arms against seed 0 with the unchanged evaluator.

Same matching, populations, policies and bootstrap draws (rng 20261123) as the seed-0
evaluate.py, so seed-0 numbers are reproduced and seed contrasts are paired. Adds
bootstrap intervals for the decomposition parts and applies the pre-declared readout.
"""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-11-26_local_rtdetr'))
from local import OLD, ORIGINAL  # noqa: E402

ROOT = Path('C:/Users/Advait/autonomous-sys-research')
SEED0 = ROOT / 'outputs/local_rtdetr_20261126'
NEW = ROOT / 'outputs/local_rtdetr_seed1_20261127'
spec = importlib.util.spec_from_file_location('existing_rtdetr_evaluation', ORIGINAL / 'evaluate.py')
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)
POLICIES = {'source_fppi_1': E.choose_fppi,
            **{f'recall_{r}': (lambda p, w=None, r=r: p.select(r, w)) for r in (.8, .9, .95)}}
PARTS = ('held_out_loss', 'ceiling_difference', 'threshold_miss_difference')


def value(d):
    return d['value'] if isinstance(d, dict) else d


def evaluate(path, gt, members, boot):
    with np.load(path) as a:
        names = a['names'].tolist()
        boxes, scores, offsets = a['boxes'], a['scores'], a['offsets']
    assert len(names) == len(set(names)) == len(gt) and set(names) == set(gt)
    predictions = {n: (boxes[offsets[i]:offsets[i+1]], scores[offsets[i]:offsets[i+1]]) for i, n in enumerate(names)}
    records = {}
    for begin in range(0, len(names), 400):
        records.update(E.match(names[begin:begin+400], gt, predictions)[0])
    pops = {s: E.Population([records[n] for n in m]) for s, m in members.items()}
    sel = pops['selection']
    ceil_reps = {s: [pops[s].point(None, w)['recall'] for w in boot[s]] for s in ('clear_day', 'night')}
    arm = dict(prediction_sha256=E.hashlib.sha256(path.read_bytes()).hexdigest(), strata={}, operating_points={})
    for s, pop in pops.items():
        arm['strata'][s] = dict(ceiling=pop.point(None), ceiling_by_height=pop.by_height(None))
    reps = {}
    for policy, select in POLICIES.items():
        threshold = select(sel)
        thresholds = [select(sel, w) for w in boot['selection']]
        op = dict(threshold=threshold, status='FEASIBLE' if threshold is not None else 'INFEASIBLE_SOURCE',
                  bootstrap_infeasible=sum(t is None for t in thresholds), conditions={})
        reps[policy] = {}
        if threshold is not None:
            op['selection'] = sel.point(threshold)
            rep = {s: [pops[s].point(t, boot[s][b]) if t is not None else None for b, t in enumerate(thresholds)]
                   for s in ('clear_day', 'night')}
            decomp = [E.held_out_loss_decomposition(c['recall'], n['recall'], ceil_reps['clear_day'][b],
                                                    ceil_reps['night'][b])
                      for b, (c, n) in enumerate(zip(rep['clear_day'], rep['night'])) if c is not None]
            for s in ('clear_day', 'night'):
                point = pops[s].point(threshold)
                for metric in ('recall', 'fppi'):
                    point[metric+'_ci'] = E.ci([r[metric] for r in rep[s] if r is not None])
                op['conditions'][s] = point
            night = op['conditions']['night']
            night['decomposition'] = E.held_out_loss_decomposition(
                op['conditions']['clear_day']['recall'], night['recall'],
                pops['clear_day'].point(None)['recall'], pops['night'].point(None)['recall'])
            night['decomposition_ci'] = {k: E.ci([value(d[k]) for d in decomp]) for k in PARTS}
            night['threshold_removable_miss_share'] = pops['night'].point(None)['recall'] - night['recall']
            reps[policy] = dict(rep, decomposition=[None if c is None else
                                E.held_out_loss_decomposition(c['recall'], n['recall'], ceil_reps['clear_day'][b],
                                                              ceil_reps['night'][b])
                                for b, (c, n) in enumerate(zip(rep['clear_day'], rep['night']))])
        arm['operating_points'][policy] = op
    for s in ('selection', 'clear_day', 'night'):
        np.savez_compressed(path.parent / f'{path.stem.replace("_pedestrian", "")}_{s}_curve.npz', **E.curve(pops[s]))
    return arm, reps


def contrast(a, b, ra, rb, policy):
    """b minus a on paired draws."""
    out = {}
    if not ra.get(policy) or not rb.get(policy):
        return out
    for s in ('clear_day', 'night'):
        out[s] = {}
        for metric in ('recall', 'fppi'):
            delta = [y[metric]-x[metric] for x, y in zip(ra[policy][s], rb[policy][s]) if x and y]
            out[s][metric] = dict(difference=b['operating_points'][policy]['conditions'][s][metric]
                                  - a['operating_points'][policy]['conditions'][s][metric], ci=E.ci(delta))
    for k in PARTS:
        delta = [value(y[k])-value(x[k]) for x, y in zip(ra[policy]['decomposition'], rb[policy]['decomposition'])
                 if x and y]
        out.setdefault('night_decomposition', {})[k] = dict(
            difference=value(b['operating_points'][policy]['conditions']['night']['decomposition'][k])
            - value(a['operating_points'][policy]['conditions']['night']['decomposition'][k]), ci=E.ci(delta))
    return out


def readout(arm1, arm0):
    """Pre-declared rules (plan 2026-11-27), at the source FPPI <= 1 threshold."""
    n1 = arm1['operating_points']['source_fppi_1']['conditions']['night']
    n0 = arm0['operating_points']['source_fppi_1']['conditions']['night']
    c1, t1 = (value(n1['decomposition'][k]) for k in PARTS[1:])
    c0, t0 = (value(n0['decomposition'][k]) for k in PARTS[1:])
    excludes = all(lo > 0 or hi < 0 for lo, hi in (n1['decomposition_ci'][k] for k in PARTS[1:]))
    moved = max(abs(c1-c0), abs(t1-t0))
    flipped = (c1 > t1) != (c0 > t0)
    if moved >= .03 or flipped:
        verdict = 'SPLIT_SEED_SENSITIVE'
    elif excludes and c1 > t1:
        verdict = 'SPLIT_REPRODUCED'
    else:
        verdict = 'INCONCLUSIVE'
    selection_ceiling = arm1['strata']['selection']['ceiling']['recall']
    return dict(verdict=verdict, seed1=dict(ceiling=c1, threshold=t1), seed0=dict(ceiling=c0, threshold=t0),
                largest_component_move=moved, order_flipped=flipped, seed1_intervals_exclude_zero=excludes,
                selection_ceiling=selection_ceiling, undertraining_flag=selection_ceiling < .85)


def main():
    gt = json.loads((OLD / 'gt_pedestrian.json').read_text())
    members = {}
    for n in sorted(gt):
        members.setdefault('selection' if gt[n]['role'] == 'selection' else gt[n]['stratum'], []).append(n)
    rng = np.random.default_rng(20261123)
    boot = {s: [np.bincount(rng.integers(0, len(m), len(m)), minlength=len(m)) for _ in range(1000)]
            for s, m in members.items() if s in ('selection', 'clear_day', 'night')}
    result = dict(researcher='Claude Opus', scope='Seed-1 replicate; exploratory; G0 pending',
                  evaluator='Unchanged ReferenceEvaluator via seed-0 evaluate helpers',
                  bootstrap='1000 paired image replicates, rng 20261123 (same draws as seed 0)', arms={}, paired={})
    reps = {}
    arms = [('seed0_baseline', SEED0 / 'baseline_pedestrian.npz')]
    for folder in ('main', 'substitute'):
        for arm in ('baseline', 'day_control', 'adaptation'):
            path = NEW / folder / f'{arm}_pedestrian.npz'
            if path.exists():
                arms.append((f'seed1_{folder}_{arm}', path))
    for label, path in arms:
        result['arms'][label], reps[label] = evaluate(path, gt, members, boot)
        print(json.dumps(dict(evaluated=label)), flush=True)
    published = json.loads((SEED0 / 'results.json').read_text())['arms']['baseline']
    t0 = result['arms']['seed0_baseline']['operating_points']['source_fppi_1']['threshold']
    result['seed0_reproduction'] = dict(threshold=t0, published=published['operating_points']['source_fppi_1']['threshold'],
                                        match=abs(t0 - published['operating_points']['source_fppi_1']['threshold']) < 1e-9)
    pairs = [('seed0_baseline', 'seed1_main_baseline'), ('seed1_main_day_control', 'seed1_main_adaptation'),
             ('seed1_substitute_day_control', 'seed1_substitute_adaptation')]
    for a, b in pairs:
        if a in reps and b in reps:
            result['paired'][f'{b}_minus_{a}'] = {p: contrast(result['arms'][a], result['arms'][b], reps[a], reps[b], p)
                                                  for p in POLICIES}
    if 'seed1_main_baseline' in result['arms']:
        result['readout'] = readout(result['arms']['seed1_main_baseline'], result['arms']['seed0_baseline'])
    (NEW / 'results.json').write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps(result.get('readout', {}), indent=2))


if __name__ == '__main__':
    main()
