"""Claude Opus 5.5, 2026-11-13: GT-level ranking diagnostic on cached head-policy outputs.

Posthoc finite-panel diagnosis of existing GPT Sol Stage A outputs; zero inference.
For each eligible GT the established evaluator's greedy prefix matching gives an
"entry score": the score of the candidate that matches it (TP at threshold t iff entry>=t).
Two frozen maps then place each entry score on a common scale per cell:
  r = source recall at that score (source_selection panel only; monotone, no reselection)
  f = target-panel FPPI at that score (descriptive; uses target labels, never selects anything)
Contrasts compare heads within a common bundle (K or N) on jointly ceiling-covered GT,
and decompose the original-threshold head TP gap exactly into a jointly-covered
ranking component and a single-ceiling availability component.

Usage: python -B experiments/2026-11-13_opus_cached_mechanism.py ROOT
ROOT = private head_policy_20261113 evidence root. Private per-GT rows go to the
ignored outputs/opus_cached_mechanism_20261113/.
"""
from __future__ import annotations
import bisect
import collections
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pilot', Path(__file__).with_name('2026-11-10_transfer_pilot.py'))
pilot = importlib.util.module_from_spec(spec); spec.loader.exec_module(pilot)
read, write, sha = pilot.read, pilot.write, pilot.sha
NATIVE = {('o2o', 'K'), ('o2m', 'N')}
SAVED = REPO/'docs/gpt/2026-11-13_sol_head_policy_mechanism.json'
OUT = REPO/'docs/claude'; PRIV = REPO/'outputs/opus_cached_mechanism_20261113'
PANELS = ['coco_reference', 'fog', 'night', 'rain', 'snow', 'fog_normal', 'night_normal', 'rain_normal', 'snow_normal']


def load_cells(root, cfg, manifest):
    """Same cell reconstruction as head_policy_mechanism.aggregate (incl. final-batch correction)."""
    result = root/'results'; a_ids = {i['image_id'] for p in manifest['panels'].values() for i in p['images']}
    raw = {c: dict(schema_version=pilot.PY_SCHEMA, predictions=[], degenerate_predictions=[],
                   provenance=dict(evaluated_image_ids=[])) for c in cfg['cells']}
    for h in ('o2o', 'o2m'):
        corr = {}; cdir = result/'correction_last_native_batch'
        if (cdir/f'{h}_batch_0000.json').exists():
            b = read(cdir/f'{h}_batch_0000.json'); assert b['validated']
            for j, iid in enumerate(b['image_ids']):
                corr[iid] = dict(native=b['native'][j], cells={p: rows[j] for p, rows in b['cells'].items()})
        for path in sorted(result.glob(f'{h}_batch_*.json')):
            b = read(path); assert b['validated']
            for policy in ('K', 'N'):
                if policy not in b['cells']: continue
                cell = h+'_'+policy; native = (h, policy) in NATIVE
                rows = b['native'] if native else b['cells'][policy]
                for iid, values in zip(b['image_ids'], rows):
                    if iid not in a_ids: continue
                    if iid in corr: values = corr[iid]['native'] if native else corr[iid]['cells'][policy]
                    raw[cell]['provenance']['evaluated_image_ids'].append(iid)
                    for j, (x1, y1, x2, y2, score, cls) in enumerate(values):
                        assert cls == 0
                        pred = dict(candidate_id=iid+f':{j:04d}', image_id=iid, category='human', bbox=[x1, y1, x2-x1, y2-y1], score=score)
                        if x1 == x2 or y1 == y2: raw[cell]['degenerate_predictions'].append(dict(**pred, native_xyxy=[x1, y1, x2, y2]))
                        else: raw[cell]['predictions'].append(pred)
    return raw


def entry(ev):
    return {r['annotation_id']: r['score'] for r in ev.rows if r['outcome'] == 'TP'}


def at_or_above(sorted_desc_neg, s):
    """Count of values >= s given an ascending list of negated values."""
    return bisect.bisect_right(sorted_desc_neg, -s)


