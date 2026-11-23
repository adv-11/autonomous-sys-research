"""GPT Sol: publication-ready measured figures, counts-only aggregates as inputs.

Run with the existing canonical tmp/pdfs/venv interpreter (Matplotlib installed).
"""
import json
import gzip
import hashlib
import pickle
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/research/2026-11-23_nightowls_evaluation'
def load(name):
    p=OUT/f'{name}.json'
    return json.loads(p.read_bytes() if p.exists() else gzip.decompress(p.with_suffix('.json.gz').read_bytes()))
R=load('aggregate')
U=load('uncertainty')
ARMS=('A_640','B_1280','C_640')
COLORS=('#2563a6','#c05b23','#278477')
PROFILE='reasonable/unused_nonpedestrian'
POLICY='h50_r0.8'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
    'axes.spines.right':False,'svg.fonttype':'none','savefig.dpi':300,'axes.titleweight':'bold'})


def save(fig,name):
    fig.savefig(OUT/f'{name}.png',bbox_inches='tight',facecolor='white')
    fig.savefig(OUT/f'{name}.svg',bbox_inches='tight',facecolor='white')
    svg=OUT/f'{name}.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines())+'\n',encoding='utf-8')
    plt.close(fig)


fig,axs=plt.subplots(1,2,figsize=(10.5,5),gridspec_kw={'width_ratios':[1.1,1]})
for j,(arm,c) in enumerate(zip(ARMS,COLORS)):
    rr=R['arms'][arm]
    p=rr['panels'][PROFILE]['pooled'][POLICY]
    ui=U['arms'][arm]['panels'][PROFILE]['cluster_conditional_unkeyed']['policies'][POLICY]['metrics']
    xs=np.array([0,1,2])+(.17*(j-1))
    ys=[rr['bdd_h50'][s]['policies'][POLICY]['operating']['recall'] for s in ('clear','night')]+[p['operating']['recall']]
    axs[0].plot(xs,ys,'o-',color=c,label=arm.replace('_',' / '),lw=1.5,ms=6)
    ci=ui['recall']['percentile_95']; y=ys[-1]
    axs[0].vlines(xs[-1],*ci,color=c,lw=1.6)
    axs[0].hlines(ci,xs[-1]-.035,xs[-1]+.035,color=c)
    axs[0].plot(xs[-1],p['ceiling']['recall'],'D',mfc='white',mec=c,ms=5)
    vals=p['loss_vs_bdd_h50_clear']
    ceil=100*vals['ceiling_difference']['value']; thr=100*vals['threshold_miss_difference']['value']
    axs[1].bar(j,ceil,color=c,alpha=.95,width=.58)
    axs[1].bar(j,thr,bottom=ceil,color=c,alpha=.30,width=.58,hatch='///',edgecolor=c)
    axs[1].text(j,ceil/2,f'{ceil:.1f}',ha='center',va='center',color='white',fontweight='bold')
    axs[1].text(j,ceil+thr/2,f'{thr:.1f}',ha='center',va='center')
    axs[1].text(j,ceil+thr+.6,f'{ceil+thr:.1f} pp',ha='center',fontsize=9)
axs[0].axhline(.8,c='.6',ls=':',lw=1)
axs[0].set(xticks=[0,1,2],xticklabels=['BDD clear-day','BDD night','NightOwls'],ylim=(0,1),ylabel='Pedestrian recall',title='Frozen source .80 policy')
axs[0].yaxis.set_major_formatter(PercentFormatter(1));axs[0].grid(axis='y',alpha=.18)
axs[0].legend(frameon=False,loc='lower left',fontsize=9)
axs[1].set(xticks=range(3),xticklabels=['A / 640','B / 1280','C / 640'],ylabel='BDD clear-day − NightOwls recall (pp)',title='Descriptive loss decomposition',ylim=(0,35))
axs[1].grid(axis='y',alpha=.18)
fig.text(.01,.02,'Filled: transferred recall. Open diamonds: candidate ceilings. Intervals: 1,000 paired recording/source-reselection draws,\nconditional on unkeyed frames. Solid bars: ceiling difference; hatched: threshold-miss difference. Primary unused_nonpedestrian.\nNative height ≥50; BDD occlusion unaligned. Fixed checkpoints; descriptive dataset contrast, G0 pending.',fontsize=8.5,va='bottom')
fig.tight_layout(rect=(0,.18,1,1));save(fig,'primary_transfer')


fig,ax=plt.subplots(figsize=(10.5,5))
groups=('R1','R2','R3','R4','R5','unkeyed','dominant_out')
x=np.arange(len(groups))
for j,(arm,c) in enumerate(zip(ARMS,COLORS)):
    panel=R['arms'][arm]['panels'][PROFILE]
    y=[panel[g][POLICY]['operating']['recall'] for g in groups]
    ceil=[panel[g][POLICY]['ceiling']['recall'] for g in groups]
    ax.plot(x+(j-1)*.14,y,'o',color=c,label=arm.replace('_',' / '),ms=7)
    ax.plot(x+(j-1)*.14,ceil,'_',color=c,ms=10)
