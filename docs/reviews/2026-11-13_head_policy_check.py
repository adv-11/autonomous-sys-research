"""GPT Sol independent saved-output review; CPU only, no inference or mutation of inputs.

Usage: PYTHONPATH=src python -B SCRIPT PRIVATE_ROOT --output IGNORED_JSON
Rebuilds candidates independently, then reuses the established matching evaluator.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('pilot', REPO/'experiments/2026-11-10_transfer_pilot.py')
pilot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pilot)
read = pilot.read


def main(root, output):
    manifest = read(root/'packet/manifest_A.json')
    public = read(REPO/'docs/gpt/2026-11-13_sol_head_policy_mechanism.json')
    historical = read(REPO/'docs/gpt/2026-11-11_sol_dual_head_transfer.json')
    cfg = read(root/'packet/config.json')
    assert pilot.sha(root/'packet/manifest_A.json') == cfg['manifest_A_sha256']
    assert cfg == public['config'] == read(REPO/'configs/research/head_policy_mechanism_20261113.json')
    universe = {i['image_id'] for p in manifest['panels'].values() for i in p['images']}
    result = dict(attribution='Independent GPT Sol CPU review', inference_calls=0,
                  native_array_replays={}, coverage={}, cells={}, historical={}, contrasts={})
    sets = {}
    for head, native_policy in [('o2o', 'K'), ('o2m', 'N')]:
        batches = [read(p) for p in sorted((root/'results').glob(head+'_batch_*.json'))]
        correction = read(root/'results/correction_last_native_batch'/f'{head}_batch_0000.json')
        # Compare actual saved arrays, independently of the operator's pass flags.
        n = 0
        for batch in batches + [correction]:
            assert batch['validated']
            assert len(batch['image_ids']) == len(batch['native'])
            assert batch['native'] == batch['cells'][native_policy]
            assert batch['stage']['format'] == ('xyxy' if head == 'o2o' else 'xywh')
            assert batch['stage']['branch_calls'][head] > 0
            assert batch['stage']['branch_calls']['o2m' if head == 'o2o' else 'o2o'] == 0
            n += len(batch['image_ids'])
        result['native_array_replays'][head] = n
        old_final = read(root.with_name('dual_head_20261111')/'results'/f'yolo26s_{head}_maximal_native_batch_0928.json')
        assert correction['image_ids'] == [r['image_id'] for r in old_final]
        for rows, old in zip(correction['native'], old_final):
            assert [r[:4] for r in rows] == old['xyxy']
            assert [r[4] for r in rows] == old['scores']
            assert [r[5] for r in rows] == old['classes']
        corrections = dict(zip(correction['image_ids'], range(5)))
        for policy in ('K', 'N'):
            cell = head+'_'+policy
            raw = dict(schema_version=pilot.PY_SCHEMA, predictions=[], degenerate_predictions=[],
                       provenance=dict(evaluated_image_ids=[]))
            for batch in batches:
                for iid, rows in zip(batch['image_ids'], batch['cells'][policy]):
                    if iid in corrections:
                        rows = correction['cells'][policy][corrections[iid]]
                    raw['provenance']['evaluated_image_ids'].append(iid)
                    for j, (x1,y1,x2,y2,score,cls) in enumerate(rows):
                        assert cls == 0 and x2 >= x1 and y2 >= y1
                        pred = dict(image_id=iid, candidate_id=f'{iid}:{j:04d}', category='human',
                                    bbox=[x1,y1,x2-x1,y2-y1], score=score)
                        if x1 == x2 or y1 == y2:
                            raw['degenerate_predictions'].append(dict(pred, native_xyxy=[x1,y1,x2,y2]))
                        else:
                            raw['predictions'].append(pred)
            coverage = raw['provenance']['evaluated_image_ids']
            assert len(coverage) == len(set(coverage)) == len(universe) == 933
            assert set(coverage) == universe
            result['coverage'][cell] = len(coverage)
            evs = {name:pilot.pilot_evaluator(panel, raw) for name,panel in manifest['panels'].items()}
            selection = evs['source_selection'].select_threshold(.9)
            threshold = selection['threshold']
            assert selection['status'] == 'FEASIBLE'
            assert threshold == public['stages']['A']['cells'][cell]['source_selection']['threshold']
            # The next stricter floating boundary must fail; include the whole tied group.
            assert evs['source_selection'].operating_point(math.nextafter(threshold, math.inf))['tp']/selection['operating_point']['eligible_gt'] < .9
            points, sets[cell] = {}, {}
            for name, ev in evs.items():
                points[name], sets[cell][name] = {}, {}
                for mode, t in [('direct',cfg['original_thresholds'][head]),('reselected',threshold),('ceiling',None)]:
                    p = ev.operating_point(t)
                    compact = {k:p[k] for k in ['tp','fp','ignored','fn','eligible_gt','image_count','retained_candidates','recall','fppi','precision','threshold']}
                    published = public['stages']['A']['cells'][cell]['panels'][name][mode]
                    assert all(v == published[k] for k,v in compact.items()), (cell,name,mode)
                    points[name][mode] = compact
                    sets[cell][name][mode] = {r['annotation_id'] for r in p['matches'] if r['outcome']=='TP'}
                    if policy == native_policy and mode != 'reselected':
                        old = historical['heads']['yolo26s_'+head]['panels'][name]['operating' if mode=='direct' else 'ceiling']
                        assert all(p[k] == old[k] for k in ('tp','fp','ignored'))
            result['cells'][cell] = dict(threshold=threshold, source_tp=selection['operating_point']['tp'], panels=points)
            if policy == native_policy:
                result['historical'][head] = dict(final_five_exact=True, all_14_panel_TP_FP_ignored_exact=True)
    for label, a, b in [('native','o2o_K','o2m_N'),('head_K','o2o_K','o2m_K'),('head_N','o2o_N','o2m_N')]:
        result['contrasts'][label] = {}
        for mode in ('direct','reselected','ceiling'):
            x,y = sets[a]['night'][mode],sets[b]['night'][mode]
            c = dict(shared=len(x&y),only_first=len(x-y),only_second=len(y-x),
                     first_only_in_second_ceiling=len((x-y)&sets[b]['night']['ceiling']))
            published = public['stages']['A']['coverage'][label]['night'][mode]
            assert all(v == published[k] for k,v in c.items())
            result['contrasts'][label][mode] = c
    for head,native,swap in [('o2o','K','N'),('o2m','N','K')]:
        for panel in manifest['panels']:
            a = result['cells'][head+'_'+native]['panels'][panel]['direct']
            b = result['cells'][head+'_'+swap]['panels'][panel]
            expected = public['stages']['A']['additive_count_checks'][head][panel]
            for key in ('tp','fp'):
                d = b['direct'][key]-a[key]
                movement = b['reselected'][key]-b['direct'][key]
                assert (d,movement,d+movement) == tuple(expected[k][key] for k in ('direct_swap','boundary_movement','total'))
    forbidden = {'image_id','annotation_id','candidate_id','bbox','native_xyxy','image_ids','evaluated_image_ids','matches'}
    def privacy(value):
        if isinstance(value,dict):
            assert not forbidden.intersection(value)
            for v in value.values(): privacy(v)
        elif isinstance(value,list):
            for v in value: privacy(v)
    for file in ['2026-11-13_sol_head_policy_mechanism.json','2026-11-13_sol_mechanism_diagnosis.json']:
        privacy(read(REPO/'docs/gpt'/file))
    result['public_key_privacy_check'] = 'PASS; report/figures separately inspected'
    pilot.write(output,result)
    print(json.dumps(dict(coverage=result['coverage'], native_array_replays=result['native_array_replays'],
                         night={c:v['panels']['night'] for c,v in result['cells'].items()},
                         source={c:[v['threshold'],v['source_tp']] for c,v in result['cells'].items()},
                         contrasts=result['contrasts'],historical=result['historical'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    main(args.root,args.output)
