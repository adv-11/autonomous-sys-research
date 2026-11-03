# GPT primary-source audit

**Audit date:** 2026-11-03. **Attribution:** GPT independently inspected the linked public sources; no Claude findings were inspected. Full text below means versioned HTML methods and relevant appendices, not a claim that every equation was reproduced. No datasets, weights, or training packages were acquired. Repository visibility is public; research gates remain evidence dependent.

## 1. The weather study: identity verified, reproduction incomplete

**Source:** Mahin, Das, Islam, Mahmood, Mridha and Hossen, *How Reliable Are Object Detection Models Beyond Clear Weather? A Deployment-Oriented Robustness Study for Autonomous Driving*, [2611.00071v1 metadata](https://arxiv.org/abs/2611.00071v1), [full text](https://arxiv.org/html/2611.00071v1), §§III–IV, Tables II and XI. **Access:** full-text HTML; no released implementation identified in the inspected article.

The models are YOLOv8n, YOLOv8m, **YOLO11m**, Faster R-CNN and DETR, not RT-DETR. The source reports clear-day BDD100K training and ACDC evaluation; ECE uses equal-width bins and class correctness plus IoU **> 0.50**. Reported DETR ECE is 0.4383 clear and 0.5790 night; these are published values, not project results.

**Limitations:** bin count, duplicate matching, candidate score cutoff, DETR backbone/checkpoint, ACDC box provenance and exact split identities remain unresolved. Text says 768 pixels where applicable; the DETR table says default preprocessing. The displayed October submission date also conflicts with the November identifier prefix; retain the identifier and flag the date rather than silently repairing it. An all-query ECE explanation is **unverified**. Reproduction needs artifacts beyond this article.

## 2. Park et al.: OCE is version sensitive

**Source:** Young-Jin Park, Carson Sobolewski and Navid Azizan, *Uncertainty Quantification in Detection Transformers: Object-Level Calibration and Image-Level Reliability*, [2412.01782v4](https://arxiv.org/abs/2412.01782v4), revised 2026-04-20; [full text](https://arxiv.org/html/2412.01782v4), §§IV–V and Appendix D. [Publisher record](https://xplorestaging.ieee.org/document/11489530/) identifies TPAMI, DOI 10.1109/TPAMI.2026.3686715. **Access:** arXiv full text; publisher metadata/excerpt.

The paper studies foreground-specialist versus suppressed queries and jointly evaluates model and postprocessing. Its older detector set cannot establish modern RT-DETR/YOLO26 behavior.

**Implementation evidence:** [OCE code, `fa2a64f`](https://github.com/azizanlab/uq-detr/blob/fa2a64fad0e6a3dfbc10c3937bd298aeeac24a9e/src/uq_detr/metrics/oce.py). The paper calls its two-IoU aggregate an average but prints a sum; this code averages. Full class scores and its scalar-score approximation differ. **GPT deduction:** predictions overlapping no ground truth cannot affect this object-indexed score, so FPPI remains necessary. This is not a universal proper measure of every detection failure. Pin the metric variant before comparisons.

## 3. Kuzucu et al.: stronger calibration protocol, different operating objective

**Source:** Selim Kuzucu, Kemal Oksuz, Jonathan Sadeghi and Puneet K. Dokania, *On Calibration of Object Detectors: Pitfalls, Evaluation and Baselines*, [2405.20459v1](https://arxiv.org/abs/2405.20459v1), 2024-05-30; [full text](https://arxiv.org/html/2405.20459v1), §§3–4 and Appendix C; [ECCV 2024 record](https://www.ecva.net/papers/eccv_2024/papers_ECCV/html/3148_ECCV_2024_paper.php). **Access:** full arXiv HTML; venue abstract. [Official code snapshot](https://github.com/fiveai/detection_calibration/tree/bf59c92f5416ac4b66a7c2c67b44487777ff2ea4).

This work improves **LaECE₀/LaACE₀**; it did not originate all LaECE formulations. Its operating threshold optimizes LRP, whereas this project's proposed primary threshold targets recall. Classwise Platt/isotonic calibration and model-dependent thresholding require explicit selection rules. Table 2 demonstrates harm from a mismatched calibration dataset; that is narrower than a theorem that every source calibrator fails under every target shift.

**Limitations:** neither the article's calibration gains nor LRP-optimal thresholds demonstrate improved recall transfer after globally monotone recalibration and recall threshold reselection. That question requires the invariance analysis in [protocol.md](protocol.md).

## 4. YOLO11: inspect score construction, not just the family name

**Sources:** [official model documentation](https://docs.ultralytics.com/models/yolo11), release 2024-09-27; pinned [architecture YAML](https://github.com/ultralytics/ultralytics/blob/73c60b7edf7b02b90c07157c87d05957fbfdd68f/ultralytics/cfg/models/11/yolo11.yaml), [loss](https://github.com/ultralytics/ultralytics/blob/73c60b7edf7b02b90c07157c87d05957fbfdd68f/ultralytics/utils/loss.py) and [assignment](https://github.com/ultralytics/ultralytics/blob/73c60b7edf7b02b90c07157c87d05957fbfdd68f/ultralytics/utils/tal.py). **Access:** official docs and implementation; no separate YOLO11 paper used.

The small detection variant is `yolo11s`, with P3–P5 outputs. The inspected loss uses BCE against task-aligned targets, with assignment combining classification and localization. Therefore, “YOLO confidence is pure class probability, DETR confidence is quality aware” is an inadequate contrast. The normal detection route uses NMS; [pinned NMS code](https://github.com/ultralytics/ultralytics/blob/73c60b7edf7b02b90c07157c87d05957fbfdd68f/ultralytics/utils/nms.py) exposes candidate floors, caps and class policy.

**Limitations:** documentation is mutable, implementation is not a statistical calibration guarantee, and no weights were inspected. The observed latest package release was `v8.4.201`; the source SHA above is a separately identified snapshot, not asserted to equal that release tag.

## 5. YOLO26: official and third-party sources disagree on chronology

**Sources:** [official docs](https://docs.ultralytics.com/models/yolo26); Jocher et al., [2606.03748v1 full text](https://arxiv.org/html/2606.03748v1), 2026-06-02, §§3 and S3; [pinned model YAML](https://github.com/ultralytics/ultralytics/blob/73c60b7edf7b02b90c07157c87d05957fbfdd68f/ultralytics/cfg/models/26/yolo26.yaml). **Access:** official full-text paper, docs and code.

Official docs identify a January 2026 release. The default one-to-one inference route is NMS free, with an optional one-to-many route; DFL is removed. The YAML records `end2end: True`, `reg_max: 1`. The paper's training recipe includes Objects365 pretraining: a checkpoint called COCO trained need not have COCO-only exposure.

**Identity correction:** Sapkota et al., [2509.25164v5 full text](https://arxiv.org/html/2509.25164v5), revised 2026-03-16, is a **third-party analysis**, not the official model paper. Its September 2025 release assertion conflicts with official docs. Use official implementation evidence and record the disagreement.

**Limitations:** `yolo26s.pt` is a proposed artifact name, not a downloaded/hash-verified checkpoint. O2O and O2M branches must be distinguished in every run.

## 6. RT-DETR and RT-DETRv2: specify the actual variant

**Sources:** Zhao et al., [2304.08069v3 full text](https://arxiv.org/html/2304.08069v3), 2024-04-03, CVPR 2024; Lv et al., [2407.17140v1 full text](https://arxiv.org/html/2407.17140v1), 2024-07-24; [official repository](https://github.com/lyuwenyu/RT-DETR/tree/df2a96c8c3a098567a1149bf0248da6efe6d495d). **Access:** both HTML papers and repository.

`RT-DETR-R18` and `RT-DETRv2-S` are distinct recipes, not interchangeable spellings. Proposed primary baseline: [v2 R18 120-epoch config](https://github.com/lyuwenyu/RT-DETR/blob/df2a96c8c3a098567a1149bf0248da6efe6d495d/rtdetrv2_pytorch/configs/rtdetrv2/rtdetrv2_r18vd_120e_coco.yml), whose [included settings](https://github.com/lyuwenyu/RT-DETR/blob/df2a96c8c3a098567a1149bf0248da6efe6d495d/rtdetrv2_pytorch/configs/rtdetrv2/include/rtdetrv2_r50vd.yml) select VFL. The [postprocessor](https://github.com/lyuwenyu/RT-DETR/blob/df2a96c8c3a098567a1149bf0248da6efe6d495d/rtdetrv2_pytorch/src/zoo/rtdetr/rtdetr_postprocessor.py) takes sigmoid top-k over flattened query-class pairs, potentially retaining multiple classes from one query. NMS free does not mean selection free.

**Limitations:** v2's optional discrete sampling changes the pipeline. Ultralytics `rtdetr-l` is a different implementation/scale and cannot silently replace this baseline. Published COCO/T4 speed is not an RTX 5060 memory or throughput measurement.

## 7. DEIM: training framework, not a standalone backbone

**Sources:** Huang et al., [2412.04234v3 full text](https://arxiv.org/html/2412.04234v3), 2025-03-26, §§3–4 and supplement; [official repository](https://github.com/Intellindust-AI-Lab/DEIM/tree/09d35d53d39ee3145a1e61e3a989b28b9468d1dd), redirected from `ShihuaHuang95/DEIM`; [small config](https://github.com/Intellindust-AI-Lab/DEIM/blob/09d35d53d39ee3145a1e61e3a989b28b9468d1dd/configs/deim_dfine/deim_hgnetv2_s_coco.yml). **Access:** full text and code/config.

Dense O2O supervision and matchability-aware loss (MAL) modify training of RT-DETR/D-FINE. The paper compares MAL/VFL loss behavior and qualitative duplicate/false-positive cases; these do not establish probability calibration under night shift. Proposed extension: DEIM-D-FINE-S, with the inherited D-FINE-S baseline if isolating DEIM is affordable.

**Limitations:** the small config specifies 132 epochs; equalizing every model to an arbitrary short schedule changes the estimand. [Requirements](https://github.com/Intellindust-AI-Lab/DEIM/blob/09d35d53d39ee3145a1e61e3a989b28b9468d1dd/requirements.txt) listing torch/torchvision/faster-coco-eval is insufficient proof that every dependency works on Windows/Blackwell. The inspected [license](https://github.com/Intellindust-AI-Lab/DEIM/blob/09d35d53d39ee3145a1e61e3a989b28b9468d1dd/LICENSE) is Apache 2.0; package/checkpoint rights still require artifact-specific review.

## 8. BDD100K: class names and labels need artifact-level checks

**Sources:** pinned [label format](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/doc/source/format.rst), [data licensing documentation](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/doc/source/license.rst). **Access:** official code documentation; the data website timed out and a documentation endpoint was inaccessible.

Detection categories explicitly separate pedestrian, rider, bicycle and motorcycle. COCO `person` does not supply a pedestrian/rider distinction. A string rename cannot harmonize these populations. Code licensing and data licensing are separately documented.

**Limitations:** no annotation archives were inspected, so category aliases, condition tags, public label availability, sequence metadata and slice counts remain unverified for the eventual artifact. Do not assume access to official test labels; reserve an evaluation partition from accessible labels. Proposed source is strictly daytime AND clear, pending actual metadata inspection. Undefined attributes stay separate.

## 9. ACDC: use the extended annotation version deliberately

**Source:** Sakaridis et al., [2104.13395v5 metadata](https://arxiv.org/abs/2104.13395v5), revised 2025-11-12; [full text](https://arxiv.org/html/2104.13395v5), §§III and IV. **Access:** full text; [dataset website](https://acdc.vision.ee.ethz.ch/) returned only a JavaScript shell.

The extended TPAMI version describes panoptic/instance annotations and detection, rather than only the original ICCV 2021 semantic task. It reports 4,006 adverse images and 1,503 annotated normal counterparts; these are **source totals, not usable project slice counts**. Corresponding views revisit scenes, rather than keeping the same pedestrians fixed. Recording separation is relevant to uncertainty and leakage.

**Limitations:** exact download version, downloadable boxes versus mask-derived boxes, visible/amodal extent, uncertain-region handling and terms remain unchecked. A mask-tight person box and BDD detection box can differ systematically. BDD→ACDC combines weather, geography, acquisition and label-policy shift. Neither paired views nor harmonized class names make it a causal weather intervention.

## Feasibility and novelty boundary

The [PyTorch 2.7 release](https://pytorch.org/blog/pytorch-2-7/) introduced Blackwell/CUDA 12.8 support; the [2.12 release](https://pytorch.org/blog/pytorch-2-12-release-blog/) changes the binary matrix and recommends CUDA 13+ for newer GPUs. Thus “torch ≥2.7 cu128” is not an adequate timeless environment pin. No package was installed. Actual driver, OS, wheel, torchvision pairing, forward/backward, evaluation and peak-memory checks are pending.

GPT audit searched the three named identities, official implementations, and combinations of object detection, calibration, threshold, recall, pedestrian, night and domain shift. The inspected work motivates a bounded threshold-transfer study; it does **not** establish priority. Adjacent work includes [Self-aware Object Detection](https://github.com/fiveai/saod), whose official repository describes joint calibration, domain-shift and rejection evaluation. “Nobody has measured this” is unsupported. All repository SHAs above were obtained through GitHub's public commit/tree APIs on the audit date; none was executed.
