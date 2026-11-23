"""GPT Sol: build the dated plain-English project briefing from saved results.

CPU-only artifact generation. No model imports, inference or dataset access.
Requires reportlab, matplotlib, pymupdf and pypdf in a report-only environment.
"""
from pathlib import Path
import json
import textwrap
import hashlib

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output/pdf'
ASSETS = OUT / 'research_progress_20261123_assets'
ASSETS.mkdir(parents=True, exist_ok=True)
PDF = OUT / 'threshold_transfer_research_progress_2026-11-23.pdf'
W, H = 595.276, 841.89
M = 46
CW = W - 2*M
NAVY = '#16324A'; TEAL = '#007E87'; ORANGE = '#DC8633'; BLUE = '#4C78A8'
INK = '#24394A'; MUTED = '#526575'; LIGHT = '#EAF2F5'
plt.rcParams.update({'font.family':'DejaVu Sans', 'font.size':10, 'axes.spines.top':False,
                     'axes.spines.right':False, 'axes.labelcolor':INK, 'text.color':INK,
                     'xtick.color':INK, 'ytick.color':INK, 'figure.facecolor':'white'})

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))

BASE = 'docs/research/2026-11-15_bdd_clearday_transfer/'
FOLLOW = 'docs/research/2026-11-17_threshold_remedies/'
arms = {a: load((FOLLOW if a=='B2_1280' else BASE)+a+'.json')
        for a in ['A_640','B_1280','C_640','B2_1280']}
B = arms['B_1280']; B2 = arms['B2_1280']
conds = ['clear_day','cloudy_day','rainy_day','snowy_day','dawn_dusk','night']
labels = ['Clear day','Cloudy day','Rain, day','Snow, day','Dawn/dusk','Night']
rows = [B['transfer']['0.8']['val:'+k] for k in conds]

def savefig(name):
    p = ASSETS / (name+'.png')
    plt.savefig(p, dpi=190, bbox_inches='tight', facecolor='white'); plt.close()
    return p

fig, ax = plt.subplots(figsize=(8.2,3.6))
x = np.arange(len(rows)); rec = [r['operating']['recall']*100 for r in rows]
err = np.array([[r['recall_ci'][0]*100 for r in rows], [r['recall_ci'][1]*100 for r in rows]])
ax.bar(x,rec,color=[BLUE]*5+[TEAL],width=.63)
ax.errorbar(x,rec,yerr=np.vstack([np.array(rec)-err[0],err[1]-np.array(rec)]),fmt='none',ecolor=INK,capsize=3)
for i,v in enumerate(rec): ax.text(i,v+6,f'{v:.1f}%',ha='center',fontsize=10)
ax.set(xticks=x,xticklabels=labels,ylim=(0,103),ylabel='Pedestrians found (%)')
ax.axhline(80,color=MUTED,lw=.8,ls='--'); ax.grid(axis='y',alpha=.15); ax.set_axisbelow(True)
condition_chart = savefig('condition_recall')

fig,ax=plt.subplots(figsize=(8,2.7))
for i,(key,title) in enumerate([('val:clear_day','Clear-day test'),('val:night','Night test')]):
    r=B['transfer']['0.8'][key]; found=r['operating']['recall']*100
    removed=(r['ceiling_recall']-r['operating']['recall'])*100; absent=(1-r['ceiling_recall'])*100
    left=0
    for v,col in [(found,TEAL),(removed,ORANGE),(absent,'#9EABB5')]:
        ax.barh(i,v,left=left,color=col,height=.52); ax.text(left+v/2,i,f'{v:.1f}%',ha='center',va='center',color='white',fontweight='bold');left+=v
ax.set(yticks=[0,1],yticklabels=['Clear-day test','Night test'],xlim=(0,100),xlabel='Share of all eligible pedestrians (%)');ax.invert_yaxis()
ax.legend([plt.Rectangle((0,0),1,1,color=c) for c in [TEAL,ORANGE,'#9EABB5']],['Found','Box exists, threshold removes it','No matched box'],loc='lower center',bbox_to_anchor=(.5,-.55),ncol=1,frameon=False)
miss_chart=savefig('absolute_misses')

