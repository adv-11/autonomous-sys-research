"""Claude Opus: overnight seed-1 replicate of the frozen local RT-DETR recipe.

Implements step 2 of docs/research/2026-11-27_rtdetr_interpretation_next_steps.md.
The seed-0 code in ../2026-11-26_local_rtdetr is reused unchanged; this file only
changes the output folder, the training seed, and the number of loader workers.
Images and annotations are the seed-0 prepared copies (directory junction).
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-11-26_local_rtdetr'))
import local as L  # noqa: E402  (also puts the official RT-DETR source on sys.path)

SEED0 = L.ROOT / 'outputs/local_rtdetr_20261126'
NEW = L.ROOT / 'outputs/local_rtdetr_seed1_20261127'
SEED = 1
STEPS_BASELINE = 20 * 665          # 10,635 images / batch 16 per epoch
STEPS_CONTINUATION = 5 * 500       # 8,000 images / batch 16 per epoch
GATE_STEPS, GATE_MEDIAN_S = 200, 1.6
BONUS_HOURS, LIMIT_HOURS = 5.5, 9.0


def configure(batch, epochs, arm, workers=0, tag=''):
    """Seed-0 configure() with the loader worker count exposed (workers=0 is identical)."""
    import yaml
    from src.core import YAMLConfig
    recipe = yaml.safe_load((L.ORIGINAL / 'recipe.yml').read_text())
    recipe['__include__'] = [str(L.OFFICIAL / 'configs/rtdetrv2/rtdetrv2_r18vd_120e_coco.yml')]
    train = recipe['train_dataloader']
    # Non-persistent workers: the official loader pushes the epoch into the dataset and
    # collate function each epoch; persistent workers would keep stale copies and the
    # strong-augmentation stop at epochs-3 would never take effect.
    train.update(total_batch_size=batch, num_workers=workers, pin_memory=False)
    train['dataset'].update(img_folder=str(L.OUT / 'data/images/train'),
                            ann_file=str(L.OUT / f'data/{"source" if arm == "baseline" else arm}.json'))
    train['dataset']['transforms']['policy']['epoch'] = epochs - 3
    recipe['val_dataloader']['num_workers'] = 0
    if arm != 'baseline':
        recipe['optimizer']['lr'] = 1e-5
        recipe['lr_warmup_scheduler']['warmup_duration'] = 200
    path = L.OUT / f'{arm}_{tag}recipe.yml'
    path.write_text(yaml.safe_dump(recipe))
    return YAMLConfig(str(path))


def child(args):
    out = Path(args.out)
    L.OUT = out
    if args.stage == 'train':
        import src.misc.dist_utils as D
        original = D.setup_seed
        D.setup_seed = lambda _seed, deterministic=False: original(SEED, deterministic)
        L.configure = lambda b, e, a: configure(b, e, a, workers=args.workers)
        L.train(args.arm, args.epochs, 16)
    else:
        import infer as I
        I.OUT = out
        I.configure = lambda b, e, a: configure(b, e, a, workers=0, tag='infer_')
        I.infer(args.arm, 16)


class Study:
    def __init__(self):
        self.start = time.time()
        self.deadline = self.start + LIMIT_HOURS * 3600
        self.log = []

    def hours(self):
        return (time.time() - self.start) / 3600

    def note(self, **event):
        event['elapsed_h'] = round(self.hours(), 3)
        self.log.append(event)
        L.OUT = NEW
        L.save('study_events.json', self.log)

    def launch(self, out, stage, arm, epochs=0, workers=0):
        command = [sys.executable, '-u', str(__file__), stage, '--out', str(out), '--arm', arm,
                   '--epochs', str(epochs), '--workers', str(workers)]
        stream = (out / f'{arm}_{stage}.log').open('ab')
        process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        self.note(event='launch', stage=stage, arm=arm, workers=workers, pid=process.pid, out=str(out))
        return process

    def kill(self, process, reason):
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True)
        process.wait(timeout=60)
        self.note(event='stopped', pid=process.pid, reason=reason)

    def wait(self, process, label):
        try:
            code = process.wait(timeout=max(1, self.deadline - time.time()))
        except subprocess.TimeoutExpired:
            self.kill(process, f'{label}: {LIMIT_HOURS} h study limit reached')
            raise RuntimeError(f'{label} exceeded the {LIMIT_HOURS} h limit')
        self.note(event='exit', label=label, exit_code=code)
        if code != 0:
            raise RuntimeError(f'{label} exited with {code}')

    def gate(self, process, out):
        """Median seconds per optimizer step over steps 25..200 (startup excluded)."""
        samples, progress = [], out / 'baseline/progress.json'
        while process.poll() is None and time.time() - self.start < 1800:
            if progress.exists():
                try:
                    p = json.loads(progress.read_text())
                except (OSError, ValueError):
                    p = None
                if p and (not samples or p['attempted_updates'] != samples[-1][0]):
                    samples.append((p['attempted_updates'], p['seconds']))
                    if p['attempted_updates'] >= GATE_STEPS:
                        break
            time.sleep(2)
        rates = [(s2 - s1) / (a2 - a1) for (a1, s1), (a2, s2) in zip(samples, samples[1:]) if a1 >= 25]
        median = statistics.median(rates) if rates else None
        return median, samples

    def train_infer(self, out, arm, epochs, workers):
        self.wait(self.launch(out, 'train', arm, epochs, workers), f'train {arm}')
        self.wait(self.launch(out, 'infer', arm), f'infer {arm}')

    def run(self):
        NEW.mkdir(parents=True, exist_ok=True)
        L.OUT = NEW
        seed0 = {a: dict(train=L.load(SEED0 / f'{a}_summary.json')['seconds'],
                         infer=L.load(SEED0 / f'{a}_inference.json')['seconds'])
                 for a in ('baseline', 'day_control', 'adaptation')}
        commit = subprocess.run(['git', '-C', str(HERE), 'rev-parse', 'HEAD'], capture_output=True, text=True)
        L.save('study_start.json', dict(researcher='Claude Opus', start_unix=self.start, seed=SEED,
               limit_hours=LIMIT_HOURS, gate=dict(steps=GATE_STEPS, median_seconds=GATE_MEDIAN_S),
               bonus_hours=BONUS_HOURS, git_commit=commit.stdout.strip(), run_sha256=L.sha(__file__),
               seed0_seconds=seed0, approval='User approved the overnight run and GPU self-approval on 2026-11-27'))
        out = NEW / 'main'
        self.link(out)
        process = self.launch(out, 'train', 'baseline', 20, 4)
        median, samples = self.gate(process, out)
        projected = median * STEPS_BASELINE / 3600 if median else None
        ok = process.poll() is None and median is not None and median <= GATE_MEDIAN_S
        self.note(event='speed_gate', median_step_s=median, projected_baseline_h=projected,
                  samples=samples, passed=ok)
        workers, bonus = 4, ok and projected <= BONUS_HOURS
        if not ok:
            if process.poll() is None:
                self.kill(process, 'speed gate failed')
            if (out / 'baseline').exists():
                (out / 'baseline').rename(out / f'baseline_workers4_aborted_{int(time.time())}')
            fallback = self.hours() + (seed0['baseline']['train'] + seed0['baseline']['infer']) / 3600
            self.note(event='fallback_projection', projected_total_h=fallback)
            if fallback <= LIMIT_HOURS:
                workers = 0
                process = self.launch(out, 'train', 'baseline', 20, 0)
            else:
                return self.substitute(seed0)
        self.note(event='decision', workers=workers, bonus_continuations=bonus)
        self.epoch_check(process, out, seed0)
        self.wait(process, 'train baseline')
        self.wait(self.launch(out, 'infer', 'baseline'), 'infer baseline')
        if bonus:
            need = sum(STEPS_CONTINUATION * median + seed0[a]['infer'] for a in ('day_control', 'adaptation')) / 3600
            if self.hours() + need <= LIMIT_HOURS:
                for arm in ('day_control', 'adaptation'):
                    self.train_infer(out, arm, 5, workers)
            else:
                self.note(event='bonus_skipped', needed_h=need)
        self.finish()

    def epoch_check(self, process, out, seed0):
        epochs = out / 'baseline/epochs.jsonl'
        while process.poll() is None:
            rows = epochs.read_text().splitlines() if epochs.exists() else []
            if len(rows) >= 2:
                mean = statistics.mean(json.loads(r)['seconds'] for r in rows[:2])
                projected = self.hours() + (18 * mean + seed0['baseline']['infer']) / 3600
                self.note(event='epoch2_projection', mean_epoch_s=mean, projected_total_h=projected)
                if projected > LIMIT_HOURS:
                    self.kill(process, 'epoch-2 projection above limit')
                    raise RuntimeError('epoch-2 projection above the limit; no partial checkpoint is used')
                return
            time.sleep(30)

    def substitute(self, seed0):
        """Pre-declared substitute: both continuations from the seed-0 baseline, training seed 1."""
        out = NEW / 'substitute'
        self.link(out)
        (out / 'baseline').mkdir(exist_ok=True)
        shutil.copy2(SEED0 / 'baseline/last.pth', out / 'baseline/last.pth')
        self.note(event='decision', substitute=True, workers=0)
        for arm in ('day_control', 'adaptation'):
            self.train_infer(out, arm, 5, 0)
        self.finish()

    def link(self, out):
        out.mkdir(parents=True, exist_ok=True)
        if not (out / 'data').exists():
            subprocess.run(['cmd', '/c', 'mklink', '/J', str(out / 'data'), str(SEED0 / 'data')],
                           check=True, capture_output=True)

    def finish(self):
        with (NEW / 'evaluate.log').open('ab') as stream:
            code = subprocess.run([sys.executable, '-u', str(HERE / 'evaluate_seed1.py')], stdout=stream,
                                  stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW).returncode
        self.note(event='evaluation', exit_code=code)
        L.OUT = NEW
        L.save('study_complete.json', dict(status='PASS', training='PASS',
               evaluation='PASS' if code == 0 else 'FAILED (rerun on CPU)', elapsed_h=self.hours()))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('stage', choices=['study', 'train', 'infer'])
    p.add_argument('--out')
    p.add_argument('--arm')
    p.add_argument('--epochs', type=int, default=0)
    p.add_argument('--workers', type=int, default=0)
    a = p.parse_args()
    try:
        child(a) if a.stage != 'study' else Study().run()
    except BaseException as error:
        L.OUT = Path(a.out) if a.out else NEW
        L.OUT.mkdir(parents=True, exist_ok=True)
        L.save(f'{a.stage}_{a.arm}_failure_{int(time.time())}.json',
               dict(type=type(error).__name__, message=str(error), traceback=traceback.format_exc()))
        raise
