# Local RT-DETRv2-R18 study: public aggregate outputs

Aggregate evidence for [the measured report](../../docs/research/2026-11-26_local_rtdetr_results.md).
Published with my permission (2026-11-27). Curated by Claude Opus from the private run folder
`outputs/local_rtdetr_20261126/`. Local home paths are replaced by `<home>`.

| File | Contents |
|---|---|
| `results.json` | Per-condition ceilings, height-bin ceilings, operating points, decompositions, paired bootstrap contrasts |
| `*_curve.npz` | Aggregate operating curves (`thresholds`, `recall`, `fppi`) per arm and population |
| `<arm>/epochs.jsonl` | True per-epoch training-loss means, update counts, AMP skips |
| `<arm>_train.log` | Native training log (rolling losses every 25 batches) |
| `<arm>_summary.json`, `<arm>/progress.json` | Training completion, seconds, peak GPU memory |
| `<arm>_inference.json` | Inference completion, candidate counts, chunk and checkpoint SHA-256 |
| `<arm>_recipe.yml`, `<arm>/resolved_config.json` | Exact training recipes |
| `*_data.json`, `preparation.json` | Dataset sizes and hashes, package versions |
| `study_complete.json`, `study_study_b16_exit.json` | Terminal receipts (exit 0, PASS) |

**Not published:** checkpoints (`last.pth`, ~308 MB each), dataset images and labels, image manifests,
per-image detections and boxes (`*_pedestrian.npz`, native chunks), and process records.
These stay private under the dataset licences and the project rule against committing images,
boxes or per-image IDs.