fig,ax=plt.subplots(figsize=(7.5,3.0))
xs=[2.365,4.79,20.96];ys=[67.921,72.3,81.3]
ax.plot(xs,ys,'o-',color=TEAL,lw=2,ms=8)
for x0,y0,t,offset in zip(xs,ys,['Frozen day threshold','Night threshold:\nsimilar FP budget','Night threshold:\naim for 80% recall'],[(9,-22),(12,5),(-130,-35)]):
    ax.annotate(t,(x0,y0),xytext=offset,textcoords='offset points',fontsize=9)
ax.set(xlim=(0,24),ylim=(63,85),xlabel='False alarms per image on night test',ylabel='Night recall (%)');ax.grid(alpha=.18)
remedy_chart=savefig('remedy_cost')

fig,ax=plt.subplots(figsize=(7.8,3.3))
names=['A: 640 / seed 0','C: 640 / seed 1','B: 1280 / seed 0','B2: 1280 / seed 1']
vals=[45.9,46.0,55.3,57.3]
ax.barh(names,vals,color=[BLUE,BLUE,TEAL,TEAL]);ax.invert_yaxis()
for i,v in enumerate(vals): ax.text(v+1,i,f'{v:.1f}%',va='center')
ax.set(xlim=(0,70),xlabel='Night recall (%) at source FPPI budget 1');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
seed_chart=savefig('resolution_seed')

c=canvas.Canvas(str(PDF),pagesize=(W,H))
c.setTitle('Threshold transfer research | Progress as of 23 November 2026')
c.setAuthor('GPT Sol | AI-assisted briefing from GPT and Claude research records')
style=ParagraphStyle('body',fontName='Helvetica',fontSize=11,leading=16,textColor=HexColor(INK),spaceAfter=8)
smallstyle=ParagraphStyle('small',parent=style,fontSize=9,leading=12)
page_no=0; y=0
def para(text, size=11, after=10, color=INK):
    global y
    s=ParagraphStyle('p',parent=style,fontSize=size,leading=size*1.43,textColor=HexColor(color))
    p=Paragraph(text,s); _,h=p.wrap(CW,800)
    if y-h<55: raise ValueError(f'Page {page_no} overflow: {text[:50]} ({y-h})')
    p.drawOn(c,M,y-h); y-=h+after
def title(kicker,heading,sub=''):
    global page_no,y
    if page_no: c.showPage()
    page_no+=1
    c.setFillColor(HexColor(NAVY));c.rect(0,H-10,W,10,fill=1,stroke=0)
    c.setFont('Helvetica-Bold',9);c.setFillColor(HexColor(TEAL));c.drawString(M,H-47,kicker.upper())
    y=H-69
    para(heading,25,12,NAVY)
    if sub: para(sub,10,19,MUTED)
    c.setStrokeColor(HexColor('#CCD9DF'));c.line(M,43,W-M,43)
    c.setFont('Helvetica',8);c.setFillColor(HexColor(MUTED));c.drawString(M,29,'THRESHOLD TRANSFER  |  23 NOV 2026  |  GPT SOL BRIEFING')
    c.drawRightString(W-M,29,f'{page_no:02d}')
