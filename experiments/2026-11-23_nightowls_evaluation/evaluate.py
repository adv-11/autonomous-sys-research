"""GPT Sol: first frozen NightOwls CPU scoring; private caches, counts-only JSON.

No model/framework imports. ReferenceEvaluator is unchanged. Run with --base
pointing to the canonical checkout; private evidence is written under its outputs.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import pickle
import shutil
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'experiments/2026-11-15_bdd_clearday_transfer'
sys.path[:0] = [str(ROOT / 'src'), str(OLD)]
import numpy as np
import evaluate_transfer as ET
from sensitivity import any_iou_hits
from threshold_transfer.metrics import ReferenceEvaluator, target_gap_decomposition, held_out_loss_decomposition
from threshold_transfer.nightowls import convert_nightowls, SETUPS, V2_PRIMARY_PROFILE, V2_SENSITIVITY_PROFILE

ARMS = ('A_640', 'B_1280', 'C_640')
PROFILES = (V2_PRIMARY_PROFILE, V2_SENSITIVITY_PROFILE)
TARGETS = (.8, .9, .95)
H50 = {'A_640': (.11140981316566467, .0056989616714417934, None),
       'B_1280': (.23994138836860657, .024179309606552124, .0009108111844398081),
       'C_640': (.12197767943143845, .0036546909250319004, None)}
ANNOTATION_SHA = '584c0dc11f0d086fc5bcbaca0385cf2dd9794074f815f2727fbf9a093fd9a9b6'
PILOT_SHA = '4f31e685cd3d2d263448e7faf207d80f7befe8c6738b041c3bc4d6614b5de99a'
BDD_SHA = '37929323cb4943766a163a8ea8bf1e02ba1e244c5ae29fe6cebe02ce5a257bbf'


def sha(p):
    return hashlib.file_digest(open(p, 'rb'), 'sha256').hexdigest()


def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, allow_nan=False), encoding='utf-8')


def load_preds(p, expected):
    assert sha(p) == expected, 'prediction hash mismatch'
    z = np.load(p)
    names = z['names'].astype(str).tolist()
    off, boxes, scores, totals = (z[k] for k in ('offsets', 'boxes', 'scores', 'all_class_candidates'))
    assert len(set(names)) == len(names) and len(off) == len(names) + 1
    assert off[0] == 0 and off[-1] == len(scores) == len(boxes) and np.all(np.diff(off) >= 0)
    assert np.isfinite(boxes).all() and np.isfinite(scores).all()
    assert np.all(boxes[:, 2:] >= boxes[:, :2]) and np.all((scores >= 1e-4) & (scores <= 1))
    return names, {n: (boxes[off[i]:off[i+1]], scores[off[i]:off[i+1]]) for i, n in enumerate(names)}, totals


def fast_image(anns, boxes, scores):
    """Eligible-first greedy IoU; FP/ignore labels vectorized after all TP choices.

    Float64 operations follow metrics._iou's subtraction order. Candidate IDs
    are padded original indices; native canonical annotation IDs break GT ties.
    """
    eligible = sorted((a for a in anns if not a['ignore']), key=lambda a: a['annotation_id'])
    ignored = [a for a in anns if a['ignore']]
    b = boxes.astype(float)
    wh = b[:, 2:] - b[:, :2]
    area = wh[:, 0] * wh[:, 1]
    order = np.lexsort((np.arange(len(scores)), -scores.astype(float)))
    hit = np.zeros(len(scores), bool)
    matches = np.full(len(eligible), np.nan)
    if eligible and len(scores):
        g = np.array([a['bbox'] for a in eligible], float)
        end = g[:, :2] + g[:, 2:]
        d = np.maximum(0, np.minimum(b[:, None, 2:], end) - np.maximum(b[:, None, :2], g[:, :2]))
        inter = d[..., 0] * d[..., 1]
        union = (area[:, None] - inter) + g[:, 2] * g[:, 3]
        iou = np.divide(inter, union, out=np.zeros_like(inter), where=union > 0)
        available = np.ones(len(g), bool)
        for j in order[np.any(iou[order] >= .5, axis=1)]:
            vals = np.where(available, iou[j], -1)
            k = int(np.argmax(vals))
            if vals[k] >= .5:
                hit[j] = True
                available[k] = False
                matches[k] = float(scores[j])
    absorbed = np.zeros(len(scores), bool)
    if ignored and len(scores):
        g = np.array([a['bbox'] for a in ignored], float)
        d = np.maximum(0, np.minimum(b[:, None, 2:], g[:, :2] + g[:, 2:]) - np.maximum(b[:, None, :2], g[:, :2]))
        inter = d[..., 0] * d[..., 1]
        ioa = np.divide(inter, area[:, None], out=np.zeros_like(inter), where=area[:, None] > 0)
        absorbed = (~hit) & np.any(ioa >= .5, axis=1)
    gt_boxes = np.array([[*a['bbox'][:2], a['bbox'][0]+a['bbox'][2], a['bbox'][1]+a['bbox'][3]] for a in eligible]).reshape(-1,4)
    return {'tp': scores[hit].astype(float), 'fp': scores[~hit & ~absorbed].astype(float),
            'ig': scores[absorbed].astype(float), 'ignored': int(absorbed.sum()), 'zero': int((area == 0).sum()),
            'gt_h': [a['bbox'][3] for a in eligible], 'gt_match': matches.tolist(),
            'gt_ids': [a['annotation_id'] for a in eligible],
            'any50': any_iou_hits(gt_boxes, b, .5), 'any30': any_iou_hits(gt_boxes, b, .3)}


def reference_check(images, anns, preds, recs, thresholds):
    """One real-data check, including oracle boundaries and explicit zero FPs."""
    pp, zero = [], []
    for im in images:
        n = im['image_id']
        bx, ss = preds[n]
        for k, (box, score) in enumerate(zip(bx, ss)):
            x1,y1,x2,y2 = map(float, box)
            if x1 == x2 or y1 == y2:
                zero.append(float(score))
            else:
                pp.append(dict(candidate_id=f'{n}#p{k:05d}', image_id=n, category='pedestrian',
                               bbox=[x1,y1,x2-x1,y2-y1], score=float(score)))
    names = [i['image_id'] for i in images]
    ev = ReferenceEvaluator(dict(schema_version='threshold-transfer-v1', images=images, annotations=anns, provenance={}),
        dict(schema_version='threshold-transfer-v1', predictions=pp, provenance={'evaluated_image_ids': names}),
        categories=['pedestrian'], ignore_policy='same_category_ioa', bounds_policy='allow_outside')
    p = ET.Population([recs[n] for n in names])
    for t in [None, *[t for t in thresholds if t is not None], *[p.select(r) for r in TARGETS]]:
        ref, fast = ev.operating_point(t), p.point(t)
        assert fast['tp'] == ref['tp']
        assert fast['fp'] == ref['fp'] + sum(t is None or s >= t for s in zero)
        assert sum(sum(t is None or s >= t for s in recs[n]['ig']) for n in names) == ref['ignored']
    for rho in TARGETS:
        assert ev.select_threshold(rho)['threshold'] == p.select(rho)
    # Per-GT matching is needed for height and joint-coverage panels.
    expected = {r['annotation_id']: r['score'] for r in ev.rows if r['outcome'] == 'TP'}
    actual = {g:s for n in names for g,s in zip(recs[n]['gt_ids'], recs[n]['gt_match']) if np.isfinite(s)}
    assert expected == actual
    return {'images':len(names), 'gt':int(p.G.sum()), 'candidates':len(pp)+len(zero),
            'status':'PASS: exact TP/FP/ignored, per-GT scores, thresholds and ceilings'}


def heights(p, t, ratio):
    out = {}
    for scale, factor in [('native',1), ('model_input',ratio)]:
        h = p.gt_h * factor
        bins = {}
        for lo,hi in ET.C.HEIGHT_BINS:
            m = (h >= lo) & ((h < hi) if hi else True)
            g = int(m.sum()); ceiling = int((m & np.isfinite(p.gt_m)).sum())
            tp = int((m & (p.gt_m >= t)).sum()) if t is not None else None
            bins[ET.C.height_bin(lo)] = {'gt':g,'ceiling_tp':ceiling,'ceiling_recall':ceiling/g if g else None,
                'tp':tp,'recall':tp/g if g and tp is not None else None,
                'no_matched_candidate':g-ceiling,'removed_by_threshold':ceiling-tp if tp is not None else None}
        out[scale] = {'minimum_gt_height':float(h.min()) if len(h) else None,'bins':bins}
    return out


def summarize(recs, images, anns, policy, rho, t, ratio, clear=None):
    p = ET.Population(recs)
    c = p.point(None); op = p.point(t) if t is not None else None
    ot = p.select(rho) if c['gt'] else None
    oracle = p.point(ot) if ot is not None else None
    track = {json.dumps(a.get('attributes',{}).get('native',{}).get('tracking_id'), sort_keys=True)
             for a in anns if not a['ignore'] and a.get('attributes',{}).get('native',{}).get('tracking_id') is not None}
    out = {'policy':policy, 'target':rho, 'source_threshold':t,
        'status':'FEASIBLE_SOURCE_TARGET' if t is not None else 'INFEASIBLE_SOURCE_TARGET',
        'images':p.n, 'eligible_gt':int(c['gt']), 'ignored_gt':sum(a['ignore'] for a in anns),
        'known_groups':len({i['group_id'] for i in images}-{None}),
        'unkeyed_images':sum(i['group_id'] is None for i in images),
        'eligible_tracking_values':len(track), 'operational_150_gt':c['gt']>=150,
        'ceiling':c,'operating':op,
        'ignored_candidates_ceiling':sum(r['ignored'] for r in recs),
        'ignored_candidates_operating':sum(int((np.asarray(r['ig'])>=t).sum()) for r in recs) if t is not None else None,
        'zero_area_candidates':sum(r['zero'] for r in recs),
        'oracle':{'status':'UNDEFINED' if not c['gt'] else 'FEASIBLE' if ot is not None else 'INFEASIBLE',
                  'threshold':ot,'operating':oracle},
        'heights':heights(p,t,ratio)}
    if op:
        out['misses']={'no_matched_candidate':int(c['gt']-c['tp']), 'removed_by_threshold':int(c['tp']-op['tp'])}
        assert sum(out['misses'].values()) == op['gt']-op['tp']
        out['target_gap']=target_gap_decomposition(rho,op['recall'],c['recall'])
        out['oracle_gap']=oracle['recall']-op['recall'] if oracle else None
        if clear:
            cp, cc, crec = clear
            co,ce = cp.point(t),cp.point(None)
            out['loss_vs_bdd_h50_clear']=held_out_loss_decomposition(co['recall'],op['recall'],ce['recall'],c['recall'])
            variants = {'base':c['recall'], 'floor1e-3':float((p.gt_m>=1e-3).sum()/c['gt']) if c['gt'] else None,
                        'any_iou50':sum(int(np.sum(r['any50'])) for r in recs)/c['gt'] if c['gt'] else None,
                        'any_iou30':sum(int(np.sum(r['any30'])) for r in recs)/c['gt'] if c['gt'] else None}
            clearvariants={'base':ce['recall'], 'floor1e-3':float((cp.gt_m>=1e-3).sum()/ce['gt']),
                'any_iou50':sum(int(np.sum(r['any50'])) for r in crec)/ce['gt'],
                'any_iou30':sum(int(np.sum(r['any30'])) for r in crec)/ce['gt']}
            out['definition_sensitivity']={}
            for v,m in variants.items():
                applicable = not (v=='floor1e-3' and t < 1e-3)
                d=clearvariants[v]-m if m is not None else None
                out['definition_sensitivity'][v]={'status':'DEFINED' if applicable else 'NOT_APPLICABLE_SOURCE_THRESHOLD_BELOW_FLOOR',
                    'target_ceiling':m,'clear_ceiling':clearvariants[v],
                    'ceiling_difference':d if applicable else None,
                    'residual_threshold_part':co['recall']-op['recall']-d if applicable and d is not None else None}
    return out


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--base',type=Path,required=True); a=ap.parse_args()
    base=a.base.resolve(); private=base/'outputs/nightowls_evaluation_20261123'; private.mkdir(parents=True,exist_ok=True)
    public=ROOT/'docs/research/2026-11-23_nightowls_evaluation'; public.mkdir(parents=True,exist_ok=True)
    start=time.time(); b=base/'outputs/bdd_transfer_20261115'
    receipt={'researcher':'GPT Sol','base_commit':'c922cdacfe4e69232db454d82b3fc2b77e0bbc43',
             'merged_policy':'5251312', 'python':sys.version, 'numpy':np.__version__, 'hashes':{}, 'checks':{},
             'status':'RUNNING_POINT_ESTIMATES', 'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    files=[Path(__file__),OLD/'evaluate_transfer.py',OLD/'sensitivity.py',ROOT/'src/threshold_transfer/metrics.py',
           ROOT/'src/threshold_transfer/nightowls.py', ROOT/'docs/research/2026-11-17_nightowls_external_contract.md',
           ROOT/'docs/research/2026-11-18_nightowls_contract_v2.md',ROOT/'docs/research/2026-11-18_nightowls_v2_bdd_reference.md']
    for f in files:
        receipt['hashes'][f.relative_to(ROOT).as_posix()]=sha(f)
        dest=private/'executed_sources'/f.relative_to(ROOT); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(f,dest)
    def checkpoint():
        receipt['elapsed_s']=round(time.time()-start,2); write(private/'receipt.json',receipt)
    checkpoint()
    labelpath=base/'data/nightowls/annotations/nightowls_validation.json'
    pilotpath=base/'outputs/nightowls_image_access_pilot_20261113/selection.json'
    assert sha(labelpath)==ANNOTATION_SHA and sha(pilotpath)==PILOT_SHA and sha(b/'private/gt_pedestrian.json')==BDD_SHA
    receipt['hashes'].update(annotations=ANNOTATION_SHA,pilot=PILOT_SHA,bdd_gt=BDD_SHA)
    native=json.loads(labelpath.read_bytes()); pilot=json.loads(pilotpath.read_bytes()); excluded=[i['id'] for i in pilot['images']]
    assert len(excluded)==64 and len(set(excluded))==64
    with zipfile.ZipFile(base/'data/nightowls/full_validation/nightowls_validation.zip') as z:
        members=[Path(i.filename).name for i in z.infolist() if i.filename.lower().endswith('.png')]
    native_names=[Path(i['file_name']).name for i in native['images']]
    assert len(members)==len(set(members))==len(native_names)==len(set(native_names))==51848
    assert set(members)==set(native_names)
    docs={}
    for setup in SETUPS:
        for profile in PROFILES:
            doc=convert_nightowls(native,profile=profile,setup=setup,matching_category='pedestrian',exclude_image_ids=excluded)
            # Preserve native key anonymization by string order, never namespaced lexical order.
            docs[setup,profile]=doc
    d=docs['reasonable',PROFILES[0]]; images=d['images']; names=[i['image_id'] for i in images]
    nativekeys=sorted({i['attributes']['native']['recordings_id'] for i in images}-{None},key=str)
    keymap={k:f'R{j+1}' for j,k in enumerate(nativekeys)}
    group=np.array([keymap.get(i['attributes']['native']['recordings_id'],'unkeyed') for i in images])
    assert len(images)==51782 and sum(group=='unkeyed')==1304
    assert d['provenance']['summary']['native_empty_night_image_count']==42316
    ag=Counter(a['image_id'] for a in d['annotations'] if not a['ignore'])
    assert [sum(ag[n] for n,g in zip(names,group) if g==f'R{j+1}') for j in range(5)]==[1005,291,4994,332,149]
    write(private/'group_map.json',{'mapping':keymap})
    ledger=json.loads((ROOT/'docs/research/2026-11-17_threshold_remedies/compute_ledger_stage2.json').read_text())
    oldledger=json.loads((ROOT/'docs/research/2026-11-15_bdd_clearday_transfer/compute_ledger.json').read_text())
    bgt=json.loads((b/'private/gt_pedestrian.json').read_bytes())
    result={'attribution':'GPT Sol; measured CPU scoring of Claude Opus saved inference',
            'status':'POINT_ESTIMATES_COMPLETE_UNCERTAINTY_PENDING','G0':'PENDING', 'arms':{}, 'joint_coverage':{},
            'pending':['1000 paired cluster/source-reselection, known-only, IID, dominant-out, oracle and contrast intervals']}
    for arm in ARMS:
        print('START',arm,flush=True)
        bn,bpred,btot=load_preds(b/'preds'/f'{arm}.npz',oldledger['predictions_and_weights'][arm]['preds_npz_sha256'])
        assert set(bn)==set(bgt)
        receipt['hashes'][f'bdd_{arm}']=oldledger['predictions_and_weights'][arm]['preds_npz_sha256']
        selections={}; bpop={}; brecs={}; policies={}
        for mh in (0,32,50):
            selected=[n for n in bn if bgt[n]['role']=='selection']
            needed=selected if mh!=50 else selected+[n for n in bn if bgt[n]['role']!='selection' and bgt[n]['stratum'] in ('clear_day','night')]
            rec={}
            for j in range(0,len(needed),400):
                out,_=ET.match_chunk(needed[j:j+400],bgt,bpred,mh); rec.update(out)
            # Add any-overlap and ignored-score bookkeeping for the shared summary path.
            for n,r in rec.items():
                eligible=[p for p in bgt[n]['peds'] if p[3]-p[1]>=mh]
                r.update(ig=[],any50=any_iou_hits(eligible,bpred[n][0],.5),any30=any_iou_hits(eligible,bpred[n][0],.3))
            sel=ET.Population([rec[n] for n in selected]); selections[mh]=sel
            if mh==50:
                for label,stratum in [('selection',None),('clear','clear_day'),('night','night')]:
                    mm=selected if stratum is None else [n for n in needed if bgt[n]['role']!='selection' and bgt[n]['stratum']==stratum]
                    brecs[label]=[rec[n] for n in mm]; bpop[label]=ET.Population(brecs[label])
                assert (sel.n,int(sel.G.sum()),bpop['clear'].n,int(bpop['clear'].G.sum()),bpop['night'].n,int(bpop['night'].G.sum()))==(1842,1181,1764,1256,3929,1616)
                assert tuple(sel.select(rho) for rho in TARGETS)==H50[arm]
            for rho in ((.6,.7,.8,.9,.95) if mh==0 else TARGETS):
                pname=('h50' if mh==50 else 'h32_exploratory' if mh==32 else 'allheight_original' if rho>=.8 else 'low_exploratory')+f'_r{rho:g}'
                t=sel.select(rho)
                if mh!=50:
                    suffix='_h32' if mh==32 else '_low' if rho<.8 else ''
                    saved=json.loads((ROOT/f'docs/research/2026-11-15_bdd_clearday_transfer/{arm}{suffix}.json').read_text())
                    assert t==saved['selection'][str(rho)]['threshold']
                policies[pname]={'min_height':mh,'target':rho,'threshold':t}
        # Decisive reference reproduction with full BDD selection/clear/night populations.
        expected={'A_640':(1035,1004),'B_1280':(1032,1003),'C_640':(1044,983)}[arm]
        assert tuple(int(bpop[s].point(H50[arm][0])['tp']) for s in ('clear','night'))==expected
        receipt['checks'][f'{arm}_BDD']='PASS unchanged match_chunk; exact stored thresholds all policies; h50 primary TP reference'
        rawname=f'nightowls_{arm}'; expectedhash=ledger['predictions_sha256'][rawname]
        nn,npr,totals=load_preds(b/'stage2/preds'/f'{rawname}.npz',expectedhash)
        assert len(nn)==51848 and set(nn)==set(native_names)
        receipt['hashes'][rawname]=expectedhash
        pred={i['image_id']:npr[Path(i['file_name']).name] for i in images}
        summary=json.loads((b/'stage2/preds'/f'{rawname}.npz.json').read_text())
        assert summary['out_sha256']==expectedhash and summary['cap_hits']==0
        ratio=(1280 if arm=='B_1280' else 640)/1024
        armout={'policies':policies,'inference':summary,'resize_ratio':ratio,
                'letterbox_tensor_hw_derived':[800,1280] if arm=='B_1280' else [416,640],
                'tensor_shape_status':'derived from saved original shapes and pinned rect/stride32 path; tensor shape not logged',
                'bdd_h50':{},'panels':{}}
        for label,p in bpop.items():
            armout['bdd_h50'][label]={'ceiling':p.point(None),'policies':{}}
            for pname,pol in policies.items():
                t=pol['threshold']; op=p.point(t) if t is not None else None
                armout['bdd_h50'][label]['policies'][pname]={'operating':op,'heights':heights(p,t,1 if arm=='B_1280' else .5)}
        cache={'groups':group,'policies':policies,'selection':selections,'bdd':bpop,'bdd_recs':brecs,'panels':{}}
        for (setup,profile),doc in docs.items():
            by=defaultdict(list)
            for ann in doc['annotations']: by[ann['image_id']].append(ann)
            rec={n:fast_image(by[n],*pred[n]) for n in names}
            # Check every annotated frame in an evenly spaced 1/17 sample, plus empty/zero cases.
            checknames=[n for j,n in enumerate(names) if j%17==0 or rec[n]['zero']]
            checkset=set(checknames)
            receipt['checks'][f'{arm}/{setup}/{profile}']=reference_check(
                [i for i in images if i['image_id'] in checkset],
                [x for x in doc['annotations'] if x['image_id'] in checkset], pred,rec,[p['threshold'] for p in policies.values()])
            rr=[rec[n] for n in names]; panel=f'{setup}/{profile}'; cache['panels'][panel]=rr
            rows={}
            masks={'pooled':np.ones(len(names),bool),'known_only':group!='unkeyed',
                   'dominant_out':group!='R3',**{g:group==g for g in ('R1','R2','R3','R4','R5','unkeyed')}}
            for label,m in masks.items():
                ii=[im for im,k in zip(images,m) if k]; keep={i['image_id'] for i in ii}
                aa=[x for x in doc['annotations'] if x['image_id'] in keep]
                rsub=[r for r,k in zip(rr,m) if k]
                rows[label]={pname:summarize(rsub,ii,aa,pname,pol['target'],pol['threshold'],ratio,
                    (bpop['clear'],None,brecs['clear'])) for pname,pol in policies.items()}
            armout['panels'][panel]=rows
            # Persist completed first points before continuing other panels/runs.
            result['arms'][arm]=armout; write(private/'point_estimates.json',result); checkpoint()
            print('POINTS',arm,panel,rows['pooled']['h50_r0.8']['operating'],flush=True)
        with open(private/f'{arm}_cache.pkl','wb') as f: pickle.dump(cache,f,pickle.HIGHEST_PROTOCOL)
        # Do not expose candidate/GT identity or native attributes in public JSON.
        write(public/'aggregate.json',result)
        print('SAVED',arm,'seconds',round(time.time()-start),flush=True)
    # Joint full-prefix coverage is aligned on canonical GT IDs, not matched candidate IDs.
    caches={a:pickle.load(open(private/f'{a}_cache.pkl','rb')) for a in ARMS}
    for contrast in (ARMS,ARMS[:2],ARMS[::2],ARMS[1:]):
        rr=[caches[a]['panels']['reasonable/'+PROFILES[0]] for a in contrast]
        counts={g:0 for g in ('R1','R2','R3','R4','R5','unkeyed')}
        for j,g in enumerate(group):
            hits=[{aid for aid,s in zip(r[j]['gt_ids'],r[j]['gt_match']) if np.isfinite(s)} for r in rr]
            counts[g]+=len(set.intersection(*hits))
        result['joint_coverage']['/'.join(contrast)]={'counts':counts,
            'supported_known_keys':sum(counts[g]>=10 for g in counts if g!='unkeyed'),
            'sequence_majority_support':'SUPPORTED' if all(counts[g]>=10 for g in counts if g!='unkeyed') else 'INCONCLUSIVE',
            'sequence_majority_test':'NOT_CLAIMED; support counts only'}
    write(private/'point_estimates.json',result); write(public/'aggregate.json',result)
    receipt['status']='POINT_ESTIMATES_COMPLETE_UNCERTAINTY_PENDING'; checkpoint()


if __name__=='__main__': main()