ax.axhline(.8,c='.6',ls=':',lw=1)
p=R['arms'][ARMS[0]]['panels'][PROFILE]
labels=[f'{g.replace("dominant_out","R3 excluded")}\nGT {p[g][POLICY]["eligible_gt"]:,}' for g in groups]
ax.set(xticks=x,xticklabels=labels,ylabel='Pedestrian recall',ylim=(0,1),title='Recording composition changes the measured result')
ax.yaxis.set_major_formatter(PercentFormatter(1));ax.grid(axis='y',alpha=.18)
ax.legend(frameon=False,ncol=3,loc='lower right')
fig.text(.01,.02,'Dots: transferred recall; short horizontal marks: greedy candidate ceiling. Primary unused_nonpedestrian; Reasonable GT.\nR3 holds 65.4% of eligible GT. R5 has 149 boxes, below the fixed 150-box floor. Unkeyed is not a sixth recording.\nR3 exclusion retains 36,604 images / 2,637 GT / four known keys plus unkeyed; original source thresholds unchanged.',fontsize=8.5,va='bottom')
fig.tight_layout(rect=(0,.20,1,1));save(fig,'recording_sensitivity')


fig,axs=plt.subplots(1,2,figsize=(10.5,5.3),sharey=True)
bins=('0-16','16-32','32-64','64-128','>=128')
for ax,scale in zip(axs,('native','model_input')):
    for j,(arm,c) in enumerate(zip(ARMS,COLORS)):
        p=R['arms'][arm]['panels'][PROFILE]['pooled'][POLICY]['heights'][scale]['bins']
        y=[p[b]['recall'] if p[b]['recall'] is not None else np.nan for b in bins]
        xx=np.arange(5)+(j-1)*.14
        ax.plot(xx,y,'o-',color=c,label=arm.replace('_',' / '),ms=5)
    ax.set(xticks=range(5),xticklabels=['[0,16)','[16,32)','[32,64)','[64,128)','≥128'],ylim=(0,1),
           xlabel='GT box height (pixels)',title='Native height' if scale=='native' else 'Model-input height')
    ax.grid(axis='y',alpha=.18); ax.yaxis.set_major_formatter(PercentFormatter(1))
axs[0].set_ylabel('Pedestrian recall');axs[0].legend(frameon=False,fontsize=9)
def support(arm,scale):
    p=R['arms'][arm]['panels'][PROFILE]['pooled'][POLICY]['heights'][scale]['bins']
    return ' / '.join(f'{p[b]["gt"]:,}' for b in bins)
caption=(f'Native GT support by bin (all runs): {support(ARMS[0],"native")}.\n'
         f'Input GT support: A/C {support(ARMS[0],"model_input")}; B {support(ARMS[1],"model_input")}.\n'
         'Reasonable GT; full assignments reused; zero-support recall undefined. Primary unused_nonpedestrian; source .80.\n'
         'Input ratios .625 A/C, 1.25 B. Native ≥50 unchanged; scale, visibility and scene composition remain confounded.')
fig.text(.01,.02,caption,fontsize=8.5,va='bottom')
fig.tight_layout(rect=(0,.22,1,1));save(fig,'height_sensitivity')

# Publish only binned replicate counts; bootstrap arrays remain private.
PRIVATE=Path('C:/Users/Advait/autonomous-sys-research/outputs/nightowls_evaluation_20261123')
draws=np.load(PRIVATE/'bootstrap_draws.npz')
absent=draws['cluster'][:,2]==0
edges=np.linspace(0,1,31);histograms={}
fig,axs=plt.subplots(1,3,figsize=(10.5,4.2),sharex=True,sharey=True)
for ax,arm,c in zip(axs,ARMS,COLORS):
    metrics=pickle.load(open(PRIVATE/f'{arm}_bootstrap_metrics.pkl','rb'))
    x=metrics[PROFILE]['cluster_conditional_unkeyed'][POLICY]['recall']
    present=x[~absent & np.isfinite(x)];omitted=x[absent & np.isfinite(x)]
    ax.hist([present,omitted],bins=edges,stacked=True,color=[c,'.72'],label=['R3 drawn','R3 omitted'])
    ax.axvline(R['arms'][arm]['panels'][PROFILE]['pooled'][POLICY]['operating']['recall'],color='.15',ls='--',lw=1)
    ax.set(title=arm.replace('_',' / '),xlabel='Replicate recall',xlim=(0,1))
    ax.xaxis.set_major_formatter(PercentFormatter(1));ax.grid(axis='y',alpha=.18)
    histograms[arm]={'bin_edges':edges.tolist(),'R3_drawn':np.histogram(present,edges)[0].tolist(),
                     'R3_omitted':np.histogram(omitted,edges)[0].tolist(),'defined':int(np.isfinite(x).sum())}
axs[0].set_ylabel('Bootstrap replicates');axs[2].legend(frameon=False,fontsize=8)
fig.text(.01,.02,'Primary unused_nonpedestrian; Reasonable GT. 1,000 paired recording draws with source reselection; unkeyed weights fixed.\nDashed line: observed frozen-policy recall. Only five known keys; 126 possible recording multisets. Percentile intervals are descriptive.',fontsize=8.5,va='bottom')
fig.tight_layout(rect=(0,.20,1,1));save(fig,'bootstrap_distribution')
(OUT/'bootstrap_histogram.json').write_text(json.dumps(histograms,indent=1)+'\n',encoding='utf-8')
print('Wrote four measured PNG/SVG figures.')
(OUT/'plot_receipt.json').write_text(json.dumps({'attribution':'GPT Sol','matplotlib':matplotlib.__version__,
    'numpy_for_plotting':np.__version__,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.suffix in ('.png','.svg')}},indent=1)+'\n',encoding='utf-8')
