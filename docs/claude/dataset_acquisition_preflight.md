# BDD100K and ACDC acquisition preflight — Claude source check

**Author:** Claude (Opus 5.5). **Access date:** 2026-11-05 (pages rendered 2026-11-06 01:13 UTC). No dataset was downloaded, no account was created or used, and no terms were accepted. My acceptance of either license remains a later decision. Sizes below are publisher-stated, not measured.

## BDD100K

| Item | Evidence |
|---|---|
| Primary sources | [`download.rst`](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/doc/source/download.rst), [`license.rst`](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/doc/source/license.rst), [`format.rst`](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/doc/source/format.rst), [`det.toml`](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/bdd100k/configs/det.toml), all at `9ac17c6`. That commit (2024-03-09) is still `master` HEAD. |
| Stated route | The docs say data is at `https://dl.cv.ethz.ch/bdd100k/data/` and downloading implies agreement to the BDD100K license. The license text refers to data "downloaded from https://bdd-data.berkeley.edu/". |
| Reachability today | `dl.cv.ethz.ch` and `doc.bdd100k.com`: DNS resolution failed from this machine. `bdd-data.berkeley.edu`: TLS certificate name mismatch. **The current working download route and whether registration is required are unverified.** |
| License | UC Regents license: use, copy, modify and distribute for educational, research and not-for-profit purposes. Commercial rights are limited to BDD/BAIR Commons members. |
| Archives needed (stated) | 100K images 5.3 GB (md5 `5a0359c86a0b8713adab1eee9a3041cb`, `images/100k/{train,val,test}`). Detection 2020 labels 53 MB (md5 `b86a3e1b7edbcad421b7dad2b3987c94`, tree `labels/det_20/det_{train,val}.json`). Legacy 2018 labels 107 MB (md5 `e21be3e7d6a07ee439faf61e769667e4`) carry the video attributes. |
| Inconsistency | The Detection 2020 prose says "validation and testing labels", but the listed tree has only `det_train.json`/`det_val.json`. Test-label availability remains unresolved, consistent with GPT's earlier finding. |
| Attributes | `format.rst` lists `weather`, `scene`, `timeofday` frame attributes, object `occluded`/`truncated`, and `crowd`/`ignore` semantics. Whether `det_20` JSON carries the frame attributes, or only the 2018 labels do, is **unknown until inspected**. |
| Ontology | `det.toml`: `pedestrian` and `rider` are separate. `name_mapping` maps `person → pedestrian`, and `ignored_mapping` maps `other person → pedestrian`. These are evaluator config evidence, not project policy. |
| Groups | Each 100K image is the frame at the 10th second of one video, so the image name identifies a video. **Shared trip, driver or route across videos is not established**. Video ≠ verified independent group until evidence exists. The 3.9 GB GPS/IMU info archive might support route-level grouping, but this is unverified. |

## ACDC (extended version)

| Item | Evidence |
|---|---|
| Primary sources | [Download page](https://acdc.vision.ee.ethz.ch/download) and [license](https://acdc.vision.ee.ethz.ch/license). Both are JavaScript-rendered and were read through a headless browser on 2026-11-06 UTC. Paper: [arXiv 2104.13395v5](https://arxiv.org/abs/2104.13395v5) (already audited in [`source_audit.md`](source_audit.md)). |
| Account | The site has a Login / Sign Up page (`/login`, `/register`). The download page listed packages as "Available" without logging in. Whether the files themselves require a logged-in session was **not tested**. |
| License | ETH Zurich research-use agreement. Non-commercial research only. The dataset must be obtained directly from ETH. No redistribution of the dataset or modified versions; only abstract derivatives such as models are allowed. Citation is required. No military use. Swiss law applies. |
| Listed packages (stated sizes) | `rgb_anon_trainvaltest.zip` 15.6 GB: 4,006 adverse images and 4,006 normal-condition references. `gt_detection_trainval.zip` 4 MB: bounding boxes, train+val, 2,006 images. `gt_panoptic_trainval.zip` 42 MB. `gt_trainval.zip` 127 MB: semantic and uncertainty-aware. `gt_detection_trainval_ref.zip` 1 MB: half of train_ref/val_ref, 1,003 normal images. `gt_panoptic_trainval_ref.zip` 22 MB. `gt_trainval_ref.zip` 55 MB. MD5 values sit behind a JavaScript link and were not recorded. |
| Instance artifact | No package is named "instance". The extended paper describes COCO-format instances. Whether these ship as `gt_detection*` (boxes) and/or `gt_panoptic*` (segments), and whether boxes are amodal or mask-tight, is **unknown**. Crowd/group fields and the JSON representation of the invalid mask are also unknown. |
| Internal reconciliation | 2,006 = 400×4 train + 100×3 + 106 night val. 1,003 = 800 + 203 reference images, matching the paper. Test labels are withheld. |

## Remaining prerequisites before BDD/ACDC work (and G0)

1. Confirm a reachable official BDD100K route and its registration requirement. I accept the BDD and ETH licenses myself; no AI accepts terms.
2. Download, hash and record exact archives: BDD 100K images plus `det_20`, plus 2018 labels if needed for attributes. For ACDC: `rgb_anon`, `gt_detection*`, `gt_panoptic*`, with MD5/SHA-256 on disk.
3. Inspect the real JSON schemas: BDD attribute location, `crowd`/`ignore`/`other person` records; ACDC bbox extent, crowd and invalid-mask representation. Then extend `data.py` with converters that preserve native flags and fail closed, and agree any contract change with GPT.
4. Establish verified group IDs: BDD trip/route evidence, ACDC normal/adverse correspondence kept in one group. Then build grouped role manifests and pass `check_roles(..., mode="held_out")`.
5. Count images, eligible objects, empty images, ignored objects and independent groups per condition cell before allocation decisions.
6. The remaining G0 items in [the protocol](../gpt/protocol.md#7-minimal-evidence-needed-next): pinned environments, checkpoint hashes, and an actual RTX 5060 forward/backward plus evaluation smoke test.

Nothing in this note, the COCO/KITTI inventory or the cache replay passes G0.
