"""GPT Sol: bounded CPU integration checks; no torch, inference or public writes.

Run with --private-root pointing to the retained information_control_20261111.
Optional --output stores only aggregate checks in an ignored evidence directory.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess

REPO = Path(__file__).resolve().parents[2]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, REPO / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-root', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    control = load('information_control', 'experiments/2026-11-11_information_control.py')
    pilot = control.pilot
    root = args.private_root
    public = pilot.read(REPO / 'docs/gpt/2026-11-11_sol_information_aggregate.json')
    code = pilot.read(root / 'code_record.json')
    assert pilot.read(root / 'results/delivery_verified.json') == code == public['code_record']
    for relative, key in [('sent_script.py', 'script_sha256'), ('sent_baseline.py', 'baseline_script_sha256'),
                          ('packet/config.json', 'config_sha256'), ('packet/manifest.json', 'manifest_sha256')]:
        assert pilot.sha(root / relative) == code[key]
    for path, key in [(Path(control.__file__), 'script_sha256'), (Path(pilot.__file__), 'baseline_script_sha256'),
                      (REPO / 'src/threshold_transfer/metrics.py', 'evaluator_sha256'),
                      (REPO / 'src/threshold_transfer/schema.py', 'schema_sha256')]:
        data = path.read_bytes()
        assert code[key] in {hashlib.sha256(data).hexdigest(),
                             hashlib.sha256(data.replace(b'\r\n', b'\n')).hexdigest()}
    original = pilot.read(root / 'packet/manifest.json')
    mapped = control.map_gt(original)
    # Independently check every continuous edge transform, not only a saved example.
    for name, panel in original['panels'].items():
        images = {i['image_id']: i for i in panel['images']}
        for before, after in zip(panel['annotations'], mapped['panels'][name]['annotations']):
            image = images[before['image_id']]
            width, height = image['width'], image['height']
            scale = 1280 / max(width, height)
            w, h = math.floor(scale * width + .5), math.floor(scale * height + .5)
            x, y, bw, bh = before['bbox']
            expected = [(1280-w)//2 + x*w/width, (1280-h)//2 + y*h/height,
                        (x+bw)*w/width - x*w/width, (y+bh)*h/height - y*h/height]
            assert all(math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-10)
                       for a, b in zip(expected, after['bbox']))
    panels = {n: mapped['panels'][n] for n in ('source_selection', 'coco_reference')}
    for name, members in [('pooled_adverse', ['fog', 'night', 'rain', 'snow']),
                          ('pooled_normal', [c+'_normal' for c in ('fog', 'night', 'rain', 'snow')]),
                          ('pooled_paired', [c+'_paired' for c in ('fog', 'night', 'rain', 'snow')])]:
        panels[name] = {**mapped['panels'][members[0]], **{
            k: [r for n in members for r in mapped['panels'][n][k]] for k in ('images', 'annotations')}}
    expected_ids = {i['image_id'] for p in mapped['panels'].values() for i in p['images']}
    summary, matched = {}, {}
    for arm in control.ARMS:
        files = sorted((root / 'results').glob(arm+'_native_batch_*.json'))
        rows = [r for file in files for r in pilot.read(file)]
        assert len(files) == 88 and len(rows) == len({r['image_id'] for r in rows}) == 700
        assert {r['image_id'] for r in rows} == expected_ids
        raw = dict(predictions=[], degenerate_predictions=[],
                   provenance=dict(evaluated_image_ids=[r['image_id'] for r in rows]))
        for row in rows:
            assert len(row['xyxy']) == len(row['scores']) == len(row['classes']) <= 3000
            for index, (box, score, cls) in enumerate(zip(row['xyxy'], row['scores'], row['classes'])):
                assert cls == 0 and all(math.isfinite(v) for v in box+[score]) and 0 <= score <= 1
                assert box[2] >= box[0] and box[3] >= box[1]
                size = 640 if arm == 'L640' else 1280
                box = [min(size, max(0., v)) * (2 if arm == 'L640' else 1) for v in box]
                x1, y1, x2, y2 = box
                pred = dict(candidate_id=row['image_id']+f':{index:04d}', image_id=row['image_id'],
                            category='human', bbox=[x1, y1, x2-x1, y2-y1], score=score)
                if x1 == x2 or y1 == y2:
                    raw['degenerate_predictions'].append(dict(**pred, native_xyxy=box))
                else:
                    raw['predictions'].append(pred)
        stored = pilot.read(root / 'results' / (arm+'.json'))
        for key in ('predictions', 'degenerate_predictions', 'provenance'):
            assert raw[key] == stored[key]
        evaluators = {n: pilot.pilot_evaluator(p, raw) for n, p in panels.items()}
        selection = evaluators['source_selection'].select_threshold(.9)
        assert selection['status'] == public['source'][arm]['status'] == 'FEASIBLE'
        assert selection['threshold'] == public['source'][arm]['threshold']
        assert evaluators['source_selection'].operating_point(math.nextafter(selection['threshold'], 1))['tp']/579 < .9
        for name, ev in evaluators.items():
            for mode, threshold in [('ceiling', None), ('operating', selection['threshold'])]:
                point = ev.operating_point(threshold)
                compact = {k: point[k] for k in public['panels'][name][arm][mode] if k != 'zero_area_fp'}
                compact['zero_area_fp'] = sum(r.get('native_zero_area', False) for r in point['matches'])
                assert compact == public['panels'][name][arm][mode], (name, arm, mode)
                if name == 'pooled_adverse' and mode == 'ceiling':
                    matched[arm] = {r['annotation_id'] for r in point['matches'] if r['outcome'] == 'TP'}
        summary[arm] = dict(images=len(rows), batches=len(files), threshold=selection['threshold'],
                            adverse_ceiling_tp=len(matched[arm]))
    for a, b, label in [('H1280', 'L640', 'H-L'), ('H1280', 'U1280', 'H-U'), ('U1280', 'L640', 'U-L')]:
        expected = public['panels']['pooled_adverse']['contrasts'][label]
        assert (len(matched[a]-matched[b]), len(matched[b]-matched[a]), len(matched[a])-len(matched[b])) == (
            expected['gained'], expected['lost'], expected['net_tp'])
    assert [summary[a]['adverse_ceiling_tp'] for a in control.ARMS] == [172, 127, 160]
    assert public['primary']['fraction_recovered'] == 33/45 and public['primary']['supports']
    complete = load('complete_audit_check', 'experiments/2026-11-11_recall_audit.py')
    partial = load('partial_audit_check', 'experiments/2026-11-11_partial_audit.py')
    result = dict(reviewer='GPT Sol', head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  information=summary, matched_points=30, net_ratio=33/45,
                  synthetic_complete=complete.tiny_check(), synthetic_partial=partial.boundary_checks())
    if args.output:
        pilot.write(args.output, result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
