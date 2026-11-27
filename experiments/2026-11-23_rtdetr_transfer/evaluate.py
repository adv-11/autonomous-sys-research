"""GPT Sol: CPU evaluation, reusing the unchanged project ReferenceEvaluator.

Reuses Claude Opus's tested Population/select_fppi aggregation. Native DETR boxes
use the existing allow_outside evaluator option, without clipping or NMS.
"""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path('C:/Users/Advait/autonomous-sys-research')
OUT = ROOT / 'outputs/rtdetr_transfer_20261123'
OLD = ROOT / 'outputs/bdd_transfer_20261115/private'
sys.path[:0] = [str(HERE.parents[1] / 'src'), str(HERE.parent / '2026-11-15_bdd_clearday_transfer')]
from threshold_transfer.metrics import ReferenceEvaluator, held_out_loss_decomposition
from evaluate_transfer import Population, ci
from matched_fppi import select_fppi


def match(names, gt, predictions):
    images, annotations, candidates, zero = [], [], [], {}
    recs = {}
    for name in names:
        images.append({'image_id': name, 'width': 1280, 'height': 720})
        peds = gt[name]['peds']
        for k, (x1, y1, x2, y2) in enumerate(peds):
            annotations.append({'annotation_id': f'{name}#g{k}', 'image_id': name,
                                'category': 'pedestrian', 'bbox': [x1, y1, x2-x1, y2-y1],
                                'ignore': False, 'iscrowd': False})
        boxes, scores = predictions[name]
        zero[name] = []
        for k, (box, score) in enumerate(zip(boxes, scores)):
            x1, y1, x2, y2 = map(float, box)
            assert x2 >= x1 and y2 >= y1
            if x1 == x2 or y1 == y2:
                zero[name].append(float(score))
            else:
                candidates.append({'candidate_id': f'{name}#p{k:05d}', 'image_id': name,
                                   'category': 'pedestrian', 'bbox': [x1, y1, x2-x1, y2-y1], 'score': float(score)})
        recs[name] = {'tp': [], 'fp': zero[name], 'zero': len(zero[name]), 'ignored': 0,
                      'gt_h': [p[3]-p[1] for p in peds], 'gt_match': [None]*len(peds)}
    ev = ReferenceEvaluator({'schema_version': 'threshold-transfer-v1', 'images': images,
                             'annotations': annotations, 'provenance': {}},
                            {'schema_version': 'threshold-transfer-v1', 'predictions': candidates,
                             'provenance': {'evaluated_image_ids': names}},
                            categories=['pedestrian'], ignore_policy='reject', bounds_policy='allow_outside')
    for row in ev.rows:
        record = recs[row['image_id']]
        record['tp' if row['outcome'] == 'TP' else 'fp'].append(row['score'])
        if row['outcome'] == 'TP':
            record['gt_match'][int(row['annotation_id'].split('#g')[1])] = row['score']
    return recs, ev


def curve(pop):
    scores = np.r_[pop.tp_all, pop.fp_all]
    if not len(scores):
        return {k: np.zeros(0) for k in ('thresholds', 'recall', 'fppi')}
    flags = np.r_[np.ones(len(pop.tp_all)), np.zeros(len(pop.fp_all))]
    order = np.argsort(-scores, kind='stable')
    scores, flags = scores[order], flags[order]
    end = np.r_[scores[1:] != scores[:-1], True]
    tp = np.cumsum(flags)[end]
    fp = (np.arange(1, len(flags)+1)-np.cumsum(flags))[end]
    # Aggregate curve retains every distinct boundary privately; display may thin.
    return {'thresholds': scores[end], 'recall': tp/pop.G.sum(), 'fppi': fp/pop.n}


def choose_fppi(pop, weights=None):
    # No observed score boundary exists in a candidate-empty source population.
    return select_fppi(pop, 1.0, weights) if len(pop.tp_all)+len(pop.fp_all) else None


