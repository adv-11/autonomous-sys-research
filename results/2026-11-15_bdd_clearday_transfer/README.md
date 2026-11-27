# YOLO11s BDD100K clear-day transfer study: public aggregate outputs

Aggregate evidence for [the YOLO11s transfer report](../../docs/research/2026-11-15_bdd_clearday_transfer.md)
and the [threshold-transfer synthesis](../../docs/research/2026-11-23_threshold_transfer_synthesis.md).
Published with my permission (2026-11-27). Curated by Claude Opus from the private run folder
`outputs/bdd_transfer_20261115/`. The files are unchanged except that three Markdown tables were
re-encoded from Windows-1252 to UTF-8. The runs were executed on Colab, so the `/content/...` paths
in `args.yaml` are Colab paths.

Arms: **A** 640 px seed 0 (primary), **B** 1280 px seed 0, **C** 640 px seed 1, **B2** 1280 px seed 1 (stage 2).

| Path | Contents |
|---|---|
| `tables_*.md`, `tables_fix.json` | Rendered result tables (final, per arm, remedies, ACDC, B2) |
| `eval/<arm>.json`, `_h32`, `_low` | Per-condition ceilings, height-bin ceilings, operating points and decompositions: all heights, height ≥ 32 px, low recall targets |
| `eval/matched_*.json` | Matched clear-day FPPI comparisons and paired arm differences (amendment 3) |
| `eval/remedies_*.json`, `sensitivity_F1.json` | Remedy analyses (proxy and night-calibration thresholds) and F1 sensitivity |
| `stage2/eval/` | B2 seed replicate, four-arm matched comparison, ACDC panel |
| `runs/<arm>/results.csv`, `updates.jsonl`, `args.yaml` | Per-epoch Ultralytics metrics, update counts and AMP skips, training arguments |
| `preds/*.npz.json`, `stage2/preds/*.json` | Inference metadata: image and candidate counts, weight and output SHA-256 |
| `pilot/` | Throughput pilot results (640 / 1280 px) |
| `stage2/*_summary.json` | Stage-2 setup and NightOwls fetch counts |

`.txt` files next to the JSON are the human-readable printouts from the same evaluator runs.

**Not published:** checkpoints (`last.pt`), prediction arrays (`*.npz`), ground truth, manifests and
labels (`private/`), the vendored Python environment, a synthetic-data evaluator test (`synthetic/`,
`eval/remedies_smoke.json`), and pilot and handoff logs. A pilot log contained an image ID, and the
handoff note contained local paths. Every published file was scanned for BDD image IDs, image file
names, box fields, local home paths, tokens and email addresses, with no matches. The longest list in
any JSON is a 160-point aggregate curve.

Other studies: the NightOwls evaluation aggregates are already in
`docs/research/2026-11-23_nightowls_evaluation/`, and the seed-miss diagnosis aggregates were published in
PR #19. Its private `*_matches.json` files are per-object and stay private. The early Colab
studies (`outputs/colab/`, 2026-11-10 to 11-13) and the failed Colab RT-DETR allocation records
(`outputs/rtdetr_transfer_20261123/`, which contain account balance details) are not included.
