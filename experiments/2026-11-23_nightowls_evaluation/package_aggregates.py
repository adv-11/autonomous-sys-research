"""GPT Sol: compact counts-only exports; retain full JSON as deterministic gzip.

Run after uncertainty, verification and figure generation. Raw JSON also remains
in canonical ignored outputs. No IDs, boxes or native recording keys exported.
"""
import csv
import gzip
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).resolve().parents[2]/'docs/research/2026-11-23_nightowls_evaluation'


def load(name):
    p=OUT/f'{name}.json'
    return json.loads(p.read_bytes() if p.exists() else gzip.decompress(p.with_suffix('.json.gz').read_bytes()))


def export(name,rows):
    with open(OUT/name,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    r=load('aggregate');u=load('uncertainty')
    primary=[]; recording=[]; eligibility=[]; heights=[]
    for arm,ar in r['arms'].items():
        for panel,groups in ar['panels'].items():
            setup,profile=panel.split('/')
            for group,policies in groups.items():
                for policy,p in policies.items():
                    row={'arm':arm,'setup':setup,'profile':profile,'group':group,'source_policy':policy,
                        'target':p['target'],'source_threshold':p['source_threshold'],'source_status':p['status'],
                        'images':p['images'],'eligible_gt':p['eligible_gt'],'ignored_gt':p['ignored_gt'],
                        'tracking_values':p['eligible_tracking_values'],'operational_150_gt':p['operational_150_gt'],
                        'known_keys':p['known_groups'],'unkeyed_images':p['unkeyed_images'],
                        'ceiling_tp':p['ceiling']['tp'],'ceiling_recall':p['ceiling']['recall'],
                        **{k:p['operating'][k] if p['operating'] else None for k in ('tp','fp','recall','fppi','precision')},
                        'ignored_candidates_ceiling':p['ignored_candidates_ceiling'],
                        'ignored_candidates_operating':p['ignored_candidates_operating'],
                        'no_matched_candidate':p['misses']['no_matched_candidate'] if p.get('misses') else None,
                        'removed_by_threshold':p['misses']['removed_by_threshold'] if p.get('misses') else None,
                        'oracle_status':p['oracle']['status'],'oracle_threshold':p['oracle']['threshold'],
                        'oracle_fppi':p['oracle']['operating']['fppi'] if p['oracle']['operating'] else None,
                        'loss_vs_bdd_clear':p['loss_vs_bdd_h50_clear']['held_out_loss']['value'] if p.get('loss_vs_bdd_h50_clear') else None}
                    if setup=='reasonable' and group=='pooled':
                        for mode in ('cluster_conditional_unkeyed','known_only_cluster','dominant_out_conditional_unkeyed','iid_image_sensitivity'):
                            v=u['arms'][arm]['panels'][panel][mode]['policies'][policy]['metrics']['recall']
                            ci=v['percentile_95']
                            row[f'{mode}_recall_low']=ci[0] if ci else None
                            row[f'{mode}_recall_high']=ci[1] if ci else None
                            row[f'{mode}_defined']=v['defined']
                        primary.append(row)
                    if setup=='reasonable' and policy=='h50_r0.8':recording.append(row)
                    if group=='pooled' and policy=='h50_r0.8':
                        eligibility.append(row)
                        for scale,v in p['heights'].items():
                            for binname,counts in v['bins'].items():
                                heights.append({'arm':arm,'setup':setup,'profile':profile,'height_scale':scale,
                                    'height_bin':binname,**counts})
    export('source_policies.csv',primary);export('recordings_primary.csv',recording)
    export('eligibility_primary.csv',eligibility);export('heights_primary.csv',heights)
    contrasts=[]
    for contrast,panels in u['contrasts'].items():
        left,right=contrast.split(' minus ')
        for profile in ('unused_nonpedestrian','person_compatible_ignore'):
            panel='reasonable/'+profile
            for mode,group in [('cluster_conditional_unkeyed','pooled'),('known_only_cluster','known_only'),
                               ('dominant_out_conditional_unkeyed','dominant_out'),('iid_image_sensitivity','pooled')]:
                lc=r['arms'][left]['panels'][panel][group]['h50_r0.8']
                rc=r['arms'][right]['panels'][panel][group]['h50_r0.8']
                row={'contrast':contrast,'setup':'reasonable','profile':profile,'source_policy':'h50_r0.8','mode':mode}
                for k in ('recall','fppi','precision','ceiling','loss'):
                    if k=='ceiling': point=lc['ceiling']['recall']-rc['ceiling']['recall']
                    elif k=='loss': point=lc['loss_vs_bdd_h50_clear']['held_out_loss']['value']-rc['loss_vs_bdd_h50_clear']['held_out_loss']['value']
                    else:point=lc['operating'][k]-rc['operating'][k]
                    ci=panels[panel][mode]['h50_r0.8'][k]
                    row[k]=point;row[k+'_low']=ci['percentile_95'][0] if ci['percentile_95'] else None
                    row[k+'_high']=ci['percentile_95'][1] if ci['percentile_95'] else None
                    row[k+'_defined']=ci['defined']
                contrasts.append(row)
    export('contrasts_primary.csv',contrasts)
    manifest={}
    for name in ('aggregate','uncertainty'):
        raw=(OUT/f'{name}.json').read_bytes() if (OUT/f'{name}.json').exists() else gzip.decompress((OUT/f'{name}.json.gz').read_bytes())
        packed=gzip.compress(raw,mtime=0)
        assert gzip.decompress(packed)==raw
        (OUT/f'{name}.json.gz').write_bytes(packed)
        manifest[f'{name}.json.gz']={'uncompressed_bytes':len(raw),'compressed_bytes':len(packed),
            'uncompressed_sha256':hashlib.sha256(raw).hexdigest(),'sha256':hashlib.sha256(packed).hexdigest(),
            'content':'Full counts-only JSON; no identity/box/native-key data; lossless compression'}
        (OUT/f'{name}.json').unlink(missing_ok=True)
    (OUT/'aggregate_manifest.json').write_text(json.dumps(manifest,indent=1)+'\n',encoding='utf-8')
    print(json.dumps(manifest))


if __name__=='__main__':main()
