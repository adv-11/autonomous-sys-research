# Existing local detection assets

**Inventory: coordinator inspection, 2026-11-05.** My earlier detection project, `det-eval-2d`, contains reusable local assets. Its checked source commit is `39c6f6d87df7775c3bf1dd36b8de3990d6a4b217`, with a clean Git working tree at inspection. The [example configuration](../configs/local_assets.example.json) locates it as a sibling directory. Do not copy datasets, checkpoints or the virtual environment into Git, and do not change the earlier project while reusing its files.

| Asset | Observed local inventory | Appropriate next use |
|---|---|---|
| COCO val2017 | 5,000 JPG images; annotation JSON contains 5,000 image records and 36,781 annotation records | Converter and evaluator development; separate human-category diagnostics |
| KITTI object training release | 7,481 PNG images and 7,481 label files | Pipeline smoke checks and optional later distance analysis after policy audit |
| Earlier derived KITTI validation JSON | 3,769 image records, 37,029 annotation records, including encoded ignore regions | Audit native ignore semantics before adapting; records are not necessarily distinct physical objects |
| Cached predictions | 25 compressed JSON files for COCO/KITTI runs | Diagnostic replay after explicit schema, vocabulary and candidate-policy checks |
| Weights | YOLO11s/m, RT-DETR-L, YOLO-World and other cached checkpoints | Reuse identified artifacts where relevant; RT-DETR-L is not the proposed RT-DETRv2-S/R18 baseline |
| Existing environment | Python 3.12.14; torch 2.11.0+cu128; torchvision 0.26.0+cu128; Ultralytics 8.4.197 | Versions and CUDA detection verified by imports, not a full model training/evaluation smoke test |

`torch.cuda.is_available()` returned true and reported the RTX 5060 Laptop GPU. This is a useful prerequisite check, not evidence that every proposed model or operation runs correctly. No packages were installed or changed during inventory.

## Identified artifacts

| Relative path under the earlier project | SHA-256 |
|---|---|
| `datasets/coco/annotations/instances_val2017.json` | `e8c7f7908f1d7278341fae127d0da654f102f11bd7b21d8aeefa635b8c810b6f` |
| `datasets/kitti/coco_gt_val.json` | `33b1806f97d8ad77d973de6184908ba36b245805c1b8c6e778c0e4be62996a63` |
| `weights/yolo11s.pt` | `85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5` |
| `weights/rtdetr-l.pt` | `6de60b10d4bc566f00cda0f5b4d64afe4b66d48dc9695d2171effb7859d8e73f` |

These hashes identify inspected local bytes; they do not prove dataset licensing, official checkpoint origin, complete image integrity, or correct annotation conversion.

## Cached-output limitations

The earlier inference code saves `{meta, detections}`. Each detection is `[image_id, x1, y1, x2, y2, score, vocabulary_index]`. The metadata includes all evaluated image IDs, vocabulary, detector policy and environment. Preserve empty images and use the declared vocabulary, rather than guessing COCO category IDs from the zero-based label index.

The code uses a 0.001 score floor and at most 300 retained raw detections per image; old AP evaluation applies a separate 100-detection budget after mapping. Coordinates are rounded to two decimals and scores to five. Any replayed candidate ceiling is therefore conditional on this censored, rounded cache. Preserve whole tie groups and record the cache policy. The scalar scores cannot reconstruct full-vector OCE. Earlier KITTI fine-tuned runs and previously inspected validation data are development/diagnostic assets, not a fresh confirmatory test.

KITTI's `DontCare`, neighbour-class and difficulty ignores have different matching semantics in the earlier evaluator. Do not flatten them into one generic crowd rule and claim official KITTI scoring. Preserve native flags and require an explicitly declared research policy.

## Remaining gaps

No BDD100K or ACDC directories were found in this inspected project. Their acquisition, annotation policies, condition/group inventories and final split manifests remain pending. Existing COCO/KITTI results do not answer night/weather threshold transfer. G0 remains pending.
