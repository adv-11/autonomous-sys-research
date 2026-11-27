"""GPT Sol: aggregate-only scientific figures from actual completed evidence."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from local import OUT, HERE


def main():
    result=json.loads((OUT/'results.json').read_text())
    dest=HERE.parents[1]/'docs/research/2026-11-26_local_rtdetr_figures'
    dest.mkdir(exist_ok=True)
    colors=dict(baseline='#26619c',day_control='#7b6a9e',adaptation='#bd6826')
    labels=dict(baseline='Source baseline',day_control='Extra day',adaptation='Day + night')
    fig,axes=plt.subplots(1,2,figsize=(10,4),sharey=True)
    for ax,group in zip(axes,('clear_day','night')):
        for arm,record in result['arms'].items():
            with np.load(OUT/f'{arm}_{group}_curve.npz') as curve:
                ax.plot(curve['fppi'],curve['recall'],label=labels[arm],color=colors[arm],lw=1.2)
            op=record['operating_points']['source_fppi_1']
            if group in op['conditions']:
                p=op['conditions'][group]
                ax.scatter(p['fppi'],p['recall'],color=colors[arm],edgecolor='white',s=30,zorder=5)
        ax.set_xscale('symlog',linthresh=1)
        ax.set(xlabel='False positives / image (linear 0–1, then log)',
               title=group.replace('_',' ').title(),ylim=(0,1),xlim=(0,None))
        ax.legend(fontsize=8); ax.grid(alpha=.2)
    axes[0].set_ylabel('Pedestrian recall')
    fig.suptitle('RT-DETRv2 R18 · final EMA · seed 0\nFull native curves; dots use source FPPI ≤ 1 thresholds')
    fig.tight_layout(); fig.savefig(dest/'recall_fppi.png',dpi=180); plt.close(fig)
    arms=[a for a,r in result['arms'].items() if 'night' in r['operating_points']['source_fppi_1']['conditions']]
    x=np.arange(len(arms)); recalled=[];removable=[];unmatched=[];cd=[];td=[]
    for a in arms:
        r=result['arms'][a]; op=r['operating_points']['source_fppi_1']['conditions']
        mn=r['strata']['night']['ceiling']['recall']; mc=r['strata']['clear_day']['ceiling']['recall']
        rn=op['night']['recall']; rc=op['clear_day']['recall']
        recalled.append(rn);removable.append(mn-rn);unmatched.append(1-mn)
        cd.append(mc-mn);td.append((mn-rn)-(mc-rc))
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    axes[0].bar(x,recalled,label='Recalled',color='#497d9b')
    axes[0].bar(x,removable,bottom=recalled,label='Threshold-removable miss',color='#e4ad50')
    axes[0].bar(x,unmatched,bottom=np.array(recalled)+removable,label='No matched candidate',color='#a6a9ad')
    axes[0].set(ylim=(0,1),ylabel='Share of night GT',title='Absolute night outcome')
    axes[1].bar(x-.17,cd,width=.34,label='Ceiling difference',color='#a6a9ad')
    axes[1].bar(x+.17,td,width=.34,label='Threshold-miss difference',color='#e4ad50')
    axes[1].axhline(0,color='#555',lw=.6)
    axes[1].set(ylabel='Signed recall difference',title='Clear-day minus night decomposition')
    for ax in axes:
        ax.set_xticks(x,[labels[a] for a in arms]);ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
    fig.suptitle('Source FPPI ≤ 1 policy · ceiling conditional on native top300/floor1e-4')
    fig.tight_layout();fig.savefig(dest/'miss_split.png',dpi=180);plt.close(fig)


if __name__=='__main__':
    main()
