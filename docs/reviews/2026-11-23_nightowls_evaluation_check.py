"""GPT Sol independent bounded review: trusted private arrays in, counts only out.

No inference, model imports, full evaluator rerun or bootstrap rerun. Importing
the old module only supplies the class definition needed by trusted local pickle.
"""
import collections
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BASE = Path('C:/Users/Advait/autonomous-sys-research')
SOURCE = Path('C:/Users/Advait/.t3/worktrees/autonomous-sys-research/t3-42574f16')
PRIVATE = BASE / 'outputs/nightowls_evaluation_20261123'
PUBLIC = SOURCE / 'docs/research/2026-11-23_nightowls_evaluation'
BDD = BASE / 'outputs/bdd_transfer_20261115'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'experiments/2026-11-15_bdd_clearday_transfer')]
import evaluate_transfer  # trusted pickle class resolution only


def digest(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def eligible(a, setup):
    h = a['bbox'][3]
    visible = .5 if a['occluded'] is True else 1.
    lo, hi, vlo, vhi = {'reasonable': (50, 1e10, .65, 1e10),
        'reasonable_small': (50, 75, .65, 1e10),
        'reasonable_heavy': (50, 1e10, .2, .65), 'all': (20, 1e10, .2, 1e10)}[setup]
    return a['category_id'] == 1 and a['ignore'] == 0 and lo <= h <= hi and vlo <= visible <= vhi


def match(boxes, scores, gt, ignored):
    """Separate eligible-first implementation; IDs supplied in lexical tie order."""
    gt = np.asarray(gt, float).reshape(-1, 4)
    ignored = np.asarray(ignored, float).reshape(-1, 4)
    assigned = np.full(len(gt), np.nan)
    tp, fp, ig = [], [], []
    for j in sorted(range(len(scores)), key=lambda j: (-float(scores[j]), j)):
        b = boxes[j].astype(float)
        area = (b[2] - b[0]) * (b[3] - b[1])
        if area == 0:
            fp.append(float(scores[j]))
            continue
        def overlap(regions):
            wh = np.maximum(0, np.minimum(b[2:], regions[:, :2] + regions[:, 2:]) - np.maximum(b[:2], regions[:, :2]))
            return wh[:, 0] * wh[:, 1]
        inter = overlap(gt)
        iou = inter / ((area - inter) + gt[:, 2] * gt[:, 3])
        iou[np.isfinite(assigned)] = -1
        if len(iou) and max(iou) >= .5:
            assigned[int(np.argmax(iou))] = float(scores[j])
            tp.append(float(scores[j]))
        elif len(ignored) and max(overlap(ignored) / area) >= .5:
            ig.append(float(scores[j]))
        else:
            fp.append(float(scores[j]))
    return assigned, tp, fp, ig


def events(p):
    return p.G, p.tp_all, p.tp_img, p.fp_all, p.fp_img


def select(e, w, rho=.8):
    g, ts, ti, _, _ = e
    denominator = np.dot(w, g)
    if not denominator:
        return None
    # Group equal scores explicitly; zero-multiplicity scores cannot set t*.
    score, inv = np.unique(ts, return_inverse=True)
    mass = np.bincount(inv, weights=w[ti], minlength=len(score))
    cumulative = np.cumsum(mass[::-1])
    k = np.flatnonzero(cumulative >= rho * denominator)
    return float(score[::-1][k[0]]) if len(k) else None


def point(e, w, t):
    g, ts, ti, fs, fi = e
    tp = int(w[ti[ts >= t]].sum()) if t is not None else len(ts)
    fp = int(w[fi[fs >= t]].sum()) if t is not None else len(fs)
    G, n = int(np.dot(w, g)), int(w.sum())
    return dict(tp=tp, fp=fp, gt=G, images=n, recall=tp/G if G else None,
                fppi=fp/n, precision=tp/(tp+fp) if tp+fp else None)


def close(a, b):
    assert a == b or (a is not None and b is not None and abs(a-b) < 1e-12), (a, b)


receipt = json.loads((PUBLIC/'receipt.json').read_bytes())
native_path = BASE/'data/nightowls/annotations/nightowls_validation.json'
pilot_path = BASE/'outputs/nightowls_image_access_pilot_20261113/selection.json'
for path, key in [(native_path, 'annotations'), (pilot_path, 'pilot'), (BDD/'private/gt_pedestrian.json', 'bdd_gt')]:
    assert digest(path) == receipt['hashes'][key]
native = json.loads(native_path.read_bytes())
pilot = {i['id'] for i in json.loads(pilot_path.read_bytes())['images']}
images = [i for i in native['images'] if i['daytime'] == 'night' and i['id'] not in pilot]
anns = collections.defaultdict(list)
for a in native['annotations']:
    anns[a['image_id']].append(a)
keys = sorted({i['recordings_id'] for i in images}-{None}, key=str)
groups = np.array([keys.index(i['recordings_id']) if i['recordings_id'] is not None else 5 for i in images])
assert len(native['images']) == 51848 and len(images) == 51782 and len(pilot) == 64
assert sum(not anns[i['id']] for i in images) == 42316
assert sum(groups == 5) == 1304
assert [sum(eligible(a, 'reasonable') for i,g in zip(images, groups) if g == j for a in anns[i['id']]) for j in range(6)] == [1005,291,4994,332,149,860]
aggregate = json.loads(gzip.decompress((PUBLIC/'aggregate.json.gz').read_bytes()))
assert aggregate == json.loads((PRIVATE/'point_estimates.json').read_bytes())
uncertainty = json.loads(gzip.decompress((PUBLIC/'uncertainty.json.gz').read_bytes()))
assert uncertainty == json.loads((PRIVATE/'uncertainty.json').read_bytes())
draws = np.load(PRIVATE/'bootstrap_draws.npz')
assert np.all(draws['cluster'][:,:5].sum(1) == 5) and np.all(draws['cluster'][:,5] == 1)
assert np.all(draws['known'][:,:5] == draws['cluster'][:,:5]) and not draws['known'][:,5].any()
assert not draws['dominant'][:,2].any() and np.all(draws['dominant'][:,:5].sum(1) == 4) and np.all(draws['dominant'][:,5] == 1)
assert np.all(draws['source'].sum(1) == 1842) and np.all(draws['clear'].sum(1) == 1764)
assert np.all(draws['iid'].sum(1) == 51782)
assert len(set(map(tuple, draws['cluster'][:,:5]))) == 119
assert int((draws['cluster'][:,2] == 0).sum()) == 336
out = {'attribution':'GPT Sol independent review of 02486e7; provisional counts', 'arms':{}}
previous_names = None
joint = None
bgt = json.loads((BDD/'private/gt_pedestrian.json').read_bytes())
for role, stratum, expected in [('selection',None,(1842,1181)),('test','clear_day',(1764,1256)),('test','night',(3929,1616))]:
    keep = [v for v in bgt.values() if (v['role']=='selection' if role=='selection' else v['role']!='selection' and v['stratum']==stratum)]
    assert (len(keep),sum(p[3]-p[1]>=50 for v in keep for p in v['peds'])) == expected
for arm in ('A_640', 'B_1280', 'C_640'):
    print('CHECK', arm, flush=True)
    assert digest(BDD/f'preds/{arm}.npz') == receipt['hashes'][f'bdd_{arm}']
    rawpath = BDD/f'stage2/preds/nightowls_{arm}.npz'
    assert digest(rawpath) == receipt['hashes'][f'nightowls_{arm}']
    z = np.load(rawpath)
    names = z['names'].astype(str).tolist(); offsets = z['offsets']; boxes = z['boxes']; scores = z['scores']
    assert len(set(names)) == 51848 and set(names) == {Path(i['file_name']).name for i in native['images']}
    assert len(scores) == len(boxes) == offsets[-1] and not (z['all_class_candidates'] >= 3000).any()
    assert np.isfinite(boxes).all() and np.isfinite(scores).all() and (boxes[:,2:] >= boxes[:,:2]).all()
    assert (scores >= 1e-4).all()
    index = {n:j for j,n in enumerate(names)}
    ix = np.array([index[Path(i['file_name']).name] for i in images])
    cache = pickle.load(open(PRIVATE/f'{arm}_cache.pkl', 'rb'))
    assert np.array_equal(cache['groups'], np.array(['R1','R2','R3','R4','R5','unkeyed'])[groups])
    bnames = np.load(BDD/f'preds/{arm}.npz')['names']
    if previous_names is not None: assert np.array_equal(bnames, previous_names)
    previous_names = bnames
    recs = cache['panels']['reasonable/unused_nonpedestrian']
    G = np.array([len(r['gt_h']) for r in recs])
    ts = np.concatenate([r['tp'] for r in recs]); fs = np.concatenate([r['fp'] for r in recs])
    e = (G, ts, np.repeat(np.arange(len(recs)), [len(r['tp']) for r in recs]), fs,
         np.repeat(np.arange(len(recs)), [len(r['fp']) for r in recs]))
    primary = aggregate['arms'][arm]['panels']['reasonable/unused_nonpedestrian']
    s = events(cache['selection'][50]); t = select(s, np.ones(1842))
    close(t, primary['pooled']['h50_r0.8']['source_threshold'])
    assert point(s, np.ones(1842), t)['tp'] == 945
    for pname, policy in cache['policies'].items():
        st = select(events(cache['selection'][policy['min_height']]),np.ones(1842),policy['target'])
        assert st == policy['threshold']
        row = primary['pooled'][pname]
        assert (row['operating'] is None) == (st is None)
        for mode in uncertainty['arms'][arm]['panels']['reasonable/unused_nonpedestrian'].values():
            if st is None: assert mode['policies'][pname]['metrics']['recall']['defined'] == 0
    p = point(e, np.ones(51782), t)
    assert p == primary['pooled']['h50_r0.8']['operating']
    removed = len(ts)-p['tp']; missing = 7631-len(ts)
    assert primary['pooled']['h50_r0.8']['misses'] == {'no_matched_candidate':missing,'removed_by_threshold':removed}
    dom = point(e, (groups != 2).astype(int), t)
    assert dom == primary['dominant_out']['h50_r0.8']['operating']
    oracle = select(e, np.ones(51782))
    assert oracle == primary['pooled']['h50_r0.8']['oracle']['threshold']
    if oracle is not None: assert point(e,np.ones(51782),oracle) == primary['pooled']['h50_r0.8']['oracle']['operating']
    emptyfp = sum(int(np.sum(np.asarray(r['fp']) >= t)) for i,r in zip(images,recs) if not anns[i['id']])
    # Bound raw rematching to a different regular sample plus every zero-area image.
    sample = set(range(11,51782,431)) | {j for j,r in enumerate(recs) if r['zero']}
    matched_checks = 0
    for panel, rr in cache['panels'].items():
        setup, profile = panel.split('/')
        eg = sum(eligible(a,setup) for i in images for a in anns[i['id']])
        ig = sum(not eligible(a,setup) for i in images for a in anns[i['id']] if a['category_id']==1 or profile=='person_compatible_ignore')
        row = aggregate['arms'][arm]['panels'][panel]['pooled']['h50_r0.8']
        assert row['eligible_gt']==eg and row['ignored_gt']==ig
        for j,(i,r) in enumerate(zip(images,rr)):
            aa = sorted([a for a in anns[i['id']] if eligible(a,setup)], key=lambda a:f"nightowls:validation:a{a['id']}")
            assert r['gt_ids'] == [f"nightowls:validation:a{a['id']}" for a in aa]
            if j not in sample: continue
            ignored = [a['bbox'] for a in anns[i['id']] if not eligible(a,setup) and (a['category_id']==1 or profile=='person_compatible_ignore')]
            sl = slice(offsets[ix[j]],offsets[ix[j]+1])
            m,tp,fp,absorb = match(boxes[sl],scores[sl],[a['bbox'] for a in aa],ignored)
            assert np.array_equal(m,np.array(r['gt_match'],float),equal_nan=True)
            for a,b in [(tp,r['tp']),(fp,r['fp']),(absorb,r['ig'])]: assert sorted(a)==sorted(b)
            matched_checks += 1
    flat = np.concatenate([np.isfinite(np.asarray(r['gt_match'],float)) for r in recs])
    joint = flat if joint is None else joint & flat
    # Absolute target misses and clear-reference differences have different denominators.
    clear = cache['bdd']['clear']; ce = events(clear)
    co = point(ce,np.ones(1764),t)
    loss = co['recall']-p['recall']
    def ceiling(records, definition):
        if definition in ('any_iou50','any_iou30'):
            field = 'any50' if definition=='any_iou50' else 'any30'
            return sum(np.sum(r[field]) for r in records)/sum(len(r['gt_h']) for r in records)
        return sum(np.sum(np.asarray(r['gt_match'],float)>=1e-3) if definition=='floor1e-3' else np.isfinite(np.asarray(r['gt_match'],float)).sum() for r in records)/sum(len(r['gt_h']) for r in records)
    definitions = {}
    for definition, reported in primary['pooled']['h50_r0.8']['definition_sensitivity'].items():
        nc = ceiling(recs,definition); bc = ceiling(cache['bdd_recs']['clear'],definition)
        close(nc,reported['target_ceiling']); close(bc,reported['clear_ceiling'])
        close(bc-nc,reported['ceiling_difference']); close(loss-(bc-nc),reported['residual_threshold_part'])
        definitions[definition] = [float(bc-nc),float(loss-(bc-nc))]
    sensitivity = aggregate['arms'][arm]['panels']['reasonable/person_compatible_ignore']['pooled']['h50_r0.8']
    assert sensitivity['operating']['tp']==p['tp']
    assert sensitivity['operating']['fp'] < p['fp']
    boot = pickle.load(open(PRIVATE/f'{arm}_bootstrap_metrics.pkl','rb'))
    checked = 0
    for mode,key in [('cluster_conditional_unkeyed','cluster'),('known_only_cluster','known'),('dominant_out_conditional_unkeyed','dominant'),('iid_image_sensitivity','iid')]:
        for b in (1,217,618,998):
            tb = select(s,draws['source'][b]); w = draws[key][b] if key=='iid' else draws[key][b,groups]
            q = point(e,w,tb); c = point(events(cache['bdd']['clear']),draws['clear'][b],tb)
            saved = boot['reasonable/unused_nonpedestrian'][mode]['h50_r0.8']
            for k in ('recall','fppi','precision'): close(q[k],float(saved[k][b]))
            close(c['recall']-q['recall'],float(saved['loss'][b]))
            checked += 1
    ar = dict(threshold=t,operating=p,misses=[missing,removed],dominant_out=dom,
              oracle_threshold=oracle,oracle_fppi=point(e,np.ones(51782),oracle)['fppi'] if oracle else None,
              native_empty_frame_fp=emptyfp,zero_area_candidates=sum(r['zero'] for r in recs),
              definition_difference_parts=definitions,
              raw_matched_images_across_panels=matched_checks,weighted_reselected_points=checked)
    out['arms'][arm] = ar
    print(json.dumps(ar), flush=True)
    del cache,boot,z,boxes,scores
assert [int(joint[np.repeat(groups,G)==j].sum()) for j in range(6)] == [512,236,3933,39,81,626]
# Inspect decompressed public JSON and textual SVGs for native identities/geometry.
restricted = {Path(i['file_name']).name for i in native['images']}
for obj in (aggregate,uncertainty):
    def scan(v):
        if isinstance(v,dict):
            assert not set(v) & {'image_id','annotation_id','candidate_id','gt_ids','gt_match','bbox','boxes','file_name','recordings_id','tracking_id'}
            for x in v.values(): scan(x)
        elif isinstance(v,list):
            for x in v: scan(x)
        elif isinstance(v,str): assert v not in restricted
    scan(obj)
for p in PUBLIC.glob('*.svg'):
    text = p.read_text(encoding='utf-8')
    assert not any(n in text for n in restricted)
assert not {'torch','ultralytics','tensorflow','jax'} & set(sys.modules)
print(json.dumps({'status':'PASS','paired_points':48,'raw_match_images':sum(v['raw_matched_images_across_panels'] for v in out['arms'].values()),'model_frameworks':[]}))
