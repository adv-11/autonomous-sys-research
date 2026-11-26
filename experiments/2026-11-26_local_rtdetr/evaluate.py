"""GPT Sol: three-arm reporting, reusing existing evaluator and selectors."""
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
from local import OUT, OLD, ORIGINAL, HERE, save, sha

spec=importlib.util.spec_from_file_location('existing_rtdetr_evaluation',ORIGINAL/'evaluate.py')
E=importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)
ARMS=('baseline','day_control','adaptation')


def main():
    gt=E.json.loads((OLD/'gt_pedestrian.json').read_text())
    members={}
    for n in sorted(gt):
        group='selection' if gt[n]['role']=='selection' else gt[n]['stratum']
        members.setdefault(group,[]).append(n)
    rng=np.random.default_rng(20261123)
    boot={s:[np.bincount(rng.integers(0,len(m),len(m)),minlength=len(m)) for _ in range(1000)]
          for s,m in members.items() if s in ('selection','clear_day','night')}
    result=dict(researcher='GPT Sol',scope='Exploratory single training seed; G0 pending',
       evaluator='Unchanged ReferenceEvaluator, IoU0.5, reject ignore, allow_outside',
       bootstrap='1000 paired image replicates; independent source/test; refit each arm threshold; no training/route variance',
       arms={},paired={})
    all_reps={}
    for arm in ARMS:
        path=OUT/f'{arm}_pedestrian.npz'
        with np.load(path) as a:
            names=a['names'].tolist()
            boxes,scores,offsets=a['boxes'],a['scores'],a['offsets']
        assert len(names)==len(set(names))==len(gt) and set(names)==set(gt)
        predictions={n:(boxes[offsets[i]:offsets[i+1]],scores[offsets[i]:offsets[i+1]]) for i,n in enumerate(names)}
        records={}
        for begin in range(0,len(names),400):
            records.update(E.match(names[begin:begin+400],gt,predictions)[0])
        pops={s:E.Population([records[n] for n in m]) for s,m in members.items()}
        sel=pops['selection']
        ar=dict(prediction_sha256=sha(path),strata={},operating_points={},checks={})
        for s,pop in pops.items():
            ceiling=pop.point(None)
            ar['strata'][s]=dict(ceiling=ceiling,unmatched_share=1-ceiling['recall'] if pop.G.sum() else None,
                                zero_area_candidates=int(pop.zero.sum()),ceiling_by_height=pop.by_height(None))
        _,reference=E.match(members['selection'],gt,predictions)
        for rho in (.8,.9,.95):
            assert reference.select_threshold(rho)['threshold']==sel.select(rho),(arm,rho)
        ar['checks']['source_full_reference_threshold_equivalence']='PASS'
        policies={'source_fppi_1':E.choose_fppi,
                  **{f'recall_{rho}':lambda p,w=None,r=rho:p.select(r,w) for rho in (.8,.9,.95)}}
        all_reps[arm]={}
        for policy,select in policies.items():
            threshold=select(sel)
            thresholds=[select(sel,w) for w in boot['selection']]
            op=dict(threshold=threshold,status='FEASIBLE' if threshold is not None else 'INFEASIBLE_SOURCE',
                    bootstrap_infeasible=sum(t is None for t in thresholds),conditions={})
            all_reps[arm][policy]={}
            if threshold is not None:
                op['selection']=sel.point(threshold)
                for s in ('clear_day','night'):
                    pop=pops[s]
                    point=pop.point(threshold)
                    point['decomposition']=E.held_out_loss_decomposition(pops['clear_day'].point(threshold)['recall'],
                       point['recall'],pops['clear_day'].point(None)['recall'],pop.point(None)['recall'])
                    point['threshold_removable_miss_share']=pop.point(None)['recall']-point['recall']
                    reps=[pop.point(t,boot[s][b]) if t is not None else None for b,t in enumerate(thresholds)]
                    for metric in ('recall','fppi'):
                        point[metric+'_ci']=E.ci([r[metric] for r in reps if r is not None])
                    op['conditions'][s]=point
                    all_reps[arm][policy][s]=reps
            ar['operating_points'][policy]=op
        for s in ('selection','clear_day','night'):
            np.savez_compressed(OUT/f'{arm}_{s}_curve.npz',**E.curve(pops[s]))
        result['arms'][arm]=ar
        save('evaluation_progress.json',dict(completed_arm=arm))
        del predictions,records,pops,reference,boxes,scores
    for a,b in [('day_control','adaptation'),('baseline','day_control'),('baseline','adaptation')]:
        contrast=f'{b}_minus_{a}'
        result['paired'][contrast]={}
        for policy in all_reps[a]:
            result['paired'][contrast][policy]={}
            for s in ('clear_day','night'):
                if s not in all_reps[a][policy] or s not in all_reps[b][policy]:
                    continue
                metrics={}
                for metric in ('recall','fppi'):
                    pa=result['arms'][a]['operating_points'][policy]['conditions'][s][metric]
                    pb=result['arms'][b]['operating_points'][policy]['conditions'][s][metric]
                    delta=[bb[metric]-aa[metric] for aa,bb in zip(all_reps[a][policy][s],all_reps[b][policy][s])
                           if aa is not None and bb is not None]
                    metrics[metric]=dict(difference=pb-pa,ci=E.ci(delta),feasible_bootstrap_pairs=len(delta))
                result['paired'][contrast][policy][s]=metrics
    (OUT/'results.json').write_text(json.dumps(result,indent=2,allow_nan=False))


if __name__=='__main__':
    main()
