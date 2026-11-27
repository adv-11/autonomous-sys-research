"""GPT Sol: measured training and threshold-transfer figures, CPU only."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path('C:/Users/Advait/autonomous-sys-research/outputs/rtdetr_transfer_20261123')
DEST = Path(__file__).resolve().parents[2] / 'docs/research/2026-11-23_rtdetr_transfer'
DEST.mkdir(exist_ok=True)


def main():
    data = json.loads((ROOT / 'results.json').read_text())
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False,
                         'figure.dpi': 150, 'savefig.bbox': 'tight'})
    colors = {'baseline': '#2763aa', 'adaptation': '#ce6c24'}
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
    for arm in data['arms']:
        rows = [json.loads(line) for line in (ROOT / 'evidence' / arm / 'epochs.jsonl').read_text().splitlines()]
        axes[0].plot([r['epoch'] for r in rows], [r['loss'] for r in rows], label=arm, color=colors[arm])
        axes[1].plot([r['epoch'] for r in rows], [r['seconds'] for r in rows], label=arm, color=colors[arm])
    axes[0].set(xlabel='Epoch within arm', ylabel='Mean native training loss', title='Training objective (not held-out accuracy)')
    axes[1].set(xlabel='Epoch within arm', ylabel='Seconds per epoch', title='Measured wall time')
    for ax in axes:
        ax.legend(); ax.grid(alpha=.15)
    fig.suptitle('Official RT-DETRv2 R18 · 640 px · seed 0 · final EMA')
    fig.tight_layout(); fig.savefig(DEST / 'training.png'); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, group in zip(axes, ('clear_day', 'night')):
        for arm in data['arms']:
            with np.load(ROOT / f'{arm}_{group}_curve.npz') as c:
                use = c['fppi'] <= 10
                ax.plot(c['fppi'][use], c['recall'][use], color=colors[arm], label=arm)
            point = data['arms'][arm]['operating_points']['source_fppi_1']
            if group in point['conditions']:
                p = point['conditions'][group]
                ax.scatter(p['fppi'], p['recall'], color=colors[arm], edgecolor='white', zorder=5)
        ax.set(xlabel='False positives per image', title=group.replace('_', ' ').title(), xlim=(0, 10), ylim=(0, 1))
        ax.grid(alpha=.15); ax.legend()
    axes[0].set_ylabel('Object-weighted pedestrian recall')
    fig.suptitle('Measured held-out curves · dots: thresholds selected at source FPPI ≤ 1')
    fig.tight_layout(); fig.savefig(DEST / 'recall_fppi.png'); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    arms = [arm for arm in data['arms'] if data['arms'][arm]['operating_points']['source_fppi_1']['status'] == 'FEASIBLE']
    x = np.arange(len(arms))
    recall, removable, unmatched, ceiling_part, threshold_part = [], [], [], [], []
    for arm in arms:
        record = data['arms'][arm]
        night = record['operating_points']['source_fppi_1']['conditions']['night']
        clear = record['operating_points']['source_fppi_1']['conditions']['clear_day']
        mn = record['strata']['night']['ceiling']['recall']
        mc = record['strata']['clear_day']['ceiling']['recall']
        recall.append(night['recall']); removable.append(mn-night['recall']); unmatched.append(1-mn)
        ceiling_part.append(mc-mn); threshold_part.append((mn-night['recall'])-(mc-clear['recall']))
    axes[0].bar(x, recall, label='Recalled', color='#497d9b')
    axes[0].bar(x, removable, bottom=recall, label='Threshold-removable miss', color='#e9b25d')
    axes[0].bar(x, unmatched, bottom=np.array(recall)+removable, label='No matched candidate', color='#a6a9ad')
    axes[0].set(ylim=(0, 1), ylabel='Share of night pedestrian GT', title='Absolute night outcomes')
    axes[1].bar(x-.17, ceiling_part, width=.34, label='Ceiling difference', color='#a6a9ad')
    axes[1].bar(x+.17, threshold_part, width=.34, label='Threshold-miss difference', color='#e9b25d')
    axes[1].axhline(0, color='#555555', lw=.7)
    axes[1].set(ylabel='Signed recall difference', title='Clear-day minus night loss components')
    for ax in axes:
        ax.set_xticks(x, arms); ax.legend(fontsize=8); ax.grid(axis='y', alpha=.15)
    fig.suptitle('Source FPPI ≤ 1 policy · candidate ceiling depends on native query/top-k policy')
    fig.tight_layout(); fig.savefig(DEST / 'miss_split.png'); plt.close(fig)


if __name__ == '__main__':
    main()
