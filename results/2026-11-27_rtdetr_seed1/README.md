# RT-DETRv2-R18 seed-1 replicate: public aggregate outputs

These files are the aggregate evidence for [the seed-1 report](../../docs/research/2026-11-28_rtdetr_seed1_results.md).
I gave permission to publish them on 2026-11-27. Claude Opus curated them from the private folder
`outputs/local_rtdetr_seed1_20261127/`, replacing local home paths with `<home>`.
The layout matches [`results/2026-11-26_local_rtdetr/`](../2026-11-26_local_rtdetr/README.md).

| File | Contents |
|---|---|
| `results.json` | Per-arm ceilings, operating points, decompositions with intervals, paired seed and arm contrasts, the pre-declared readout, and the seed-0 reproduction check |
| `*_curve.npz` | Aggregate operating curves per arm and population |
| `<arm>/epochs.jsonl`, `<arm>_train.log` | Per-epoch loss means, update counts, native training log |
| `<arm>_summary.json`, `<arm>/progress.json`, `<arm>_inference.json` | Completion, timings, memory, checkpoint and chunk SHA-256 |
| `<arm>_recipe.yml`, `<arm>/resolved_config.json`, `<arm>/initialization.json` | Exact recipes and initialization |
| `study_start.json`, `study_events.json`, `study_complete.json` | Run rules, every gate decision and stage exit, terminal receipt |

**Not published:** the checkpoints, per-image detections (`*_pedestrian.npz` and the native chunks),
and the dataset images and labels.
