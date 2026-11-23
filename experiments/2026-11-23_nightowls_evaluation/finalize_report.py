"""GPT Sol: insert measured uncertainty and validation text in the report."""
import gzip
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/research/2026-11-23_nightowls_evaluation'
REPORT=OUT.with_suffix('.md')


def load(name):
    p=OUT/f'{name}.json'
    return json.loads(p.read_bytes() if p.exists() else gzip.decompress(p.with_suffix('.json.gz').read_bytes()))


def main():
    u=load('uncertainty');r=load('aggregate');v=load('validation');receipt=load('receipt')
    assert r['status']=='COMPLETE' and not r['pending'] and v['status']=='PASS'
    panel='reasonable/unused_nonpedestrian';policy='h50_r0.8';arms=('A_640','B_1280','C_640')
    lines=['All intervals below are descriptive 2.5/97.5 percentiles from **1,000 paired',
           'draws, seed 20261117**, with independent BDD source reselection and clear-test',
           'resampling. All primary source draws were feasible; each displayed recall',
           'interval has 1,000 defined replicates. Source-infeasible policies elsewhere',
           'retain their counts and undefined transfer intervals.',
           '', '| Target resampling mode | A recall interval | B recall interval | C recall interval |',
           '|---|---:|---:|---:|']
    modes=[('cluster_conditional_unkeyed','Five-key, fixed unkeyed (primary)'),
           ('known_only_cluster','Known-key-only'),('dominant_out_conditional_unkeyed','R3-out, fixed unkeyed'),
           ('iid_image_sensitivity','IID images (sensitivity)')]
    for mode,label in modes:
        vals=[]
        for arm in arms:
            ci=u['arms'][arm]['panels'][panel][mode]['policies'][policy]['metrics']['recall']
            assert ci['defined']==1000
            vals.append('–'.join(f'{100*x:.2f}' for x in ci['percentile_95'])+'%')
            assert u['arms'][arm]['selection'][policy]['feasible_replicates']==1000
        lines.append('| '+label+' | '+' | '.join(vals)+' |')
    contrast=[]
    for label,pp in u['contrasts'].items():
        left,right=label.split(' minus ')
        ci=pp[panel]['cluster_conditional_unkeyed'][policy]['recall']['percentile_95']
        point=r['arms'][left]['panels'][panel]['pooled'][policy]['operating']['recall']-r['arms'][right]['panels'][panel]['pooled'][policy]['operating']['recall']
        contrast.append(f'{left[0]}−{right[0]} {100*point:+.2f} [{100*ci[0]:+.2f}, {100*ci[1]:+.2f}]')
    freq=[u['arms'][arm]['panels'][panel]['cluster_conditional_unkeyed']['oracles']['0.8']['threshold']['defined'] for arm in arms]
    lines+=['','Paired primary recall contrasts (point [interval], percentage points):',
            '; '.join(contrast)+'. These condition on the trained checkpoints.',
            '',f'Target .80 oracle feasibility was **{freq[0]}/{freq[1]}/{freq[2]} of 1,000**',
            'recording draws for A/B/C; oracle intervals use only feasible draws and',
            'report infeasible/zero-GT counts. This does not change observed feasibility.',
            f'The five-key draw space has only **126 distinct multisets**; {u["distinct_cluster_multisets_observed"]} occurred,',
            f'and R3 was omitted in **{u["dominant_key_omitted_replicates"]}/1,000** draws (theoretical probability .32768).',
            'Lumpy recording support and unverified trip independence limit interpretation.',
            'Pooled and R3-out intervals condition on fixed unkeyed frames; IID-image',
            'intervals may be anti-conservative under video correlation. Nominal coverage',
            'has not been established.']
    validation=(f'GPT Sol retained **24 real-data fast/reference equivalence checks**, using a\n'
        f'fixed 1/17 image sample plus every zero-area-candidate image in each arm/setup/\n'
        f'profile. Exact per-GT scores, TP/FP/ignored counts, thresholds and oracles agree.\n'
        f'The unchanged BDD matcher reproduced every stored source threshold and the\n'
        f'decisive ≥50 clear/night TP reference points. One final bounded pass checked\n'
        f'**{v["aggregate_rows_checked"]:,} aggregate rows**, {v["weighted_reference_points_checked"]} weighted operating points,\n'
        f'{v["weighted_height_intervals_checked"]} height-interval comparisons, image pairing, source infeasibility,\n'
        f'candidate accounting, miss identities, cap counts and public JSON privacy.\n'
        f'These are implementation checks on actual saved predictions, not independent\n'
        f'review or synthetic detector evidence. All required analyses completed.\n'
        f'Point scoring took **{receipt["elapsed_s"]/60:.2f} CPU wall-minutes**; bootstrap took\n'
        f'**{receipt["bootstrap_elapsed_s"]/60:.2f} wall-minutes**. Scoring used Python 3.12.14 /\n'
        f'NumPy {receipt["numpy"]}; the earlier BDD reference used NumPy 2.2.6. Exact point\n'
        f'reproduction was checked; historical bootstrap intervals were not claimed\n'
        f'reproduced with the external joint seed.')
    text=REPORT.read_text(encoding='utf-8')
    assert 'UNCERTAINTY_PENDING' in text and 'VALIDATION_PENDING' in text
    text=text.replace('UNCERTAINTY_PENDING','\n'.join(lines)).replace('VALIDATION_PENDING',validation)
    REPORT.write_text(text,encoding='utf-8')
    print('Inserted measured uncertainty and validation; no pending markers.')


if __name__=='__main__':main()
