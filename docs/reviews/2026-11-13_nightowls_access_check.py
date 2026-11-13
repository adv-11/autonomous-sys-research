"""Read-only Claude Opus check of the stopped NightOwls access-pilot evidence.

Recomputes private-artifact hashes and byte accounting against the public counts
JSON. No network, no writes, no process control. Prints aggregates only.
"""
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path('C:/Users/Advait/autonomous-sys-research')
EVID = ROOT / 'data/nightowls/image_access_pilot/2026-11-13'
REPO = Path(__file__).resolve().parents[2]
counts = json.loads((REPO / 'docs/gpt/2026-11-13_nightowls_image_access_counts.json').read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
files = {'private_request_log': 'logs/requests.jsonl', 'private_worker_checkpoint_at_stop': 'logs/worker_checkpoint_at_stop.json',
         'private_original_controller': 'logs/control.json', 'private_operator_stop': 'logs/operator_stop.json',
         'private_complete_index_tail': 'archive_index/range_0001.bin'}
out = {name: sha(EVID / rel) == counts['artifact_sha256'][name] for name, rel in files.items()}
events = [json.loads(x) for x in (EVID / 'logs/requests.jsonl').read_text().splitlines()]
ck = json.loads((EVID / 'logs/worker_checkpoint_at_stop.json').read_text())
ctl = json.loads((EVID / 'logs/control.json').read_text())
op = json.loads((EVID / 'logs/operator_stop.json').read_text())
heads = [e for e in events if e['event'] == 'headers_before_body']
spans = []
for h in heads:
    a, b, t = map(int, re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', h['headers']['Content-Range']).groups())
    spans.append(b - a + 1)
    assert h['status'] == 206 and t == 57481286834 and int(h['headers']['Content-Length']) == b - a + 1
    assert h['headers']['ETag'] == '"5ce813b8-d6226d4b2"' and h['headers']['Last-Modified'] == 'Fri, 24 May 2019 15:54:32 GMT'
reserved = [e['reserved'] for e in events if e['event'] == 'reserved_before_request']
out.update(
    two_206_identity_ok=len(heads) == 2, spans_equal_reservations=spans == reserved,
    charged=sum(reserved), charged_matches=sum(reserved) == ck['charged_bytes'] == counts['http_body_bytes']['conservative_charged_upper_bound'],
    confirmed=ck['confirmed_bytes'], confirmed_matches=ck['confirmed_bytes'] == counts['http_body_bytes']['durably_confirmed_lower_bound'],
    partial_second_body=ck['confirmed_bytes'] - spans[0], partial_is_whole_64k_chunks=(ck['confirmed_bytes'] - spans[0]) % 65536 == 0,
    body_complete_events=sum(e['event'] == 'body_complete' for e in events), request_failed_events=sum(e['event'] == 'request_failed' for e in events),
    index_tail_bytes=(EVID / 'archive_index/range_0001.bin').stat().st_size, png_files=len(list(EVID.rglob('*.png'))),
    controller_pid_is_launcher=ctl['worker_pid'] == op['launcher_pid'] != op['actual_http_worker_pid'] == ck['worker_pid'],
    remaining_total=150_000_000 - sum(reserved), remaining_index=16_000_000 - sum(reserved),
    fresh_index_reread_fits=sum(reserved) <= 16_000_000 - sum(reserved))
print(json.dumps(out, indent=2))
sys.exit(0 if all(v for k, v in out.items() if isinstance(v, bool) and k != 'request_failed_events') else 1)
