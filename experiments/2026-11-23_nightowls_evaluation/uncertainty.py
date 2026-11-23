"""GPT Sol: fixed 1000 paired bootstrap, from first-scoring private caches.

No matching, inference or policy selection occurs here. Source t* is reselected
within each independently resampled BDD selection draw. Target oracles reselect
on their own target draw and are diagnostic. Pickles are trusted local evidence.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import pickle
import shutil
import time
os.environ['OPENBLAS_NUM_THREADS']='1'
os.environ['OMP_NUM_THREADS']='1'
import numpy as np
import evaluate as E

B=1000
SEED=20261117
MODES=('cluster_conditional_unkeyed','known_only_cluster','dominant_out_conditional_unkeyed','iid_image_sensitivity')


def interval(x):
    a=np.asarray(x,float); a=a[np.isfinite(a)]
    return {'percentile_95':np.percentile(a,[2.5,97.5]).tolist() if len(a) else None,
            'defined':len(a),'undefined':B-len(a)}


def divide(a,b):
    a,b=np.broadcast_arrays(np.asarray(a,float),np.asarray(b,float))
    return np.divide(a,b,out=np.full(a.shape,np.nan),where=b!=0)


def weighted(w,counts):
    # GT occupies few of the 51,782 images; skip exact zero contributions.
    idx=np.flatnonzero(counts)
    return w[:,idx].astype(float) @ counts[idx]


def selected(p, rho, w, unit=None):
    """Highest observed TP boundary, inclusive ties, as Population.select."""
    unit=np.arange(p.n) if unit is None else unit
    g=weighted(w,np.bincount(unit,weights=p.G,minlength=w.shape[1]))
    if not len(p.tp_all): return np.full(B,np.nan)
    order=np.argsort(-p.tp_all,kind='stable')
    c=np.cumsum(w[:,unit[p.tp_img[order]]],axis=1,dtype=float)
    feasible=(g>0)&(c[:,-1]/np.where(g>0,g,1)>=rho)
    k=np.argmax(c/np.where(g[:,None]>0,g[:,None],1)>=rho,axis=1)
    return np.where(feasible,p.tp_all[order[k]],np.nan)


class Counts:
    """Sorted score events; one sweep evaluates all replicate thresholds exactly."""
    def __init__(self,p,unit=None):
        self.p=p
        self.unit=np.arange(p.n) if unit is None else unit
        self.n=int(self.unit.max())+1
        self.g=np.bincount(self.unit,weights=p.G,minlength=self.n)
        self.images=np.bincount(self.unit,minlength=self.n)
        self.events={}
        self.denominators={}
        for k,s,idx in [('tp',p.tp_all,p.tp_img),('fp',p.fp_all,p.fp_img)]:
            order=np.argsort(-s,kind='stable')
            active,compressed=np.unique(self.unit[idx[order]],return_inverse=True)
            self.events[k]=(-s[order],compressed,active)

    def at(self,k,t,w):
        neg,idx,active=self.events[k]
        return event_counts(neg,idx,t,w[:,active])

    def ceiling(self,w):
        _,idx,active=self.events['tp']
        return weighted(w[:,active],np.bincount(idx,minlength=len(active)))

    def point(self,t,w):
        tp=self.at('tp',t,w); fp=self.at('fp',t,w)
        if id(w) not in self.denominators:
            self.denominators[id(w)]=(weighted(w,self.g),w.sum(axis=1) if np.all(self.images==1) else weighted(w,self.images),self.ceiling(w))
        g,n,ceil=self.denominators[id(w)]
        return {'recall':divide(tp,g),'fppi':divide(fp,n),'precision':divide(tp,tp+fp),
                'ceiling':divide(ceil,g),'no_matched_candidate':g-ceil,'removed_by_threshold':ceil-tp,
                'gt':g,'images':n}


def event_counts(neg,idx,t,w):
    out=np.full(B,np.nan)
    counts=np.zeros(w.shape[1],np.int64); prev=0
    for threshold in np.unique(t[np.isfinite(t)])[::-1]:
        end=int(np.searchsorted(neg,-threshold,side='right'))
        counts+=np.bincount(idx[prev:end],minlength=w.shape[1]); prev=end
        reps=np.flatnonzero(t==threshold)
        out[reps]=np.sum(w[reps]*counts,axis=1)
    return out


def height_basis(p,unit,w,ratio):
    basis={}
    for kind,scale in [('native',1),('model_input',ratio)]:
        basis[kind]={};h=p.gt_h*scale
        for lo,hi in E.ET.C.HEIGHT_BINS:
            keep=(h>=lo)&((h<hi) if hi else True)
            g=weighted(w,np.bincount(unit[p.gt_img[keep]],minlength=w.shape[1]))
            matched=keep & np.isfinite(p.gt_m)
            m=weighted(w,np.bincount(unit[p.gt_img[matched]],minlength=w.shape[1]))
            order=np.argsort(-p.gt_m[matched],kind='stable')
            scores=p.gt_m[matched][order]
            active,idx=np.unique(unit[p.gt_img[matched][order]],return_inverse=True)
            basis[kind][E.ET.C.height_bin(lo)]=(g,m,-scores,idx,active)
    return basis


def height_boot(basis,w,t):
    out={}
    for kind,bins in basis.items():
        out[kind]={}
        for name,(g,m,neg,idx,active) in bins.items():
            tp=event_counts(neg,idx,t,w[:,active])
            out[kind][name]={k:interval(v) for k,v in
                {'recall':divide(tp,g),'ceiling':divide(m,g),'no_matched_candidate':g-m,'removed_by_threshold':m-tp}.items()}
    return out


def image_draws(rng,n):
    return np.array([np.bincount(rng.integers(0,n,n),minlength=n) for _ in range(B)],dtype=np.uint8)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base',type=Path,required=True);a=ap.parse_args()
    private=a.base/'outputs/nightowls_evaluation_20261123'; public=E.ROOT/'docs/research/2026-11-23_nightowls_evaluation'
    result=json.loads((private/'point_estimates.json').read_text())
    receipt=json.loads((private/'receipt.json').read_text()); start=time.time()
    shutil.copy2(__file__,private/'executed_sources/uncertainty.py')
    receipt['hashes']['experiments/2026-11-23_nightowls_evaluation/uncertainty.py']=E.sha(Path(__file__))
    rng=np.random.default_rng(SEED)
    # This order is fixed before uncertainty computation, independent of scores.
    ws=image_draws(rng,1842); wc=image_draws(rng,1764)
    cluster=np.zeros((B,6),np.uint8)
    cluster[:,:5]=np.array([np.bincount(rng.integers(0,5,5),minlength=5) for _ in range(B)])
    cluster[:,5]=1
    known=cluster.copy(); known[:,5]=0
    dominant=np.zeros((B,6),np.uint8)
    dominant[:,[0,1,3,4]]=np.array([np.bincount(rng.integers(0,4,4),minlength=4) for _ in range(B)])
    dominant[:,5]=1
    wi=image_draws(rng,51782)
    np.savez_compressed(private/'bootstrap_draws.npz',source=ws,clear=wc,cluster=cluster,known=known,dominant=dominant,iid=wi)
    out={'attribution':'GPT Sol','replicates':B,'seed':SEED,'draw_order':['BDD source images','BDD clear images','5 known keys','4 nondominant known keys','NightOwls IID images'],
         'interval_rule':'2.5/97.5 percentiles of defined replicates only; observed source-infeasible transfer remains undefined',
         'assumptions':'Five recording keys need not be independent trips. Pooled cluster and dominant-out intervals condition on fixed unkeyed frames. IID-image sensitivity may be anti-conservative. BDD selection/clear keyframes treated as independent images; trained weights fixed.',
         'distinct_cluster_multisets_observed':len(set(map(tuple,cluster[:,:5]))),
         'dominant_key_omitted_replicates':int((cluster[:,2]==0).sum()),'arms':{},'contrasts':{}}
    boot={}
    for arm in E.ARMS:
        print('BOOT_START',arm,flush=True)
        cache=pickle.load(open(private/f'{arm}_cache.pkl','rb')); groups=cache['groups']
        groupidx=np.array([('R1','R2','R3','R4','R5','unkeyed').index(g) for g in groups])
        policies=cache['policies']; clear=Counts(cache['bdd']['clear'])
        thresholds={p:selected(cache['selection'][pol['min_height']],pol['target'],ws) for p,pol in policies.items()}
        armout={'selection':{},'panels':{}}; boot[arm]={}
        for p,pol in policies.items():
            ts=thresholds[p]
            armout['selection'][p]={'observed_threshold':pol['threshold'],'threshold':interval(ts),
                'feasible_replicates':int(np.isfinite(ts).sum()),'infeasible_replicates':int(np.isnan(ts).sum()),
                'observed_status':'FEASIBLE' if pol['threshold'] is not None else 'INFEASIBLE_SOURCE_TARGET'}
        for panel,recs in cache['panels'].items():
            p=E.ET.Population(recs); ct=Counts(p,groupidx); iid=Counts(p)
            armout['panels'][panel]={}; boot[arm][panel]={}
            ratio=result['arms'][arm]['resize_ratio']
            for mode,w,counts,unit in [(MODES[0],cluster,ct,groupidx),(MODES[1],known,ct,groupidx),
                                      (MODES[2],dominant,ct,groupidx),(MODES[3],wi,iid,np.arange(p.n))]:
                modeout={'oracles':{},'policies':{}}; boot[arm][panel][mode]={}
                hb=height_basis(p,unit,w,ratio)
                targetg=weighted(w,counts.g)
                for rho in (.6,.7,.8,.9,.95):
                    ot=selected(p,rho,w,unit)
                    op=counts.point(ot,w)
                    modeout['oracles'][str(rho)]={'threshold':interval(ot),
                        'zero_gt_replicates':int((targetg==0).sum()),
                        'infeasible_replicates':int((targetg>0).sum()-np.isfinite(ot).sum()),
                        'metrics':{k:interval(op[k]) for k in ('recall','fppi','precision','ceiling')}}
                for pname,pol in policies.items():
                    # Preserve bootstrap feasibility counts even when the observed source is infeasible.
                    t=thresholds[pname] if pol['threshold'] is not None else np.full(B,np.nan)
                    op=counts.point(t,w); co=clear.point(t,wc)
                    op['loss']=co['recall']-op['recall']
                    op['ceiling_difference']=co['ceiling']-op['ceiling']
                    op['threshold_miss_difference']=op['loss']-op['ceiling_difference']
                    rho=pol['target']; op['signed_gap']=rho-op['recall'];op['shortfall']=np.maximum(0,op['signed_gap'])
                    op['ceiling_shortfall']=np.maximum(0,rho-op['ceiling'])
                    op['removable_shortfall']=np.maximum(0,np.minimum(rho,op['ceiling'])-op['recall'])
                    # Observed source-infeasible policies have no ordinary transfer interval.
                    entry={'metrics':{k:interval(v) for k,v in op.items()},
                           'heights':height_boot(hb,w,t)}
                    modeout['policies'][pname]=entry
                    boot[arm][panel][mode][pname]={k:op[k] for k in ('recall','fppi','precision','ceiling','loss','ceiling_difference','threshold_miss_difference')}
                armout['panels'][panel][mode]=modeout
                print('BOOT_MODE',arm,panel,mode,'seconds',round(time.time()-start),flush=True)
            out['arms'][arm]=armout
            E.write(private/'uncertainty_partial.json',out)
            print('BOOT_PANEL',arm,panel,'seconds',round(time.time()-start),flush=True)
        with open(private/f'{arm}_bootstrap_metrics.pkl','wb') as f:pickle.dump(boot[arm],f,pickle.HIGHEST_PROTOCOL)
        E.write(public/'uncertainty.json',out)
        del cache,clear,ct,iid,p
    for left,right in ((E.ARMS[0],E.ARMS[1]),(E.ARMS[0],E.ARMS[2]),(E.ARMS[1],E.ARMS[2])):
        label=f'{left} minus {right}'; out['contrasts'][label]={}
        for panel,modes in boot[left].items():
            out['contrasts'][label][panel]={}
            for mode,pp in modes.items():
                out['contrasts'][label][panel][mode]={pname:{k:interval(vals[k]-boot[right][panel][mode][pname][k]) for k in vals} for pname,vals in pp.items()}
    out['elapsed_s']=round(time.time()-start,2)
    E.write(private/'uncertainty.json',out);E.write(public/'uncertainty.json',out)
    result['status']='COMPLETE';result['pending']=[]
    E.write(private/'point_estimates.json',result);E.write(public/'aggregate.json',result)
    receipt.update(status='COMPLETE',bootstrap_elapsed_s=out['elapsed_s'],completed_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    receipt['hashes']['bootstrap_draws.npz']=E.sha(private/'bootstrap_draws.npz')
    E.write(private/'receipt.json',receipt)
    # The receipt is counts/hashes/code metadata only; it contains no private identities.
    E.write(public/'receipt.json',receipt)
    print('BOOT_COMPLETE',out['elapsed_s'],flush=True)


if __name__=='__main__':main()
