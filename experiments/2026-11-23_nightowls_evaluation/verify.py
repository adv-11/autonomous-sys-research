"""GPT Sol: one bounded real-data correctness/accounting/privacy pass.

This checks the completed run; it is not synthetic qualification or independent
review. No model imports. It does not repeat already-passed reference matching.
"""
import argparse
import gzip
import json
from pathlib import Path
import pickle
import shutil
import sys
import numpy as np
import evaluate as E
import uncertainty as U


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);a=ap.parse_args()
    private=a.base/'outputs/nightowls_evaluation_20261123'
    public=E.ROOT/'docs/research/2026-11-23_nightowls_evaluation'
    def load(name):
        p=public/f'{name}.json'
        return json.loads(p.read_bytes() if p.exists() else gzip.decompress(p.with_suffix('.json.gz').read_bytes()))
    r=load('aggregate');u=load('uncertainty')
    receipt=json.loads((private/'receipt.json').read_text())
    assert r['status']=='COMPLETE' and r['pending']==[] and u['replicates']==1000 and u['seed']==20261117
    draws=np.load(private/'bootstrap_draws.npz')
    previous=None; total_rows=0; weighted_checks=0; height_checks=0
    for arm in E.ARMS:
        names=np.load(a.base/f'outputs/bdd_transfer_20261115/preds/{arm}.npz')['names']
        if previous is not None: assert np.array_equal(names,previous),'BDD image pairing changed'
        previous=names
        cache=pickle.load(open(private/f'{arm}_cache.pkl','rb'))
        groupidx=np.array([('R1','R2','R3','R4','R5','unkeyed').index(g) for g in cache['groups']])
        for panel,rows in r['arms'][arm]['panels'].items():
            setup,profile=panel.split('/')
            for pname in cache['policies']:
                pooled=rows['pooled'][pname]
                assert pooled['images']==51782
                if setup=='reasonable':
                    assert pooled['eligible_gt']==7631
                    assert pooled['ignored_gt']==(2520 if profile==E.PROFILES[0] else 9421)
                for field in ('images','eligible_gt','ignored_gt','ignored_candidates_ceiling','zero_area_candidates'):
                    assert pooled[field]==sum(rows[g][pname][field] for g in ('R1','R2','R3','R4','R5','unkeyed'))
                for label,entries in rows.items():
                    v=entries[pname];total_rows+=1
                    for scale in ('native','model_input'):
                        bins=v['heights'][scale]['bins']
                        assert sum(b['gt'] for b in bins.values())==v['eligible_gt']
                        assert sum(b['ceiling_tp'] for b in bins.values())==v['ceiling']['tp']
                        assert all(b['recall'] is None and b['ceiling_recall'] is None for b in bins.values() if not b['gt'])
                        if v['operating']:
                            assert sum(b['tp'] for b in bins.values())==v['operating']['tp']
                    if v['operating']:
                        assert sum(v['misses'].values())==v['eligible_gt']-v['operating']['tp']
                        dec=v['loss_vs_bdd_h50_clear']
                        if v['operating']['recall'] is None:
                            assert all(x['value'] is None for x in dec.values())
                        else:
                            assert abs(dec['held_out_loss']['value']-dec['ceiling_difference']['value']-dec['threshold_miss_difference']['value'])<1e-12
                    else:
                        assert v['source_threshold'] is None
                for mode in U.MODES:
                    metrics=u['arms'][arm]['panels'][panel][mode]['policies'][pname]['metrics']
                    for item in metrics.values(): assert item['defined']+item['undefined']==1000
                    if cache['policies'][pname]['threshold'] is None:
                        assert metrics['recall']['defined']==metrics['fppi']['defined']==metrics['loss']['defined']==0
            # Profiles must preserve all TP assignments on identical GT.
            if profile==E.PROFILES[0]:
                rr=cache['panels'][f'{setup}/{E.PROFILES[1]}']
                for left,right in zip(cache['panels'][panel],rr):
                    assert left['gt_ids']==right['gt_ids']
                    assert np.array_equal(left['gt_match'],right['gt_match'],equal_nan=True)
        # Verify weighted fast aggregation and reselection on actual target data,
        # with three fixed replicates from each required bootstrap mode.
        p=E.ET.Population(cache['panels']['reasonable/'+E.PROFILES[0]])
        source=cache['selection'][50]
        ts=U.selected(source,.8,draws['source'])
        for mode,key in zip(U.MODES,('cluster','known','dominant','iid')):
            w=draws[key]; unit=np.arange(p.n) if key=='iid' else groupidx
            ct=U.Counts(p,unit); op=ct.point(ts,w); ot=U.selected(p,.8,w,unit)
            for b in (0,499,999):
                assert ts[b]==source.select(.8,draws['source'][b])
                targetw=w[b] if key=='iid' else w[b,groupidx]
                for t in (float(ts[b]),float(ot[b]) if np.isfinite(ot[b]) else None):
                    if t is None: continue
                    direct=p.point(t,targetw)
                    vv=ct.point(np.full(1000,t),w)
                    for k in ('recall','fppi','precision'):
                        if direct[k] is None:assert np.isnan(vv[k][b])
                        else:assert abs(direct[k]-vv[k][b])<1e-12
                    weighted_checks+=1
                assert (p.select(.8,targetw)==float(ot[b])) if np.isfinite(ot[b]) else (p.select(.8,targetw) is None)
            saved=u['arms'][arm]['panels']['reasonable/'+E.PROFILES[0]][mode]['policies']['h50_r0.8']['metrics']
            assert U.interval(op['recall'])==saved['recall']
            for scale,ratio,lo,hi in [('native',1,32,64),('model_input',r['arms'][arm]['resize_ratio'],64,128)]:
                keep=(p.gt_h*ratio>=lo)&(p.gt_h*ratio<hi)
                weights=w[:,unit[p.gt_img[keep]]]
                g=weights.sum(axis=1)
                tp=(weights*(p.gt_m[keep][None,:]>=ts[:,None])).sum(axis=1).astype(float)
                tp[~np.isfinite(ts)]=np.nan
                c=(weights*np.isfinite(p.gt_m[keep])[None,:]).sum(axis=1)
                actual=u['arms'][arm]['panels']['reasonable/'+E.PROFILES[0]][mode]['policies']['h50_r0.8']['heights'][scale][f'{lo}-{hi}']
                assert U.interval(U.divide(tp,g))==actual['recall']
                assert U.interval(U.divide(c,g))==actual['ceiling']
                height_checks+=1
        # Candidate accounting includes all empty images and native zero FPs.
        z=np.load(a.base/f'outputs/bdd_transfer_20261115/stage2/preds/nightowls_{arm}.npz')
        labels=json.loads((a.base/'data/nightowls/annotations/nightowls_validation.json').read_bytes())
        assert {(i['height'],i['width']) for i in labels['images']}=={(640,1024)}
        assert r['arms'][arm]['inference']['orig_shapes_hw']==[[640,1024]]
        pilot=json.loads((a.base/'outputs/nightowls_image_access_pilot_20261113/selection.json').read_bytes())
        excluded={i['id'] for i in pilot['images']}
        kept={Path(i['file_name']).name for i in labels['images'] if i['daytime']=='night' and i['id'] not in excluded}
        n=z['names'].astype(str); sizes=np.diff(z['offsets'])
        assert np.all(z['all_class_candidates']>=sizes)
        assert int((z['all_class_candidates']>=3000).sum())==0
        candidates=int(sizes[np.isin(n,list(kept))].sum())
        for profile in E.PROFILES:
            v=r['arms'][arm]['panels']['reasonable/'+profile]['pooled']['h50_r0.8']
            assert v['ceiling']['tp']+v['ceiling']['fp']+v['ignored_candidates_ceiling']==candidates
        if arm==E.ARMS[0]:
            r['population']={'images':51782,'native_empty_frames':42316,'zero_eligible_gt_frames':int((p.G==0).sum()),
                'eligible_gt':7631,'fixed_pilot_exclusions':64,'excluded_dusk_frames':2,'known_recording_keys':5,
                'unkeyed_frames':1304,'unkeyed_gt':860,'dominant_recording':'R3','dominant_gt':4994,
                'primary_profile':E.PROFILES[0],'primary_ignored_gt':2520,'sensitivity_profile':E.PROFILES[1],'sensitivity_ignored_gt':9421}
        # Counts-only public JSON: reject identities/geometry/native metadata.
        restricted=set(n.tolist())|{str(i['id']) for i in labels['images']}
        for f in public.glob('*.json'):
            obj=json.loads(f.read_text())
            def scan(v):
                if isinstance(v,dict):
                    assert not set(v)&{'bbox','boxes','image_id','annotation_id','candidate_id','recordings_id','tracking_id','gt_ids','gt_match','file_name'}
                    for x in v.values():scan(x)
                elif isinstance(v,list):
                    for x in v:scan(x)
                elif isinstance(v,str): assert v not in restricted
            scan(obj)
    checks={'attribution':'GPT Sol implementation check; independent review pending',
            'status':'PASS','aggregate_rows_checked':total_rows,'weighted_reference_points_checked':weighted_checks,
            'weighted_height_intervals_checked':height_checks,
            'bdd_image_order_pairing':'exact across A/B/C',
            'checks':['24 sampled real-data ReferenceEvaluator equivalence checks retained in receipt',
                      'BDD exact frozen source thresholds and decisive h50 TP references',
                      'recording sums, empty-image candidate accounting, both ignore profiles',
                      'full-assignment height counts and zero-support undefined values',
                      'miss and signed clear-reference identities',
                      '1000 interval supports; source infeasibility propagation',
                      'source/target reselection and weighted counts at fixed actual bootstrap replicates',
                      'public JSON identity/geometry/native-key scan']}
    assert not {'torch','ultralytics','tensorflow','jax'}.intersection(sys.modules)
    checks['model_framework_modules_loaded']=[]
    E.write(public/'validation.json',checks);E.write(private/'validation.json',checks)
    E.write(public/'aggregate.json',r);E.write(private/'point_estimates.json',r)
    local=[E.OLD/'common.py',E.OLD/'matched_fppi.py',E.OLD/'config.json',E.OLD/'amendment_3.json',
           E.ROOT/'src/threshold_transfer/schema.py',E.ROOT/'src/threshold_transfer/data.py',Path(__file__),
           Path(__file__).with_name('figures.py'),Path(__file__).with_name('package_aggregates.py'),
           Path(__file__).with_name('finalize_report.py')]
    for f in local:
        rel=f.relative_to(E.ROOT);receipt['hashes'][rel.as_posix()]=E.sha(f)
        dest=private/'executed_sources'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
    receipt['checks']['final_accounting']=checks
    evidence=[*private.glob('*_cache.pkl'),*private.glob('*_bootstrap_metrics.pkl'),
              private/'bootstrap_draws.npz',private/'point_estimates.json',private/'uncertainty.json',private/'bootstrap.log']
    receipt['private_artifacts']={f.name:{'sha256':E.sha(f),'bytes':f.stat().st_size} for f in evidence}
    E.write(private/'receipt.json',receipt);E.write(public/'receipt.json',receipt)
    print(json.dumps(checks))


if __name__=='__main__':main()
