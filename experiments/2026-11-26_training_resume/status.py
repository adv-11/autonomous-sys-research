# Claude Opus: read-only remote status for both stages (queue logs, markers, last epochs, GPU).
import pathlib
import subprocess

for E in (pathlib.Path('/content/evidence'), pathlib.Path('/content/yevidence')):
    q = E / 'queue.log'
    if not q.exists():
        continue
    print('==', E)
    print(q.read_text()[-1500:])
    print('markers:', sorted(p.name for p in E.iterdir() if p.name.startswith(('DONE_', 'FAIL_', 'QUEUE_'))))
for ep in [*pathlib.Path('/content/evidence').glob('*/epochs.jsonl'), *pathlib.Path('/content/runs').glob('*/updates.jsonl')]:
    rows = ep.read_text().splitlines()
    print(ep, len(rows), rows[-1][:260] if rows else '')
print(subprocess.run(['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used', '--format=csv,noheader'],
                     capture_output=True, text=True).stdout)