def main():
    gt = json.loads((OLD / 'gt_pedestrian.json').read_text())
    members = {'selection': [], 'clear_day': [], 'night': []}
    for name in sorted(gt):
        group = 'selection' if gt[name]['role'] == 'selection' else gt[name]['stratum']
        members.setdefault(group, []).append(name)
    rng = np.random.default_rng(20261123)
    boot = {s: [np.bincount(rng.integers(0, len(m), len(m)), minlength=len(m)) for _ in range(1000)]
            for s, m in members.items() if s in ('selection', 'clear_day', 'night')}
    result = {'researcher': 'GPT Sol', 'scope': 'Exploratory BDD, fixed single seed per arm; G0 pending',
              'evaluator': 'Unchanged ReferenceEvaluator, IoU0.5, reject ignore, allow_outside native geometry',
              'bootstrap': '1000 image replicates; source/test independent; image draws paired across arms; thresholds reselected',
              'arms': {}, 'paired': {}}
    all_reps = {}
    for arm in ('baseline', 'adaptation'):
        path = OUT / 'evidence' / f'{arm}_pedestrian.npz'
        if not path.exists():
            continue
        with np.load(path) as archive:
            names = archive['names'].tolist()
            boxes, scores, offsets = archive['boxes'], archive['scores'], archive['offsets']
        assert len(names) == len(set(names)) == len(gt) and set(names) == set(gt)
        predictions = {n: (boxes[offsets[i]:offsets[i+1]], scores[offsets[i]:offsets[i+1]]) for i, n in enumerate(names)}
        records = {}
        for begin in range(0, len(names), 400):
            records.update(match(names[begin:begin+400], gt, predictions)[0])
        pops = {s: Population([records[n] for n in members[s]]) for s in members}
        sel = pops['selection']
        ar = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'strata': {}, 'operating_points': {}, 'checks': {}}
        for s, pop in pops.items():
            ar['strata'][s] = {'ceiling': pop.point(None), 'unmatched_share': 1-pop.point(None)['recall'] if pop.G.sum() else None,
                                'zero_area_candidates': int(pop.zero.sum()), 'ceiling_by_height': pop.by_height(None)}
        # Whole-population match/threshold equivalence on source is the meaningful
        # guard against adapting aggregation incorrectly for the new model.
        _, reference = match(members['selection'], gt, predictions)
        for rho in (0.8, 0.9, 0.95):
            actual = reference.select_threshold(rho)
            assert actual['threshold'] == sel.select(rho), (arm, rho)
        ar['checks']['source_full_reference_threshold_equivalence'] = 'PASS'
        policies = {'recall_0.8': lambda p, w=None: p.select(0.8, w),
                    'recall_0.9': lambda p, w=None: p.select(0.9, w),
                    'recall_0.95': lambda p, w=None: p.select(0.95, w),
                    'source_fppi_1': choose_fppi}
        all_reps[arm] = {}
        for policy, select in policies.items():
            threshold = select(sel)
            thresholds = [select(sel, w) for w in boot['selection']]
            op = {'threshold': threshold, 'status': 'FEASIBLE' if threshold is not None else 'INFEASIBLE_SOURCE',
                  'bootstrap_infeasible': sum(t is None for t in thresholds), 'conditions': {}}
            all_reps[arm][policy] = {}
            if threshold is not None:
                op['selection'] = sel.point(threshold)
                for s in ('clear_day', 'night'):
                    pop = pops[s]
                    point = pop.point(threshold)
                    point['decomposition'] = held_out_loss_decomposition(pops['clear_day'].point(threshold)['recall'],
                                                                         point['recall'], pops['clear_day'].point(None)['recall'],
                                                                         pop.point(None)['recall'])
                    point['removable_night_miss_share'] = pop.point(None)['recall']-point['recall']
                    reps = []
                    for b, t in enumerate(thresholds):
                        reps.append(pop.point(t, boot[s][b]) if t is not None else None)
                    for metric in ('recall', 'fppi'):
                        point[metric+'_ci'] = ci([r[metric] for r in reps if r is not None])
                    op['conditions'][s] = point
                    all_reps[arm][policy][s] = reps
            ar['operating_points'][policy] = op
        for s in ('selection', 'clear_day', 'night'):
            np.savez_compressed(OUT / f'{arm}_{s}_curve.npz', **curve(pops[s]))
        result['arms'][arm] = ar
        print(json.dumps({'arm': arm, 'source_ceiling': ar['strata']['selection']['ceiling']['recall'],
                          'night_ceiling': ar['strata']['night']['ceiling']['recall']}), flush=True)
    if 'adaptation' in result['arms']:
        for policy in all_reps['baseline']:
            result['paired'][policy] = {}
            for s in ('clear_day', 'night'):
                if s not in all_reps['baseline'][policy] or s not in all_reps['adaptation'][policy]:
                    continue
                result['paired'][policy][s] = {}
                for metric in ('recall', 'fppi'):
                    a = result['arms']['baseline']['operating_points'][policy]['conditions'][s][metric]
                    b = result['arms']['adaptation']['operating_points'][policy]['conditions'][s][metric]
                    deltas = [bb[metric]-aa[metric] for aa, bb in zip(all_reps['baseline'][policy][s], all_reps['adaptation'][policy][s])
                              if aa is not None and bb is not None]
                    result['paired'][policy][s][metric] = {'adaptation_minus_baseline': b-a, 'ci': ci(deltas),
                                                         'feasible_bootstrap_pairs': len(deltas)}
    (OUT / 'results.json').write_text(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
