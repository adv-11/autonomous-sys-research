# Claude Opus: read-only remote status (queue log, stage log tail, epochs, GPU).
import pathlib, subprocess
E = pathlib.Path('/content/evidence')
q = E / 'queue.log'
print(q.read_text() if q.exists() else 'no queue.log')
print('markers:', sorted(p.name for p in E.glob('QUEUE_*')))
lines = q.read_text().split('\n') if q.exists() else []
starts = [l.split()[-1] for l in lines if ' START ' in l]
if starts:
    log = E / (starts[-1] + '.log')
    if log.exists():
        print('--- tail', log.name); print('\n'.join(log.read_text(errors='replace').splitlines()[-6:]))
for arm in ('pilot', 'baseline', 'adaptation'):
    ep = E / arm / 'epochs.jsonl'
    if ep.exists():
        rows = ep.read_text().splitlines()
        print(arm, 'epochs', len(rows), rows[-1][:300])
print(subprocess.run(['nvidia-smi', '--query-gpu=name,utilization.gpu,memory.used', '--format=csv,noheader'], capture_output=True, text=True).stdout)
