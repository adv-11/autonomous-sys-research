"""GPT Sol: concise aggregate report from completed measured evidence only."""
import json
from local import HERE, OUT, load, sha


def main():
    result=load(OUT/'results.json'); plan=load(HERE/'plan.json')
    rows=['# Local RT-DETRv2 measured results','',
          'GPT Sol executed this locally amended study; Claude Opus medium contributed',
          'scientific design and interpretation limits. Independent completed-result',
          'review remains separate. G0 remains pending. No merge approval is implied.','',
          f"Declared baseline: {plan['baseline_epochs']} epochs; both continuations: five",
          f"epochs / 8,000 images; physical batch {plan['batch']}; training seed zero.",
          'Final declared EMA only. All selection/validation images remain outside training.','',
          '| Arm | Source threshold (FPPI ≤ 1) | Night recall | Night FPPI | Clear recall | Clear FPPI | Night ceiling |',
          '|---|---:|---:|---:|---:|---:|---:|']
    for arm,ar in result['arms'].items():
        p=ar['operating_points']['source_fppi_1']
        if p['status']=='FEASIBLE':
            n,c=p['conditions']['night'],p['conditions']['clear_day']
            rows.append(f"| {arm} | {p['threshold']:.6f} | {n['recall']:.4f} | {n['fppi']:.4f} | {c['recall']:.4f} | {c['fppi']:.4f} | {ar['strata']['night']['ceiling']['recall']:.4f} |")
        else: rows.append(f'| {arm} | INFEASIBLE | — | — | — | — | — |')
    rows+=['','## Paired changes at the source-selected FPPI policy','',
           'Intervals use 1,000 paired image bootstrap replicates with source threshold',
           'reselection. They condition on the trained seed and do not cover route or',
           'training-seed variation. Recall and actual FPPI changes are reported together.','',
           '| Contrast | Condition | Recall change [95% interval] | FPPI change [95% interval] |',
           '|---|---|---:|---:|']
    for contrast,policies in result['paired'].items():
        for group,metrics in policies['source_fppi_1'].items():
            cells=[]
            for metric in ('recall','fppi'):
                p=metrics[metric]; ci=p['ci']
                cells.append(f"{p['difference']:+.4f} [{ci[0]:+.4f}, {ci[1]:+.4f}]" if ci else 'UNDEFINED')
            rows.append(f'| {contrast} | {group} | '+ ' | '.join(cells)+' |')
    rows+=['','## Source-recall sensitivities','',
           '| Arm | Source target | Status | Night recall | Night FPPI | Clear recall | Clear FPPI |',
           '|---|---:|---|---:|---:|---:|---:|']
    for arm,ar in result['arms'].items():
        for target in (.8,.9,.95):
            p=ar['operating_points'][f'recall_{target}']
            if p['status']=='FEASIBLE':
                n,c=p['conditions']['night'],p['conditions']['clear_day']
                rows.append(f"| {arm} | {target} | FEASIBLE | {n['recall']:.4f} | {n['fppi']:.4f} | {c['recall']:.4f} | {c['fppi']:.4f} |")
            else: rows.append(f'| {arm} | {target} | INFEASIBLE | — | — | — | — |')
    rows+=['','## Execution evidence','',
           '| Arm | Epochs | Seconds | Attempted updates | Successful updates | AMP skips |',
           '|---|---:|---:|---:|---:|---:|']
    for arm in result['arms']:
        s=load(OUT/f'{arm}_summary.json')
        rows.append(f"| {arm} | {s['epochs']} | {s['seconds']:.1f} | {s['attempted_updates']} | {s['successful_updates']} | {s['attempted_updates']-s['successful_updates']} |")
    rows+=['',f"Aggregate results SHA256: `{sha(OUT/'results.json')}`.",
       'Private evidence retains raw query logits/boxes/native candidates, checkpoint',
       'hashes, optimizer/scaler/EMA state, full curves, runtime records and failures.','',
       'Ordinary adaptation is not a novel method. The mixed arm adds 4,000 unseen',
       'night images while day training images are reused; this combines night content',
       'with image novelty. A recall gain with increased FPPI or lower clear recall is',
       'a tradeoff. An interval crossing zero leaves a difference unestablished, not',
       'equivalent. Candidate-ceiling improvement is useful but not required for a',
       'better ranking/tradeoff. Test curves are descriptive, not replacement policies.',
       'The local environment differs from Colab; numerical equivalence is not claimed.',
       'Exact YOLO1280 seed repeats remain deferred because their original memory',
       'requirement exceeds this GPU. No external-dataset inference was added.','']
    path=HERE.parents[1]/'docs/research/2026-11-26_local_rtdetr_results.md'
    path.write_text('\n'.join(rows),encoding='utf-8')


if __name__=='__main__': main()