def main(root):
    t0 = time.process_time(); root = Path(root)
    cfg = read(root/'packet/config.json'); manifest = read(root/'packet/manifest_A.json'); saved = read(SAVED)
    raw = load_cells(root, cfg, manifest)
    th = cfg['original_thresholds']
    ent, rmap, fmap, checks, gt_meta = {}, {}, {}, [], {}
    for cell in cfg['cells']:
        h = cell.split('_')[0]
        evs = {n: pilot.pilot_evaluator(manifest['panels'][n], raw[cell]) for n in ['source_selection']+PANELS}
        src = evs['source_selection']; src_neg = sorted(-s for s in entry(src).values())
        rmap[cell] = lambda s, a=src_neg, g=src.gt_count: at_or_above(a, s)/g
        ent[cell] = {}; fmap[cell] = {}
        for n, ev in evs.items():
            for mode, t in (('ceiling', None), ('direct', th[h])):
                p = ev.operating_point(t); s = saved['stages']['A']['cells'][cell]['panels'][n][mode]
                checks.append(all(p[k] == s[k] for k in ('tp', 'fp', 'ignored')))
            ent[cell][n] = entry(ev)
            fp_neg = sorted(-r['score'] for r in ev.rows if r['outcome'] == 'FP'); imgs = len(manifest['panels'][n]['images'])
            fmap[cell][n] = lambda s, a=fp_neg, m=imgs: at_or_above(a, s)/m
            gt_meta[n] = ev.gt_count
    assert all(checks), 'saved Stage A counts not reproduced'
    out = dict(researcher='Claude Opus 5.5', analysis_of='GPT Sol Stage A cached outputs', G0='PENDING',
               kind='posthoc finite-panel conditional diagnostic; zero inference', contrasts={}, private_rows={})
    for bundle in ('N', 'K', 'native'):
        A, B = ('o2o_K', 'o2m_N') if bundle == 'native' else ('o2o_'+bundle, 'o2m_'+bundle)
        ta, tb = th['o2o'], th['o2m']
        res = {}
        for n in PANELS:
            ea, eb = ent[A][n], ent[B][n]; J = sorted(set(ea) & set(eb))
            opa = {g for g, s in ea.items() if s >= ta}; opb = {g for g, s in eb.items() if s >= tb}
            # exact identity: direct TP gap = ranking part (within J) + availability part (outside other ceiling)
            rank_part = len((opa - opb) & set(J)) - len((opb - opa) & set(J))
            avail_part = len(opa - set(eb)) - len(opb - set(ea))
            assert rank_part + avail_part == len(opa) - len(opb)
            ra = [rmap[A](ea[g]) for g in J]; rb = [rmap[B](eb[g]) for g in J]
            fa = [fmap[A][n](ea[g]) for g in J]; fb = [fmap[B][n](eb[g]) for g in J]
            dr = [y-x for x, y in zip(ra, rb)]; df = [y-x for x, y in zip(fa, fb)]
            res[n] = dict(gt=gt_meta[n], jointly_ceiling_covered=len(J), only_first_ceiling=len(set(ea)-set(eb)),
                only_second_ceiling=len(set(eb)-set(ea)), direct_tp_first=len(opa), direct_tp_second=len(opb),
                direct_tp_gap=len(opa)-len(opb), gap_ranking_within_joint=rank_part, gap_availability=avail_part,
                joint_first_only_operating=len((opa-opb)&set(J)), joint_second_only_operating=len((opb-opa)&set(J)),
                source_rank_first_earlier=sum(d > 0 for d in dr), source_rank_second_earlier=sum(d < 0 for d in dr),
                source_rank_tied=sum(d == 0 for d in dr),
                median_source_rank_first=statistics.median(ra) if J else None,
                median_source_rank_second=statistics.median(rb) if J else None,
                median_paired_source_rank_diff=statistics.median(dr) if J else None,
                fppi_cost_first_lower=sum(d > 0 for d in df), fppi_cost_second_lower=sum(d < 0 for d in df),
                fppi_cost_tied=sum(d == 0 for d in df),
                median_fppi_cost_first=statistics.median(fa) if J else None,
                median_fppi_cost_second=statistics.median(fb) if J else None)
            out['private_rows'][f'{bundle}:{n}'] = [dict(annotation_id=g, r_first=x, r_second=y, f_first=u, f_second=v)
                                                     for g, x, y, u, v in zip(J, ra, rb, fa, fb)]
        out['contrasts'][bundle] = dict(first=A, second=B, original_thresholds=dict(first=ta, second=tb),
            source_rank_at_original_threshold=dict(first=rmap[A](ta), second=rmap[B](tb)), panels=res)
    PRIV.mkdir(parents=True, exist_ok=True)
    write(PRIV/'per_gt_rows.json', out.pop('private_rows'))
    out['controls'] = dict(saved_stageA_tp_fp_ignored_reproduced=f'{sum(checks)}/{len(checks)}',
        gap_identity='direct TP gap = ranking_within_joint + availability, asserted per panel')
    out['provenance'] = dict(private_root=str(root), manifest_A_sha256=sha(root/'packet/manifest_A.json'),
        config_sha256=sha(root/'packet/config.json'), evidence_final_sha256=sha(root/'evidence_final.tar.gz'),
        saved_aggregate_sha256=sha(SAVED), evaluator_sha256=sha(REPO/'src/threshold_transfer/metrics.py'),
        script_sha256=sha(__file__), private_rows_sha256=sha(PRIV/'per_gt_rows.json'),
        cpu_seconds=round(time.process_time()-t0, 2))
    write(OUT/'2026-11-13_opus_cached_mechanism.json', out)
    figure(root)
    for b in ('N', 'K', 'native'):
        p = out['contrasts'][b]['panels']
        print(b, {n: (p[n]['direct_tp_gap'], p[n]['gap_ranking_within_joint'], p[n]['gap_availability'],
                      p[n]['jointly_ceiling_covered'], p[n]['source_rank_first_earlier'], p[n]['source_rank_second_earlier'],
                      p[n]['fppi_cost_first_lower'], p[n]['fppi_cost_second_lower']) for n in PANELS[:5]})
    print(out['controls'], out['provenance']['cpu_seconds'])