def h(text): para(text,14,7,NAVY)
def bullet(text): para('&#8226; '+text,11,8)
def note(text): para('<b>Read this carefully.</b> '+text,10,12,TEAL)
def table(headers, rows, widths=None, fs=9):
    global y
    widths=widths or [CW/len(headers)]*len(headers)
    s=ParagraphStyle('cell',parent=smallstyle,fontSize=fs,leading=fs*1.35)
    hs=ParagraphStyle('head',parent=s,textColor=white,fontName='Helvetica-Bold')
    data=[[Paragraph(str(v),hs) for v in headers]]+[[Paragraph(str(v),s) for v in row] for row in rows]
    t=Table(data,colWidths=widths,hAlign='LEFT');t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),HexColor(NAVY)),('ROWBACKGROUNDS',(0,1),(-1,-1),[white,HexColor('#EFF4F6')]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
        ('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,-1),(-1,-1),.4,HexColor('#CAD6DD'))]))
    _,th=t.wrap(CW,800)
    if y-th<55: raise ValueError(f'Table overflow page {page_no}')
    t.drawOn(c,M,y-th);y-=th+16
def img(path,maxh=240):
    global y
    im=ImageReader(str(path));iw,ih=im.getSize();scale=min(CW/iw,maxh/ih);dw,dh=iw*scale,ih*scale
    c.drawImage(im,M+(CW-dw)/2,y-dh,dw,dh,mask='auto');y-=dh+13
def flow(items, colors=None, height=72):
    global y
    gap=12;bw=(CW-gap*(len(items)-1))/len(items)
    for i,text in enumerate(items):
        x=M+i*(bw+gap);col=(colors or [LIGHT]*len(items))[i]
        c.setFillColor(HexColor(col));c.roundRect(x,y-height,bw,height,7,fill=1,stroke=0)
        p=Paragraph(text,ParagraphStyle('flow',parent=smallstyle,alignment=1,fontSize=9,leading=12));_,ph=p.wrap(bw-12,height-8);p.drawOn(c,x+6,y-height+(height-ph)/2)
        if i<len(items)-1:
            c.setStrokeColor(HexColor(TEAL));c.line(x+bw+1,y-height/2,x+bw+gap-1,y-height/2)
            c.line(x+bw+gap-4,y-height/2+3,x+bw+gap-1,y-height/2);c.line(x+bw+gap-4,y-height/2-3,x+bw+gap-1,y-height/2)
    y-=height+18

title('Project update / start here','Can a daytime detection threshold be trusted at night?',
      'Plain-English research briefing | Evidence available as of November 23, 2026 | Repository baseline: 5251312 (PRs 14 and 15 merged)')
para('<b>My goal:</b> understand why a pedestrian detector loses recall when its daytime decision threshold is reused at night, then develop and test an improvement that survives strong baselines.',13,18)
flow(['<b>Train on clear day</b><br/>Learn pedestrian boxes', '<b>Choose threshold on day</b><br/>Freeze the decision rule','<b>Test at night</b><br/>Measure misses and false alarms'])
h('What is already real')
bullet('<b>Four full fine-tuning runs are complete.</b> YOLO11s was trained for 100 epochs per run, at two image sizes and two random seeds, on Berkeley DeepDrive 100K (BDD100K) clear-day images.')
bullet('<b>The night loss replicates.</b> At an 80% source recall objective, the two 1280-pixel models find about 68-70% of night pedestrians, versus 81-82% on clear-day test images.')
bullet('<b>Threshold adjustment helps, but costs false alarms.</b> A night-calibrated threshold can recover roughly 3-7 percentage points at a similar calibration FP budget. Recovering about 80% night recall costs roughly 17-21 false alarms per image in the two high-resolution runs.')
bullet('<b>External inference is ready.</b> NightOwls predictions are saved. Its merged scoring rules now permit the fixed CPU evaluation; that result is not in this briefing.')
note('There is no established novel method yet. The project has a concrete empirical question, trained baselines and informative negative results. RT-DETR is the next model family, not an already measured improvement.')
para('<b>Fast reading:</b> pages 2-3 explain the idea and architectures; pages 6-9 show training and results; pages 10-12 explain external tests, novelty and next actions. Page 13 is the glossary and reading guide.',10)

title('02 / the question','What does "threshold transfer" actually mean?')
para('A detector proposes boxes around things it thinks are pedestrians. Each box gets a score. The threshold is the minimum score needed to show the box. Raising it usually removes false alarms, but also removes some real people.')
flow(['<b>Image</b><br/>A street scene','<b>Candidate boxes</b><br/>Boxes + scores','<b>Threshold</b><br/>Keep score >= t','<b>Output</b><br/>Kept detections'])
h('A simple example - illustration, not an experiment')
table(['Pedestrian candidate','Day score','Night score','At threshold 0.50'],[['Same kind of correct box','0.82','0.42','Day: kept. Night: removed.'],['False alarm','0.30','0.20','Removed in both.'],['Pedestrian with no usable box','No box','No box','Threshold cannot recover it.']], [150,75,75,CW-300])
h('Two different reasons for a miss')
bullet('<b>Box exists, score too low:</b> lowering the threshold might recover the person. It will also admit extra false alarms.')
bullet('<b>No usable candidate:</b> no pedestrian-class box matches the labelled person under the fixed overlap and score-floor rules. A different threshold alone cannot fix this.')
para('The <b>candidate ceiling</b> is the recall obtained by keeping all saved candidates. It is a ceiling for this saved pipeline, not proof that the network or another method could never detect the person.')
h('The research question in one sentence')
para('<b>When a clear-day threshold fails at night, how much is a decision-rule problem, how much is a candidate or ranking problem, and which intervention improves the tradeoff on new data?</b>',13)
para('A score is not automatically a trustworthy probability. Changing every score with the same strictly increasing formula preserves ordering; if the source threshold is reselected consistently, the kept boxes stay the same. That is why global score recalibration is a control, not a recall remedy.',10)

title('03 / architectures','What has been trained, and what changes with RT-DETR?', 'Conceptual diagrams: simplified components, not benchmark measurements.')
h('Completed baseline: YOLO11s - You Only Look Once')
flow(['<b>Image</b><br/>Resize / pad','<b>Backbone + neck</b><br/>Extract and combine features','<b>Detection head</b><br/>Many boxes + class scores','<b>NMS + threshold</b><br/>Remove duplicates; filter'],height=83)
para('The completed runs use YOLO11s initialized from Common Objects in Context (COCO) weights, then fine-tuned on ten BDD classes. Pedestrians and riders remain separate classes. Non-maximum suppression (NMS) removes overlapping duplicate predictions.',10,18)
h('Next family: RT-DETR - Real-Time Detection Transformer')
flow(['<b>Image + backbone</b><br/>Multi-scale features','<b>Hybrid encoder</b><br/>Within / across-scale processing','<b>Queries + decoder</b><br/>Refine selected object queries','<b>Boxes + threshold</b><br/>Native end-to-end output'],height=83)
para('RT-DETR uses an efficient hybrid encoder and a transformer decoder. Its native design produces an end-to-end detection set without the usual NMS stage. The exact RT-DETR / RT-DETRv2 checkpoint, training recipe and query limit still need to be frozen for this project.',10)
table(['Why compare families?','What it will not prove by itself'],[['Ask whether the transfer pattern persists under a different detection pipeline.','An advantage is not automatically caused by transformers or by removing NMS.'],['Test the same data split, source-only threshold and night metrics.','Different recipes, capacity, scale and pretrained data remain confounders.']], [CW/2,CW/2])
para('Source for the RT-DETR sketch: Zhao et al., "DETRs Beat YOLOs on Real-time Object Detection," arXiv:2304.08069v3, and the official lyuwenyu/RT-DETR repository (checked 2026-11-23). No RT-DETR training result is claimed here.',9)

title('04 / history in order','What happened, and why each stage mattered')
table(['When','Work completed','Research consequence'],[
['Nov 3-6','Source audits, literature corrections, deterministic evaluator, data adapters and peer review.','Established what can be measured; corrected paper and dataset claims.'],
['Nov 6-9','Real data acquisition and ACDC sequence / near-duplicate audit.','Official split names did not ensure independence. A four-condition adaptation bridge was not supported.'],
['Nov 10','Pretrained YOLO11s candidate-floor/cap and resolution experiments.','Candidate-policy hypothesis was null on the fixed panel. Higher resolution helped.'],
['Nov 10-11','Cached scale fusion, agreement gate, low-detail enlargement and recall-audit studies.','Simple baselines/prior art closed several apparent novelty opportunities.'],
['Nov 11-13','YOLO26 two-head study and head x postprocessing controls.','Observed ranking differences survived controls, but were not established as night-specific.'],
['Nov 13-17','NightOwls labels, schema/ignore policy, failed bounded access attempts, then full archive verification.','External data became usable; failures and privacy restrictions were preserved.'],
['Nov 15-16','Fine-tuned YOLO11s runs A/B/C for 100 epochs each.','First trained BDD threshold-transfer result; high targets were often infeasible.'],
['Nov 17-18','Run B2, night-calibration remedies, ACDC inference and NightOwls prediction capture.','Seed replication and FP-cost analysis made the claim narrower and stronger.'],
['Nov 23','PR14 and PR15 merged; this briefing prepared.','NightOwls scoring unblocked. RT-DETR and fine-tuning authorized as the next direction.']
], [57,220,CW-277],fs=9)
note('Early pretrained panels and later trained BDD experiments use different tasks, populations and checkpoints. Their percentages should not be pooled into one performance curve.')

title('05 / data and separation','What data are being used?')
table(['Dataset / full name','Role and current state','Main caution'],[
['BDD100K: Berkeley DeepDrive 100K','Core training and daytime-to-night test. Legacy 2018 labels; images acquired and used.','Not the revised Detection 2020 release; image mirror publisher identity unverified, archive hash fixed.'],
['ACDC: Adverse Conditions Dataset with Correspondences','External descriptive fog, night, rain, snow panel: 2,006 adverse + 1,003 labelled reference images.','Related views / recordings; references can contain different people. Not a causal weather experiment.'],
['NightOwls','External night test. 51,848 archive images inferred; frozen evaluation cohort has 51,782 images and 7,631 eligible pedestrian boxes.','Five known recording keys plus unkeyed frames; adjacent frames repeat people.'],
['COCO: Common Objects in Context','Pretrained weight source and early exploratory image panels.','Not a verified clean-day deployment sample.'],
['KITTI: Karlsruhe Institute of Technology and Toyota Technological Institute driving benchmark','Local inventory / diagnostic preparation.','Not the main trained threshold-transfer result.']
], [124,216,CW-340],fs=9)
h('The core BDD split')
flow(['<b>10,635 clear-day train</b><br/>Update model weights','<b>1,842 source selection</b><br/>Choose threshold; no training','<b>10,000 val test</b><br/>Clear / night / weather results'],height=76)
para('A further 2,000 BDD train-night images are used only for exploratory night-calibration remedies. They were not in clear-day training. Night calibration and night test are distinct.',10)
note('Empty images are retained. Removing them would distort false alarms per image. Threshold selection, calibration and final test have different jobs and must stay separated.')

title('06 / actual training','Yes - the models have already been fine-tuned')
table(['Run','Image size','Seed','Training','Status'],[['A','640 px','0','100 epochs','Complete'],['C','640 px','1','100 epochs','Complete'],['B','1280 px','0','100 epochs','Complete'],['B2','1280 px','1','100 epochs','Complete']], [48,88,45,110,CW-291])
para('All four start from COCO-pretrained YOLO11s, learn ten BDD classes, use an effective batch of 64 and evaluate the final moving-average checkpoint (<b>last.pt</b>). A seed changes training randomness; it is a repeat, not a new architecture.',10)
img(ROOT / BASE / 'bdd_transfer_training_curves.png',240)
para('<b>Measured training curves from runs A/B/C.</b> B2 was trained later and is summarized in the table, not drawn as an extra curve. Epoch means one pass through the training set. mAP is mean Average Precision: a training-monitoring detection metric, not the threshold-transfer answer.',9)
para('Selection mAP peaked around epochs 50-60 and then softened. The fixed final checkpoint was still evaluated; a better-looking test checkpoint was not substituted. Future RT-DETR work should use a declared development-only stopping rule rather than automatically repeating 100 epochs.',10)
para('Approximate peak memory: 7.8 GiB for A/C, 16 GiB for B/B2. All GPU work used Colab L4 sessions, not the local GPU. Mixed-precision skipped updates and the final checkpoint hashes are recorded in the source ledgers.',10)

title('07 / main measured answer','A clear-day threshold loses recall at night', 'Run B: 1280 px, seed 0. Threshold chosen to reach 80% recall on clear-day selection data; then frozen.')
para('The frozen primary arm A (640 px) was infeasible at 80%. B was added before training and supplies this feasible preregistered result.',10,8)
img(condition_chart,240)
para('Bars show test recall; whiskers are 95% image-bootstrap intervals conditional on this trained checkpoint. The dashed line is the source objective, not a guarantee on another sample.',9)
table(['Test condition','Recall','False alarms / image','People / images'],[[labels[i],f"{r['operating']['recall']*100:.1f}%",f"{r['operating']['fppi']:.2f}",f"{int(r['operating']['gt']):,} / {int(r['operating']['images']):,}"] for i,r in enumerate(rows)], [136,75,139,CW-350])
para('<b>Interpretation:</b> night loses 13.2 percentage points relative to clear-day test (81.1% to 67.9%). It also produces fewer false alarms at the same threshold (4.53 to 2.37 per image). A quieter output is therefore not automatically a better detector.',11)
note('Night is an observed dataset condition. These comparisons do not isolate darkness from scene composition, annotation policy, geography or camera exposure.')

title('08 / why detections are lost','Separate absolute misses from the extra night loss')
img(miss_chart,245)
para('The night row says that about 68% of labelled pedestrians are found, 15% have a saved matched box removed by the threshold, and 17% have no matched candidate. These are absolute shares of all eligible night pedestrians.',11)
table(['Quantity, run B','Plain meaning','Value'],[['Absolute unmatched night share','No saved matched pedestrian candidate at night.','17.0%'],['Extra unmatched share vs day','17.0% night minus 10.3% clear day.','6.7 pp'],['Extra threshold-miss share vs day','15.1% night minus 8.5% clear day.','6.6 pp'],['Total clear-to-night recall loss','6.7 + 6.6, allowing rounding.','13.2 pp']], [155,273,CW-428])
h('What "no matched candidate" means here')
para('The saved pipeline uses a score floor of 0.0001 and overlap of at least 0.50. A badly placed box, a person labelled as another class, or a box removed earlier in the pipeline can contribute. This is not a claim that the image contains no usable visual information.',10)
note('Earlier text used "6-9% no matched candidate" as shorthand. The corrected meaning is the <b>excess over clear day</b>. The absolute unmatched night share is 17-29% across runs. The merged report now preserves a dated erratum.')
para('Changing the score floor or overlap requirement changes the split. Training seeds also move it. Both components are useful diagnostics, but neither is a stable causal explanation by itself.',10)

title('09 / remedies and repeats','What helped - and what did it cost?')
img(remedy_chart,218)
para('Exploratory, post hoc follow-up: measured run B night-calibration remedies, rounded from the report. The equal-FP-budget point uses its calibration budget, not an exact guarantee of the same test false-positive rate.',9)
table(['Run B policy','Night recall','Night FPPI','Interpretation'],[['Reuse daytime threshold','67.9%','2.37','Starting point.'],['Night threshold, similar FP budget','72.3%','4.79','About +4.4 pp; more false alarms.'],['Night threshold, aim for 80% recall','81.3%','20.96','About +13.3 pp; very large FP cost.'],['Global monotone recalibration','Unchanged','Unchanged','Same ordering and equivariant threshold reselection.']], [153,66,66,CW-285])
para('Per-condition Platt scaling changes recall little (at most about 1.2 pp in reported rows). A threshold can move along the night tradeoff curve; it cannot create missing candidates or make the curve equal to daytime.',10)
para('<b>Uncertainty matters:</b> for B at the 80% target, 138 of 1,000 bootstrap night-calibration samples could not attain the target. The equal-recall interval uses only feasible samples. Also, a calibration FPPI budget can be exceeded on fresh test images.',10)

title('10 / resolution and external context','Bigger images help recall; the night gap is less settled')
img(seed_chart,215)
para('<b>Exploratory, post hoc comparison.</b> At source FPPI budget 1, night recall improves by 9.4 pp for B vs A and 11.3 pp for B2 vs C. That resolution benefit appears in both seed-matched comparisons. The change in <b>clear-day-minus-night recall loss</b> differs by seed pair: +0.8 pp loss for seed 0 versus -2.7 pp for seed 1.',10)
table(['Important result','What it means'],[['High recall is sometimes infeasible','All-height source ceilings are about 77% at 640 and 88% at 1280. The original 90% and 95% targets cannot be reached by lowering these thresholds. A/C also cannot reach 80% on the all-height population.'],['B2 repeats the main night pattern','At source 80%, B2 has 81.6% clear-day vs 69.6% night recall (B: 81.1% vs 67.9%).'],['ACDC is a harder domain','B/B2 recall is about 48-75% across adverse conditions, and only 54-63% on normal reference views.'],['ACDC reference is not a perfect control','Different people, sizes, cameras and related recordings prevent a simple causal weather interpretation.']], [165,CW-165])
para('Only two seeds per size were trained. Image-bootstrap intervals do not estimate training-seed variability or dependence between routes and drivers. A new model-family comparison must retain those limits.',10)

title('11 / independent test','NightOwls: ready for scoring, not a result yet')
flow(['<b>Done</b><br/>Publisher archive verified','<b>Done</b><br/>All four prediction files retrieved','<b>Done</b><br/>Scoring contract merged','<b>Next</b><br/>CPU score + review'],height=82)
para('The frozen primary analysis covers A/B/C. B2 predictions exist but are outside that contract and must not be quietly promoted into its primary comparison. The cohort excludes two dusk frames and the original 64 access-pilot frames.',10)
table(['Fixed before scoring','Rule'],[['Population','51,782 night images, including empty frames; 7,631 eligible pedestrian boxes.'],['Primary eligibility','Native height at least 50 px, nonignored, not marked occluded. Null occlusion follows the declared SDK convention.'],['Source threshold','Reselect on BDD clear-day pedestrians >=50 px; primary target 80%, sensitivities 90% and 95%. No NightOwls tuning.'],['Profiles','Primary unused_nonpedestrian; fixed person-compatible ignore sensitivity. Label every FPPI result with its profile.'],['Dependence','Five known recording keys; 1,304 unkeyed frames. Report per-recording and dominant-recording sensitivity.'],['Inference','Already completed for 51,848 images per run; no new GPU allocation needed to score.']], [135,CW-135])
note('Height alignment does not align occlusion, scene content, input object size or box definitions. This is an external transfer test, not proof that a change in illumination caused a result.')
para('The next deliverable is an immutable first scoring record, measured plots and a separate independent review. A disappointing external result will narrow the claim; it will not trigger a search over thresholds on the same test.',10)

title('12 / contribution and direction','How this becomes a research contribution')
para('<b>My end goal is a defensible answer and, if supported, a useful new method.</b> Another detector or a nicer graph is not enough. The immediate value is to learn which failure survives threshold, scale, seed and dataset controls.',12)
table(['Evidence status','What belongs in a paper today'],[['Supported on current panels','Clear-day thresholds lose night recall; missing candidates and threshold removals both contribute; recovery has a false-positive cost.'],['Closed or negative directions','Cap/floor hypothesis on the early panel; ordinary fusion/agreement as a new method; enlargement gain as new detail; audit method novelty.'],['Not established','A general night-specific ranking mechanism; a novel detector/calibrator; causal darkness; cross-family generalization.'],['Next decisive comparison','RT-DETR fine-tuned on the same clear-day training split; source-only selection; fixed BDD and external evaluation.']], [140,CW-140])
h('The next research sequence')
bullet('<b>1. Finish external validation:</b> score saved NightOwls A/B/C predictions under the merged contract. No repeat inference.')
bullet('<b>2. Establish RT-DETR baseline:</b> choose and pin one official model/recipe; fine-tune on the same clear-day split. Bound Colab cost using measured throughput, save weights and candidates, and stop the owned session.')
bullet('<b>3. Test a training intervention:</b> compare clear-day-only training with a separately frozen night-adaptation arm using training-side labels. Keep night calibration and final tests out of training. Give clear-day retention and night FP cost equal prominence.')
bullet('<b>4. Earn a method claim:</b> only pursue a new ranking or training idea if it improves a residual failure beyond ordinary fine-tuning, scale and night-threshold baselines on untouched evaluation data.')
para('Steps 2-3 are a proposed direction authorized by the latest instruction, not completed results or a frozen new experiment. Before allocation, record the exact hypothesis, checkpoint, partitions, comparison, kill rule and bounded CU estimate. G0, the project readiness gate, remains pending.',10)

title('13 / glossary, resources and reading','What to read, and what to remember')
table(['Term','Plain-English meaning'],[['Recall / TP / FN','Share of labelled people found / true positive / missed labelled person.'],['FP / FPPI','False positive / false positives per image. Empty images count in the denominator.'],['IoU','Intersection over Union: box overlap. At least 0.50 is required in the main project matcher.'],['Calibration / Platt scaling','Making scores agree better with a named correctness target; Platt scaling fits a sigmoid score map. Better probabilities need not improve ranking.'],['Seed / epoch / fine-tuning','Training randomness / one pass through training data / adapting pretrained weights.'],['Bootstrap / percentage point','Resampling to describe uncertainty / absolute difference between percentages. 81% to 68% is -13 pp.'],['G0 / CU','Project readiness gate / Colab compute unit. A merged PR does not pass the gate.']], [139,CW-139],fs=9)
h('Cost and limits')
para('Recorded project-owned Colab spend through stage 2 is about <b>60.9 displayed CU</b>: 5.06 earlier + 32.38 first training stage + 23.48 follow-up. Last verified teardown recorded zero assignments. This is historical evidence, not a live account reading. A separate balance drop from 262.56 to 200 CU is unexplained and is not charged to these experiment ledgers.',10)
h('Reading map - start with the first two')
para('1. <b>Core result:</b> docs/research/2026-11-15_bdd_clearday_transfer.md, including its dated erratum.<br/>2. <b>Remedies and replication:</b> docs/research/2026-11-17_threshold_remedies.md.<br/>3. <b>External rules:</b> docs/research/2026-11-18_nightowls_contract_v2.md, then the linked version 1 and BDD reference.<br/>4. <b>Earlier negative results:</b> docs/research/2026-11-10_checkpoint.md and 2026-11-11_audit_checkpoint.md.<br/>5. <b>RT-DETR primary sources:</b> <link href="https://arxiv.org/abs/2304.08069">arxiv.org/abs/2304.08069</link> and <link href="https://github.com/lyuwenyu/RT-DETR">github.com/lyuwenyu/RT-DETR</link>.',9)
para('<b>Attribution:</b> GPT Sol prepared this briefing from merged research records. Claude Opus executed the four BDD training runs and follow-up inference; GPT Sol and Claude Opus performed the recorded independent reviews. Earlier GPT Astra work is historical. Charts in this briefing are saved-result summaries, not new evaluations. No restricted images, boxes or native image IDs are included.',9)
c.save()

manifest={'date':'2026-11-23','prepared_by':'GPT Sol','baseline':'5251312','pdf':str(PDF.relative_to(ROOT)),
          'pages':page_no,'source_arms':{k:v['preds_sha256'] for k,v in arms.items()},
          'pdf_sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),
          'note':'Synthesis only; no new inference or NightOwls scoring.'}
(OUT/'research_progress_20261123_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps(manifest,indent=2))
