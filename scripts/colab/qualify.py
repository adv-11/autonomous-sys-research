"""Unqualified Colab-only YOLO11 CUDA harness, not a research training run.

2026-11-10: both remote attempts failed before an optimizer update. Do not treat
this script or a zero CLI exit code as qualification; repair and review first.

Three FP32 SGD updates on synthetic empty-target images check detector loss,
backward and checkpoint round-trip. No dataset or performance metric is used.
The coordinator owns allocation, usage-rate admission, retrieval and teardown.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

OUT = Path('/content/threshold_transfer_qualification')
EXPECTED = '85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5'


def main():
    if not Path('/content').is_dir() or not os.environ.get('COLAB_RELEASE_TAG'):
        raise RuntimeError('Colab-only qualification: refusing a local or unidentified runtime')
    OUT.mkdir(exist_ok=False)
    started = time.monotonic()
    record = {'status': 'FAIL', 'purpose': 'synthetic CUDA mechanical qualification only',
              'dataset': None, 'requested_successful_updates': 3, 'successful_updates': 0}

    def deadline(_signum, _frame):
        raise TimeoutError('600-second remote qualification deadline')

    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(600)
    try:
        print('QUALIFICATION: installing pinned Ultralytics; torch comes from the runtime', flush=True)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet',
                        '--disable-pip-version-check', 'ultralytics==8.4.197'],
                       check=True, timeout=240)
        import torch
        import ultralytics
        from ultralytics import YOLO
        from ultralytics.cfg import get_cfg
        if not torch.cuda.is_available():
            raise RuntimeError('Allocated runtime has no usable CUDA')
        torch.manual_seed(0)
        torch.set_num_threads(2)
        device = torch.cuda.get_device_properties(0)
        record['runtime'] = {'python': sys.version, 'torch': torch.__version__,
                             'ultralytics': ultralytics.__version__,
                             'cuda': torch.version.cuda, 'gpu': device.name,
                             'total_memory_bytes': device.total_memory}
        subprocess.run(['nvidia-smi', '--query-gpu=name,driver_version,memory.total',
                        '--format=csv,noheader'], check=True, timeout=15)
        weights = OUT / 'yolo11s.pt'
        url = 'https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11s.pt'
        with urllib.request.urlopen(url, timeout=60) as response, weights.open('wb') as target:
            while chunk := response.read(1024 * 1024):
                target.write(chunk)
                if weights.stat().st_size > 100_000_000:
                    raise RuntimeError('Unexpected checkpoint size')
        actual = hashlib.sha256(weights.read_bytes()).hexdigest()
        record['checkpoint'] = {'url': url, 'sha256': actual, 'expected_sha256': EXPECTED}
        if actual != EXPECTED:
            raise RuntimeError('Checkpoint identity mismatch; no model load permitted')
        model = YOLO(str(weights)).model.to('cuda').float().train()
        model.args = get_cfg(overrides=model.args)
        optimizer = torch.optim.SGD(model.parameters(), lr=0.0001)
        images = torch.rand(2, 3, 640, 640, device='cuda')
        batch = {'img': images, 'batch_idx': torch.empty(0, device='cuda'),
                 'cls': torch.empty(0, 1, device='cuda'),
                 'bboxes': torch.empty(0, 4, device='cuda')}
        reference = next(model.parameters()).detach().clone()
        torch.cuda.reset_peak_memory_stats()
        update_times = []
        losses = []
        for index in range(3):
            before = time.monotonic()
            optimizer.zero_grad(set_to_none=True)
            loss, _ = model.loss(batch)
            loss = loss.sum()
            if not bool(torch.isfinite(loss)):
                raise RuntimeError('Nonfinite synthetic loss')
            loss.backward()
            if not all(bool(torch.isfinite(p.grad).all()) for p in model.parameters() if p.grad is not None):
                raise RuntimeError('Nonfinite synthetic gradient')
            optimizer.step()
            torch.cuda.synchronize()
            record['successful_updates'] += 1
            update_times.append(time.monotonic() - before)
            losses.append(float(loss.detach()))
            if torch.cuda.max_memory_reserved() > device.total_memory * 0.8:
                raise RuntimeError('Qualification exceeded 80 percent reserved-memory ceiling')
            print(f'QUALIFICATION: completed update {index + 1}/3', flush=True)
        if torch.equal(reference, next(model.parameters()).detach()):
            raise RuntimeError('No parameter change observed')
        saved = OUT / 'synthetic_resume.pt'
        torch.save({'model': model.state_dict(), 'optimizer': optimizer.state_dict(),
                    'successful_updates': record['successful_updates']}, saved)
        checkpoint = torch.load(saved, map_location='cpu', weights_only=True)
        if checkpoint['successful_updates'] != 3:
            raise RuntimeError('Checkpoint counter round-trip failed')
        record.update(status='PASS', synthetic_loss=losses, update_seconds=update_times,
                      peak_reserved_bytes=torch.cuda.max_memory_reserved(),
                      checkpoint_roundtrip='counter/model/optimizer serialized and tensor values checked',
                      scope_limit='Not a resumable training recipe or detector performance result')
        for name, value in model.state_dict().items():
            if not torch.equal(checkpoint['model'][name], value.detach().cpu()):
                raise RuntimeError('Checkpoint tensor round-trip failed')
        freeze = subprocess.check_output([sys.executable, '-m', 'pip', 'freeze'], text=True, timeout=30)
        (OUT / 'environment.txt').write_text(freeze, encoding='utf8')
        record['environment_sha256'] = hashlib.sha256(freeze.encode()).hexdigest()
    except BaseException as exc:
        record.update(status='FAIL', error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        signal.alarm(0)
        record['elapsed_seconds'] = time.monotonic() - started
        (OUT / 'summary.json').write_text(json.dumps(record, indent=2, allow_nan=False), encoding='utf8')
        print('QUALIFICATION_SUMMARY=' + json.dumps(record, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