def figure(root):
    sys.path.insert(0, str(Path(root)/'plotdeps'))
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    data = read(OUT/'2026-11-13_opus_cached_mechanism.json'); rows = read(PRIV/'per_gt_rows.json')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.fonttype': 'none', 'figure.facecolor': 'white'})
    blue, orange, ink, muted = '#2a78d6', '#eb6834', '#222222', '#8a8a85'
    c = data['contrasts']['N']; r0 = c['source_rank_at_original_threshold']
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.7), gridspec_kw=dict(width_ratios=[1, 1, 1.25]))
    for ax, n, title in ((axes[0], 'night', 'Night'), (axes[1], 'coco_reference', 'COCO reference')):
        R = rows['N:'+n]; x = [q['r_first'] for q in R]; y = [q['r_second'] for q in R]
        ax.plot([0, 1], [0, 1], color=muted, lw=1, ls='--')
        ax.axvline(r0['first'], color=blue, lw=1, alpha=.6); ax.axhline(r0['second'], color=orange, lw=1, alpha=.6)
        ax.scatter(x, y, s=16, color=ink, alpha=.55, linewidths=0)
        p = c['panels'][n]
        ax.set_title(f"{title}, common N: {p['jointly_ceiling_covered']} jointly covered GT", fontsize=9, loc='left')
        ax.text(.03, .97, f"O2O earlier: {p['source_rank_first_earlier']}\nO2M earlier: {p['source_rank_second_earlier']}",
                transform=ax.transAxes, va='top', fontsize=8, color=ink)
        ax.set_xlim(0, 1.0); ax.set_ylim(0, 1.0); ax.set_aspect('equal')
        ax.set_xlabel('O2O entry rank (source recall at GT score)'); ax.set_ylabel('O2M entry rank (source recall)')
    ax = axes[2]; names = ['coco_reference', 'fog', 'night', 'rain', 'snow', 'night_normal']; labels = ['COCO\nref', 'Fog', 'Night', 'Rain', 'Snow', 'Night\nnormal']
    import numpy as np
    xs = np.arange(len(names)); w = .38
    for k, (b, col, lab) in enumerate((('N', blue, 'common N'), ('K', orange, 'common K'))):
        P = data['contrasts'][b]['panels']
        rk = [P[n]['gap_ranking_within_joint'] for n in names]; av = [P[n]['gap_availability'] for n in names]
        ax.bar(xs+(k-.5)*w, rk, w*.92, color=col, label=f'{lab}: ranking within jointly covered GT')
        ax.bar(xs+(k-.5)*w, av, w*.92, bottom=[max(0, v) if a >= 0 else min(0, v) for v, a in zip(rk, av)],
               color=col, alpha=.35, hatch='///', edgecolor='white', label=f'{lab}: one-ceiling availability')
    ax.axhline(0, color=muted, lw=1); ax.set_xticks(xs, labels)
    ax.set_ylabel('O2O − O2M TP at original thresholds'); ax.set_title('Exact decomposition of direct head TP gap', fontsize=9, loc='left')
    ax.legend(fontsize=7, frameon=False, loc='upper center', bbox_to_anchor=(.5, -.2), ncol=2)
    fig.text(.01, -.12, 'Claude Opus 5.5 analysis of GPT Sol cached outputs. Finite panel; conditional on GT-level greedy matching and joint ceiling coverage. '
             'Vertical/horizontal lines: original thresholds on each head\'s source-recall scale.', fontsize=7, color=muted)
    fig.tight_layout()
    for ext in ('png', 'svg'): fig.savefig(OUT/f'2026-11-13_opus_cached_mechanism.{ext}', dpi=170, bbox_inches='tight')


if __name__ == '__main__':
    main(sys.argv[1])
