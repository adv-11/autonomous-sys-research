"""GPT Sol: bounded experiment stages; official model/train_one_epoch/postprocessor.

Runs ONLY inside the owned Colab VM. No model or evaluator implementation is
replaced. The small loop omits validation/model selection entirely.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request
import zipfile

PACKET = Path('/content/packet')
OUT = Path('/content/evidence')
OUT.mkdir(exist_ok=True)
CFG = json.loads((PACKET / 'config.json').read_text())
sys.path.insert(0, str(PACKET))
import common as C


def sha(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2))
    print(json.dumps({'artifact': name, **value}), flush=True)


def download(url, dest, digest):
    dest = Path(dest)
    if dest.exists() and sha(dest) == digest:
        return
    print(json.dumps({'download': url}), flush=True)
    start = time.time()
    h = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=120) as response, dest.open('wb') as target:
        while chunk := response.read(16 << 20):
            h.update(chunk)
            target.write(chunk)
            if time.time() - start > 1200:
                raise TimeoutError('direct dataset download exceeded 20 minutes')
    assert h.hexdigest() == digest, f'{dest.name}: hash mismatch {h.hexdigest()}'


def setup():
    signal.alarm(2700)
    start = time.time()
    assert sys.version_info[:2] in ((3, 11), (3, 12)), sys.version
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet',
                    'torch==2.4.1', 'torchvision==0.19.1', '--index-url',
                    'https://download.pytorch.org/whl/cu121'], check=True)
    subprocess.run([sys.executable, '-m', 'pip', 'install', '--quiet',
                    'numpy==1.26.4', 'scipy==1.14.1', 'Pillow==11.0.0',
                    'faster-coco-eval==1.6.8', 'PyYAML==6.0.2', 'tensorboard==2.18.0',
                    'packaging==24.2', 'pycocotools==2.0.8'], check=True)
    subprocess.run(['git', 'clone', '--quiet', 'https://github.com/lyuwenyu/RT-DETR.git', '/content/RT-DETR'], check=True)
    subprocess.run(['git', '-C', '/content/RT-DETR', 'checkout', '--quiet', CFG['model']['code_commit']], check=True)
    download(CFG['data']['images_url'], '/content/images.zip', CFG['data']['images_archive_sha256'])
    download(CFG['data']['labels_url'], '/content/labels.zip', CFG['data']['labels_archive_sha256'])
    assert sha(PACKET / 'official_init.pth') == CFG['model']['checkpoint_sha256']
    source = json.loads((PACKET / 'manifest_source_train.json').read_text())
    selection = json.loads((PACKET / 'manifest_selection.json').read_text())
    val = json.loads((PACKET / 'manifest_val.json').read_text())
    adapt = json.loads((PACKET / 'manifest_adaptation.json').read_text())
    assert sha(PACKET / 'manifest_adaptation.json') == CFG['training']['adaptation']['manifest_sha256']
    want_train = set(source) | set(selection) | set(adapt['night'])
    want = {f'100k/train/{n}.jpg': ('train', n) for n in want_train}
    want.update({f'100k/val/{n}.jpg': ('val', n) for n in val})
    from PIL import Image
    with zipfile.ZipFile('/content/images.zip') as archive:
        for member, (split, name) in want.items():
            dest = Path(f'/content/data/images/{split}/{name}.jpg')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(archive.read(member))
            with Image.open(dest) as image:
                assert image.size == (1280, 720)
    groups = {'source': set(source), 'adaptation': set(adapt['day']) | set(adapt['night'])}
    docs = {}
    with zipfile.ZipFile('/content/labels.zip') as archive:
        required = groups['source'] | groups['adaptation']
        for item in archive.infolist():
            parts = item.filename.split('/')
            if item.is_dir() or len(parts) != 3 or parts[1] != 'train':
                continue
            name = Path(item.filename).stem
            if name not in required:
                continue
            doc = json.loads(archive.read(item))
            assert doc['name'] == name
            docs[name] = doc
    assert required == set(docs)
    for group, members in groups.items():
        images, annotations = [], []
        for i, name in enumerate(sorted(members)):
            images.append({'id': i, 'file_name': name + '.jpg', 'width': 1280, 'height': 720})
            boxes, _ = C.convert_objects(docs[name]['frames'][0]['objects'])
            for cls, x1, y1, x2, y2 in boxes:
                annotations.append({'id': len(annotations), 'image_id': i, 'category_id': cls,
                                    'bbox': [x1, y1, x2-x1, y2-y1], 'area': (x2-x1)*(y2-y1), 'iscrowd': 0})
        data = {'images': images, 'annotations': annotations,
                'categories': [{'id': i, 'name': name} for i, name in enumerate(C.CLASSES)]}
        path = Path(f'/content/data/{group}.json')
        path.write_text(json.dumps(data))
        save(group + '_data.json', {'images': len(images), 'objects': len(annotations), 'sha256': sha(path)})
    import importlib.metadata as md
    (OUT / 'pip_freeze.txt').write_bytes(subprocess.check_output([sys.executable, '-m', 'pip', 'freeze']))
    save('setup.json', {'status': 'PASS', 'seconds': time.time()-start, 'python': sys.version,
                        'packages': {k: md.version(k) for k in ['torch', 'torchvision', 'numpy', 'faster-coco-eval', 'scipy', 'Pillow', 'PyYAML']},
                        'image_archive_sha256': sha('/content/images.zip'), 'label_archive_sha256': sha('/content/labels.zip')})
    signal.alarm(0)


def train(arm, epochs):
    if arm == 'pilot':
        signal.alarm(1100)  # <= 1 CU at the maximum admitted rate
    import torch
    sys.path.insert(0, '/content/RT-DETR/rtdetrv2_pytorch')
    from src.core import YAMLConfig
    from src.misc.dist_utils import setup_seed
    from src.solver.det_engine import train_one_epoch
    from src.solver._solver import BaseSolver
    setup_seed(0)
    torch.set_num_threads(4)
    cfg = YAMLConfig(str(PACKET / 'recipe.yml'))
    cfg.yaml_cfg['train_dataloader']['dataset']['transforms']['policy']['epoch'] = 47 if arm == 'pilot' else max(0, epochs-3)
    adaptation = arm == 'adaptation'
    if adaptation:
        cfg.yaml_cfg['train_dataloader']['dataset']['ann_file'] = '/content/data/adaptation.json'
        cfg.yaml_cfg['optimizer']['lr'] = 0.00001
        cfg.yaml_cfg['lr_warmup_scheduler']['warmup_duration'] = 200
    model = cfg.model
    path = OUT / 'baseline/last.pth' if adaptation else PACKET / 'official_init.pth'
    state = torch.load(path, map_location='cpu', weights_only=False)
    weights = state['ema']['module'] if 'ema' in state else state['model']
    matched, info = BaseSolver._matched_state(model.state_dict(), weights)
    assert not info['missed'], info
    allowed = ('score_head', 'denoising_class_embed')
    assert not adaptation or not info['unmatched'], info
    assert all(any(k in name for k in allowed) for name in info['unmatched']), info
    model.load_state_dict(matched, strict=adaptation)
    model.to('cuda')
    criterion = cfg.criterion.to('cuda')
    optimizer = cfg.optimizer
    scheduler, warmup = cfg.lr_scheduler, cfg.lr_warmup_scheduler
    ema = cfg.ema.to('cuda')
    scaler = cfg.scaler
    loader = cfg.train_dataloader
    directory = OUT / arm
    directory.mkdir(exist_ok=True)
    (directory / 'initialization.json').write_text(json.dumps({'checkpoint_sha256': sha(path), **info}, indent=2))
    (directory / 'resolved_config.json').write_text(json.dumps(cfg.yaml_cfg, indent=2))
    attempted = successful = 0
    original_step = scaler.step
    def count_step(*args, **kwargs):
        nonlocal attempted, successful
        attempted += 1
        result = original_step(*args, **kwargs)
        # GradScaler found_inf is populated after step and before update.
        found = scaler._found_inf_per_device(optimizer)
        successful += int(not any(float(v.item()) for v in found.values()))
        return result
    scaler.step = count_step
    start = time.time()
    for epoch in range(epochs):
        loader.set_epoch(epoch)
        tick = time.time()
        stats = train_one_epoch(model, criterion, loader, optimizer, torch.device('cuda'), epoch,
                                max_norm=0.1, print_freq=100, ema=ema, scaler=scaler,
                                lr_warmup_scheduler=warmup)
        if warmup.finished():
            scheduler.step()
        row = {'epoch': epoch+1, 'seconds': time.time()-tick, 'attempted_updates': attempted,
               'successful_updates': successful, 'amp_skipped': attempted-successful,
               'peak_memory_gib': torch.cuda.max_memory_allocated()/2**30, **stats}
        with (directory / 'epochs.jsonl').open('a') as stream:
            stream.write(json.dumps(row)+'\n')
        torch.save({'model': model.state_dict(), 'ema': ema.state_dict(), 'epoch': epoch+1,
                    'optimizer': optimizer.state_dict(), 'scaler': scaler.state_dict()}, directory / 'last.pth')
        print(json.dumps({'arm': arm, **row}), flush=True)
    save(arm + '_summary.json', {'status': 'PASS', 'epochs': epochs, 'seconds': time.time()-start,
                                'attempted_updates': attempted, 'successful_updates': successful,
                                'checkpoint_sha256': sha(directory / 'last.pth')})


def infer(arm):
    import numpy as np
    import torch
    import torchvision.transforms as T
    from PIL import Image
    sys.path.insert(0, '/content/RT-DETR/rtdetrv2_pytorch')
    from src.core import YAMLConfig
    cfg = YAMLConfig(str(PACKET / 'recipe.yml'))
    state = torch.load(OUT / arm / 'last.pth', map_location='cpu', weights_only=False)
    model = cfg.model
    model.load_state_dict(state['ema']['module'], strict=True)
    model = model.deploy().to('cuda').eval()
    post = cfg.postprocessor.deploy().to('cuda')
    selection = json.loads((PACKET / 'manifest_selection.json').read_text())
    val = json.loads((PACKET / 'manifest_val.json').read_text())
    names = list(selection) + sorted(val)
    transforms = T.Compose([T.Resize((640, 640)), T.ToTensor()])
    boxes, scores, labels, query_ids, logits, raw_boxes = [], [], [], [], [], []
    start = time.time()
    with torch.inference_mode():
        for begin in range(0, len(names), 16):
            chunk = names[begin:begin+16]
            inputs = []
            for name in chunk:
                split = 'train' if begin < len(selection) else 'val'
                # A batch can cross the selection/validation boundary.
                split = 'train' if name in selection else 'val'
                with Image.open(f'/content/data/images/{split}/{name}.jpg') as image:
                    inputs.append(transforms(image.convert('RGB')))
            output = model(torch.stack(inputs).to('cuda'))
            lab, box, score = post(output, torch.tensor([[1280, 720]]*len(chunk), device='cuda'))
            idx = output['pred_logits'].sigmoid().flatten(1).topk(300, dim=-1).indices // 10
            assert bool(torch.isfinite(box).all() and torch.isfinite(score).all())
            boxes.extend(box.cpu().numpy()); scores.extend(score.cpu().numpy()); labels.extend(lab.cpu().numpy())
            query_ids.extend(idx.cpu().numpy()); logits.extend(output['pred_logits'].cpu().numpy())
            raw_boxes.extend(output['pred_boxes'].cpu().numpy())
            if begin % 1600 == 0:
                print(json.dumps({'infer': arm, 'images': begin+len(chunk), 'seconds': time.time()-start}), flush=True)
    boxes, scores, labels = np.asarray(boxes), np.asarray(scores), np.asarray(labels)
    # Full native 300 query-class candidates retained; pedestrian filtering is later.
    path = OUT / f'{arm}_native.npz'
    np.savez_compressed(path, names=np.asarray(names), boxes=boxes, scores=scores, labels=labels,
                        query_ids=np.asarray(query_ids), logits=np.asarray(logits), raw_boxes=np.asarray(raw_boxes))
    pboxes, pscores, offsets = [], [], [0]
    for box, score, lab in zip(boxes, scores, labels):
        keep = (lab == 0) & (score >= 0.0001)
        pboxes.extend(box[keep]); pscores.extend(score[keep]); offsets.append(len(pscores))
    compat = OUT / f'{arm}_pedestrian.npz'
    np.savez_compressed(compat, names=np.asarray(names), boxes=np.asarray(pboxes, dtype=np.float32).reshape(-1, 4),
                        scores=np.asarray(pscores, dtype=np.float32), offsets=np.asarray(offsets),
                        all_class_candidates=np.full(len(names), 300))
    save(arm + '_inference.json', {'status': 'PASS', 'images': len(names), 'seconds': time.time()-start,
                                  'native_sha256': sha(path), 'pedestrian_sha256': sha(compat),
                                  'native_candidates_per_image': 300, 'pedestrian_candidates': len(pscores)})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['setup', 'train', 'infer'])
    parser.add_argument('--arm', default='pilot')
    parser.add_argument('--epochs', type=int, default=1)
    args = parser.parse_args()
    if args.stage == 'setup':
        setup()
    elif args.stage == 'train':
        train(args.arm, args.epochs)
    else:
        infer(args.arm)
