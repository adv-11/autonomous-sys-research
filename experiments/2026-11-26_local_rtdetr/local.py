"""GPT Sol: bounded Windows adapter; official RT-DETRv2 training stays native."""
import argparse
import hashlib
import importlib.metadata as md
import itertools
import json
import os
import random
from pathlib import Path
import subprocess
import sys
import time
import traceback
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = Path('C:/Users/Advait/autonomous-sys-research')
OLD = ROOT / 'outputs/bdd_transfer_20261115/private'
PIN = ROOT / 'outputs/rtdetr_transfer_20261123'
OUT = ROOT / 'outputs/local_rtdetr_20261126'
OFFICIAL = PIN / 'official/rtdetrv2_pytorch'
ORIGINAL = HERE.parent / '2026-11-23_rtdetr_transfer'
sys.path[:0] = [str(OFFICIAL), str(HERE.parent / '2026-11-15_bdd_clearday_transfer')]


def sha(path):
    with open(path, 'rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2), encoding='utf-8')
    os.replace(temp, path)
    print(json.dumps({'artifact': name, 'saved': True}), flush=True)


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def prepare():
    import common as C
    cfg = load(ORIGINAL / 'config.json')
    if not (OUT / 'deadline.json').exists():
        save('deadline.json', {'start_unix': time.time(), 'deadline_unix': time.time()+86400,
                              'researcher': 'GPT Sol', 'max_wall_hours': 24})
    source, selection, val = [load(OLD / f'manifest_{s}.json') for s in ('source_train', 'selection', 'val')]
    for name, expected in cfg['data']['manifests'].items():
        assert sha(OLD / name) == expected['sha256']
    assert sha(PIN / 'official_init.pth') == cfg['model']['checkpoint_sha256']
    mixed = load(PIN / 'manifest_adaptation.json')
    assert sha(PIN / 'manifest_adaptation.json') == cfg['training']['adaptation']['manifest_sha256']
    control = sorted(sorted(source, key=lambda n: hashlib.sha256(('rtdetr-local-day-control-v1:'+n).encode()).hexdigest())[:8000])
    groups = {'source': set(source), 'day_control': set(control), 'adaptation': set(mixed['day']+mixed['night'])}
    forbidden = set(selection) | set(val) | set(load(OLD / 'manifest_nightcal.json'))
    assert all(not s & forbidden for s in groups.values())
    assert len(source) == 10635 and len(selection) == 1842 and len(val) == 10000
    assert len(groups['day_control']) == len(groups['adaptation']) == 8000
    save('manifest_day_control.json', {'salt': 'rtdetr-local-day-control-v1:', 'names': control})
    want = {f'100k/train/{n}.jpg': ('train', n) for n in set(source)|set(selection)|set(mixed['night'])}
    want.update({f'100k/val/{n}.jpg': ('val', n) for n in val})
    from PIL import Image
    with zipfile.ZipFile(ROOT / 'data/bdd100k/archives/bdd100k_images_100k.mirror-unverified.zip') as archive:
        for member, (split, name) in want.items():
            dest = OUT / f'data/images/{split}/{name}.jpg'
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                dest.write_bytes(archive.read(member))
            with Image.open(dest) as im:
                assert im.size == (1280, 720)
    required = set(source) | set(mixed['night'])
    docs = {}
    with zipfile.ZipFile(ROOT / 'data/bdd100k/archives/bdd100k_labels.berkeley-candidate.zip') as archive:
        for item in archive.infolist():
            parts = item.filename.split('/')
            if item.is_dir() or len(parts) != 3 or parts[1] != 'train':
                continue
            name = Path(item.filename).stem
            if name in required:
                docs[name] = json.loads(archive.read(item))
    assert set(docs) == required
    for group, names in groups.items():
        images, annotations = [], []
        for i, name in enumerate(sorted(names)):
            images.append(dict(id=i, file_name=name+'.jpg', width=1280, height=720))
            boxes, _ = C.convert_objects(docs[name]['frames'][0]['objects'])
            for cls, x1, y1, x2, y2 in boxes:
                annotations.append(dict(id=len(annotations), image_id=i, category_id=cls,
                                        bbox=[x1,y1,x2-x1,y2-y1], area=(x2-x1)*(y2-y1), iscrowd=0))
        path = OUT / f'data/{group}.json'
        path.write_text(json.dumps(dict(images=images, annotations=annotations,
                            categories=[dict(id=i,name=n) for i,n in enumerate(C.CLASSES)])))
        save(group+'_data.json', dict(images=len(images), objects=len(annotations), sha256=sha(path)))
    save('preparation.json', dict(status='PASS', extracted_images=len(want),
         day_control_manifest_sha256=sha(OUT/'manifest_day_control.json'),
         packages={n:md.version(n) for n in ['torch','torchvision','numpy','scipy','Pillow','faster-coco-eval','PyYAML']},
         python=sys.version, official_source_commit=cfg['model']['code_commit'],
         note='Existing local runtime; no numerical equivalence to Colab asserted.'))


def configure(batch, epochs, arm):
    import yaml
    from src.core import YAMLConfig
    recipe = yaml.safe_load((ORIGINAL/'recipe.yml').read_text())
    recipe['__include__'] = [str(OFFICIAL/'configs/rtdetrv2/rtdetrv2_r18vd_120e_coco.yml')]
    train = recipe['train_dataloader']
    train.update(total_batch_size=batch, num_workers=0, pin_memory=False)
    train['dataset'].update(img_folder=str(OUT/'data/images/train'), ann_file=str(OUT/f'data/{"source" if arm in ("pilot","baseline") else arm}.json'))
    train['dataset']['transforms']['policy']['epoch'] = 47 if arm == 'pilot' else epochs-3
    recipe['val_dataloader']['num_workers'] = 0
    if arm not in ('pilot','baseline'):
        recipe['optimizer']['lr'] = 1e-5
        recipe['lr_warmup_scheduler']['warmup_duration'] = 200
    path = OUT/f'{arm}_recipe.yml'
    path.write_text(yaml.safe_dump(recipe))
    return YAMLConfig(str(path))


class Limited:
    def __init__(self, loader, count):
        self.loader, self.count = loader, min(count,len(loader))
    def __len__(self):
        return self.count
    def __iter__(self):
        return itertools.islice(self.loader, self.count)


def train(arm, epochs, batch):
    import torch
    from src.misc.dist_utils import setup_seed
    from src.solver.det_engine import train_one_epoch
    from src.solver._solver import BaseSolver
    setup_seed(0)
    torch.set_num_threads(4)
    cfg = configure(batch, epochs, arm)
    model = cfg.model
    init = PIN/'official_init.pth' if arm in ('pilot','baseline') else OUT/'baseline/last.pth'
    state = torch.load(init, map_location='cpu', weights_only=False)
    weights = state['ema']['module'] if 'ema' in state else state['model']
    matched, info = BaseSolver._matched_state(model.state_dict(), weights)
    assert not info['missed'], info
    assert all(any(k in name for k in ('score_head','denoising_class_embed')) for name in info['unmatched']), info
    assert arm in ('pilot','baseline') or not info['unmatched']
    model.load_state_dict(matched, strict=arm not in ('pilot','baseline'))
    del state, weights, matched
    model.to('cuda')
    criterion = cfg.criterion.to('cuda')
    optimizer, scheduler, warmup = cfg.optimizer, cfg.lr_scheduler, cfg.lr_warmup_scheduler
    ema, scaler, loader = cfg.ema.to('cuda'), cfg.scaler, cfg.train_dataloader
    directory = OUT/arm
    directory.mkdir(exist_ok=True)
    save(arm+'/initialization.json', dict(checkpoint_sha256=sha(init), **info))
    save(arm+'/resolved_config.json', cfg.yaml_cfg)
    attempted = successful = 0
    original = scaler.step
    start = time.time()
    def step(*args, **kwargs):
        nonlocal attempted, successful
        attempted += 1
        result = original(*args, **kwargs)
        successful += int(not any(float(v.item()) for v in scaler._found_inf_per_device(optimizer).values()))
        if attempted == 1 or attempted % 25 == 0:
            torch.cuda.synchronize()
            save(arm+'/progress.json', dict(attempted_updates=attempted, successful_updates=successful,
                 seconds=time.time()-start, peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30,
                 peak_reserved_gib=torch.cuda.max_memory_reserved()/2**30, batch=batch))
        return result
    scaler.step = step
    for epoch in range(epochs):
        loader.set_epoch(epoch)
        tick = time.time()
        active = Limited(loader,128) if arm == 'pilot' else loader
        stats = train_one_epoch(model, criterion, active, optimizer, torch.device('cuda'), epoch,
                     max_norm=.1, print_freq=25, ema=ema, scaler=scaler, lr_warmup_scheduler=warmup)
        torch.cuda.synchronize()
        if warmup.finished():
            scheduler.step()
        row = dict(epoch=epoch+1, seconds=time.time()-tick, attempted_updates=attempted,
                   successful_updates=successful, amp_skipped=attempted-successful,
                   peak_allocated_gib=torch.cuda.max_memory_allocated()/2**30, **stats)
        with (directory/'epochs.jsonl').open('a') as stream:
            stream.write(json.dumps(row)+'\n')
        temp = directory/'last.tmp.pth'
        torch.save(dict(model=model.state_dict(), ema=ema.state_dict(), epoch=epoch+1,
                        optimizer=optimizer.state_dict(), scaler=scaler.state_dict(),
                        scheduler=scheduler.state_dict(), warmup=warmup.state_dict(),
                        torch_rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all(),
                        python_rng=random.getstate(), numpy_rng=__import__('numpy').random.get_state(),
                        resolved_config=cfg.yaml_cfg), temp)
        os.replace(temp, directory/'last.pth')
        print(json.dumps(dict(arm=arm, **row)),flush=True)
    save(arm+'_summary.json', dict(status='PASS', epochs=epochs, batch=batch, seconds=time.time()-start,
          attempted_updates=attempted, successful_updates=successful,
          images=128*batch if arm=='pilot' else epochs*(10635 if arm=='baseline' else 8000),
          checkpoint_sha256=sha(directory/'last.pth')))


def guard(args):
    deadline = load(OUT/'deadline.json')['deadline_unix']
    seconds = max(0, min(deadline-time.time(), args.cap))
    command = [sys.executable, '-u', str(__file__), args.child, '--arm', args.arm,
               '--epochs',str(args.epochs),'--batch',str(args.batch)]
    log = OUT/f'{args.child}_{args.arm}_b{args.batch}.log'
    with log.open('ab') as stream:
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        save('owned_process.json',dict(pid=process.pid, guard_pid=os.getpid(), command=command,
                                      deadline_unix=deadline, stage_cap_seconds=seconds))
        try:
            code = process.wait(timeout=seconds)
        except subprocess.TimeoutExpired:
            # The child is still held by Popen; kill only that exact owned tree.
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'], stdout=stream, stderr=stream)
            code = process.wait(timeout=30)
            save('deadline_stop.json', dict(pid=process.pid, exit_code=code, time_unix=time.time()))
        save(f'{args.child}_{args.arm}_b{args.batch}_exit.json',dict(exit_code=code,time_unix=time.time()))
        snapshot = subprocess.run(['nvidia-smi','--query-compute-apps=pid,process_name,used_memory',
                                   '--format=csv'],capture_output=True,text=True)
        save(f'{args.child}_{args.arm}_cleanup.json',dict(owned_child_pid=process.pid,
             owned_child_exited=process.poll() is not None,gpu_query_exit=snapshot.returncode,
             compute_processes=snapshot.stdout,gpu_query_error=snapshot.stderr,time_unix=time.time()))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('stage',choices=['prepare','train','guard','study'])
    p.add_argument('--child',default='train')
    p.add_argument('--arm',default='pilot')
    p.add_argument('--epochs',type=int,default=1)
    p.add_argument('--batch',type=int,default=16)
    p.add_argument('--cap',type=float,default=2700)
    a = p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    try:
        if a.stage == 'prepare': prepare()
        elif a.stage == 'guard': guard(a)
        elif a.stage == 'study':
            plan = load(HERE/'plan.json')
            assert plan['batch'] == a.batch
            for arm,epochs in [('baseline',plan['baseline_epochs']),('day_control',5),('adaptation',5)]:
                for command in ([sys.executable,'-u',str(__file__),'train','--arm',arm,
                                 '--epochs',str(epochs),'--batch',str(a.batch)],
                                [sys.executable,'-u',str(HERE/'infer.py'),'--arm',arm,'--batch',str(a.batch)]):
                    with (OUT/f'{arm}_{"infer" if "infer.py" in command[2] else "train"}.log').open('ab') as stream:
                        subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=True,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            with (OUT/'evaluate.log').open('ab') as stream:
                subprocess.run([sys.executable,'-u',str(HERE/'evaluate.py')],stdout=stream,
                               stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run([sys.executable,str(HERE/'report.py')],check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
            # Plotting is isolated from the existing GPU environment and is not
            # a training prerequisite. One bounded attempt; no dependency loop.
            try:
                with (OUT/'figures.log').open('ab') as stream:
                    subprocess.run(['uv','run','--no-project','--with','matplotlib','--with','numpy',
                                    '--python',sys.executable,str(HERE/'figures.py')],
                                   stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=300,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
            except (OSError,subprocess.SubprocessError) as error:
                save('figures_failure.json',dict(type=type(error).__name__,message=str(error)))
            save('study_complete.json',dict(status='PASS',time_unix=time.time(),plan_sha256=sha(HERE/'plan.json')))
        else: train(a.arm,a.epochs,a.batch)
    except BaseException as error:
        save(f'{a.stage}_{a.arm}_b{a.batch}_failure_{int(time.time())}.json',
             dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        raise
