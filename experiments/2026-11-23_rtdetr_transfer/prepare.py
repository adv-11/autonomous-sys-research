"""GPT Sol: CPU-only contract/manifest preparation; never imports torch."""
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = Path('C:/Users/Advait/autonomous-sys-research')
OUT = ROOT / 'outputs/rtdetr_transfer_20261123'
OLD = ROOT / 'outputs/bdd_transfer_20261115/private'
sys.path.insert(0, str(HERE.parent / '2026-11-15_bdd_clearday_transfer'))
import common as C


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def sha(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    cfg = json.loads((HERE / 'config.json').read_text())
    weights = OUT / 'official_init.pth'
    if not weights.exists():
        urllib.request.urlretrieve(cfg['model']['official_checkpoint_url'], weights)
    print(json.dumps({'weights_bytes': weights.stat().st_size, 'weights_sha256': sha(weights)}), flush=True)
    source = json.loads((OLD / 'manifest_source_train.json').read_text())
    selection = set(json.loads((OLD / 'manifest_selection.json').read_text()))
    val = set(json.loads((OLD / 'manifest_val.json').read_text()))
    nightcal = set(json.loads((OLD / 'manifest_nightcal.json').read_text()))
    blocked = set(source) | selection | val | nightcal
    nights = []
    with zipfile.ZipFile(ROOT / 'data/bdd100k/archives/bdd100k_labels.berkeley-candidate.zip') as archive:
        for item in archive.infolist():
            parts = item.filename.split('/')
            if item.is_dir() or len(parts) != 3 or parts[1] != 'train':
                continue
            doc = json.loads(archive.read(item))
            if doc['attributes'].get('timeofday') == 'night' and doc['name'] not in blocked:
                nights.append(doc['name'])
    def choose(names, salt):
        return sorted(sorted(names, key=lambda n: hashlib.sha256((salt + n).encode()).hexdigest())[:4000])
    manifest = {'day': choose(source, 'rtdetr-adapt-day-v1:'),
                'night': choose(nights, 'rtdetr-adapt-night-v1:')}
    assert len(manifest['day']) == len(manifest['night']) == 4000
    assert not set(manifest['night']) & blocked
    (OUT / 'manifest_adaptation.json').write_bytes(canonical(manifest))
    print(json.dumps({'adaptation_manifest_sha256': sha(OUT / 'manifest_adaptation.json'),
                      'day_images': 4000, 'night_images': 4000,
                      'eligible_night_pool': len(nights), 'exclusion_check': 'PASS'}), flush=True)


if __name__ == '__main__':
    main()
