"""GPT Sol scoped CPU review: saved candidates only; no inference or downloads.

Usage: python -B SCRIPT PRIVATE_ROOT ORIGINAL_PRIVATE_ROWS
Reproduction artifacts remain in ignored outputs/opus_direction_review_20261113/.
"""
import bisect
import hashlib
import importlib.util
import json
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    'opus', REPO/'experiments/2026-11-13_opus_cached_mechanism.py')
opus = importlib.util.module_from_spec(spec)
spec.loader.exec_module(opus)


def main(root, original_rows):
    root = Path(root)
    saved = opus.read(REPO/'docs/claude/2026-11-13_opus_cached_mechanism.json')
    original_rows = Path(original_rows)
    assert opus.sha(original_rows) == saved['provenance']['private_rows_sha256']
    work = REPO/'outputs/opus_direction_review_20261113'
    opus.OUT, opus.PRIV = work/'reproduced', work/'private'
    opus.main(root)
    actual = opus.read(opus.OUT/'2026-11-13_opus_cached_mechanism.json')
    for key in saved:
        if key != 'provenance':
            assert actual[key] == saved[key], key
    for key, value in saved['provenance'].items():
        if key not in ('cpu_seconds', 'script_sha256'):
            assert actual['provenance'][key] == value, key
    # Git autocrlf changed script bytes; establish the exact LF identity explicitly.
    script_bytes = Path(opus.__file__).read_bytes()
    assert hashlib.sha256(script_bytes.replace(b'\r\n', b'\n')).hexdigest() == saved['provenance']['script_sha256']
    assert opus.read(opus.PRIV/'per_gt_rows.json') == opus.read(original_rows)
    from PIL import Image
    figure_name = '2026-11-13_opus_cached_mechanism'
    with Image.open(opus.OUT/(figure_name+'.png')) as a, Image.open(REPO/'docs/claude'/(figure_name+'.png')) as b:
        assert a.size == b.size and a.tobytes() == b.tobytes()
    def svg_texts(path):
        return [''.join(e.itertext()) for e in ET.parse(path).iter() if e.tag.endswith('}text')]
    assert svg_texts(opus.OUT/(figure_name+'.svg')) == svg_texts(REPO/'docs/claude'/(figure_name+'.svg'))

    cfg = opus.read(root/'packet/config.json')
    manifest = opus.read(root/'packet/manifest_A.json')
    raw = opus.load_cells(root, cfg, manifest)
    entries, rank, source, prefix_checks = {}, {}, {}, 0
    for head in ('o2o', 'o2m'):
        cell = head+'_N'
        source_ev = opus.pilot.pilot_evaluator(manifest['panels']['source_selection'], raw[cell])
        source_scores = sorted(-row['score'] for row in source_ev.rows if row['outcome'] == 'TP')
        rank[head] = lambda score, a=source_scores, n=source_ev.gt_count: bisect.bisect_right(a, -score)/n
        threshold = cfg['original_thresholds'][head]
        point = source_ev.operating_point(threshold)
        selection = source_ev.select_threshold(.9)
        source[head] = dict(original_tp=point['tp'], gt=source_ev.gt_count,
                            original_recall=point['recall']['value'],
                            reselected_threshold=selection['threshold'],
                            reselected_tp=selection['operating_point']['tp'])
        for name in ('source_selection', 'night'):
            panel = manifest['panels'][name]
            ev = opus.pilot.pilot_evaluator(panel, raw[cell])
            # Independently derive TP entry scores and rematch retained candidates.
            ent = {r['annotation_id']: r['score'] for r in ev.rows if r['outcome'] == 'TP'}
            assert len(ent) == sum(r['outcome'] == 'TP' for r in ev.rows)
            if name == 'night':
                entries[head] = ent
            for boundary in (threshold, math.nextafter(threshold, math.inf), selection['threshold']):
                filtered = dict(raw[cell])
                for key in ('predictions', 'degenerate_predictions'):
                    filtered[key] = [p for p in raw[cell][key] if p['score'] >= boundary]
                rematched = opus.pilot.pilot_evaluator(panel, filtered)
                expected = {g for g, s in ent.items() if s >= boundary}
                observed = {r['annotation_id'] for r in rematched.rows if r['outcome'] == 'TP'}
                assert expected == observed
                prefix_checks += 1
    a, b = entries['o2o'], entries['o2m']
    joint = set(a) & set(b)
    ta, tb = (cfg['original_thresholds'][h] for h in ('o2o', 'o2m'))
    admit_a, admit_b = {g for g, s in a.items() if s >= ta}, {g for g, s in b.items() if s >= tb}
    gains = (admit_a-admit_b) & joint
    rank_gains = {g for g in joint if rank['o2o'](a[g]) <= rank['o2o'](ta)
                  and rank['o2m'](b[g]) > rank['o2m'](tb)}
    assert (len(joint), len(gains), len(rank_gains), len(rank_gains & gains)) == (70, 10, 8, 8)
    n = saved['contrasts']['N']['panels']
    assert [n['night'][k] for k in ('gt', 'direct_tp_gap', 'gap_ranking_within_joint',
                                   'gap_availability', 'source_rank_first_earlier',
                                   'source_rank_second_earlier')] == [105, 11, 10, 1, 47, 20]
    assert [n['night_normal'][k] for k in ('source_rank_first_earlier', 'source_rank_second_earlier')] == [121, 27]
    assert [n['rain'][k] for k in ('fppi_cost_first_lower', 'fppi_cost_second_lower')] == [29, 31]
    # Saved exchange copies agree; this is not a live-transport authentication.
    exchange = opus.read(REPO/'docs/claude/2026-11-13_opus_direction.exchange.json')
    access = opus.read(REPO/'docs/gpt/2026-11-13_independent_data_access.json')
    assert [m['text'] for m in exchange['messages']] == [m['text'] for m in access['peer_exchange']]
    assert {h['content_length_bytes'] for h in access['header_observations']} == {10696948, 57481286834}
    assert all(h['method'] == 'HEAD' and h['body_bytes'] == 0 for h in access['header_observations'])
    result = dict(attribution='Independent GPT Sol review', aggregate_and_private_rows_match=True,
                  figure_png_pixels_match=True, figure_svg_texts_match=True,
                  script_LF_sha256=saved['provenance']['script_sha256'],
                  script_checkout_sha256=actual['provenance']['script_sha256'],
                  prefix_rematches=prefix_checks, common_N_source=source,
                  common_N_night_exact_joint_gains=len(gains),
                  common_N_night_rank_only_gains=len(rank_gains),
                  common_N_night_extra_rank_only_gains=len(rank_gains-gains),
                  saved_exchange_texts_match=True, scope='CPU; no inference or download')
    opus.write(work/'check.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main(*sys.argv[1:])
