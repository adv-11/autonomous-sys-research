# Phase 0 source audit (Claude audit)

**Author of this audit:** Claude (Opus 5.5), working as an independent AI research agent for my project. Every "read" and "verified" below means Claude fetched and read the source. I have not yet re-read these sources myself.
**Revision status:** independent initial audit in `4af4f810f36851b462298a9b473dd421f30e6ba3`; peer-revised after Claude reviewed GPT commit `80519fcee2c99d134a5a6a89559f743772c2ffb8` (see the [addendum](#4-peer-review-addendum-2026-11-03) and [discussion record](discussion_with_gpt.md)). Initial findings are kept; corrections are marked.
**Access date:** 2026-11-03. arxiv.org, export.arxiv.org, raw.githubusercontent.com, api.github.com, the OpenReview API and docs.ultralytics.com were reachable. doc.bdd100k.com failed DNS resolution. acdc.vision.ee.ethz.ch is a JavaScript single-page app, so its content could not be read without a browser.
**Method (Claude):** Claude fetched each arXiv abstract page for the title, authors, version history and comments, then downloaded the versioned PDF to a scratch directory outside the repository (not committed). Claude extracted the text with `pdftotext` and searched it for the claims in `RESEARCH_PLAN.md`. Quotes are short and taken verbatim from the extracted text.

Access levels:
- **FT**: full text read (the relevant sections of the versioned PDF).
- **ABS**: arXiv abstract page or metadata only.
- **REPO**: official code repository README or configuration.
- **DOC**: official documentation page.
- **SEC**: secondary source only.
- **NR**: not reached.

## 1. Survey rows (10 primary sources)

| # | Paper (verified identity, version read) | Venue status (evidence) | Claim relevant to my project | Baseline / data | Metric | Code | Access |
|---|---|---|---|---|---|---|---|
| 1 | **arXiv 2611.00071v1**, Mahin, Das, Islam, Mahmood, Mridha, Hossen, "How Reliable Are Object Detection Models Beyond Clear Weather? A Deployment-Oriented Robustness Study for Autonomous Driving" (v1, displayed submission 15 Oct 2026 despite a November-style `2611` identifier; only version). sha256 in §4 | IEEE-journal template with placeholder dates ("Manuscript received MM DD, YYYY"); publication/acceptance status not verified from the inspected sources | Train on clear-day images, test on adverse conditions. YOLO models show ECE ≈ 0.012–0.021. DETR ECE rises from 0.4383 (clear) to 0.5790 (night). Night causes the largest mAP50 drop (up to 62.90%, DETR) | YOLOv8n, YOLOv8m, YOLO11m, Faster R-CNN and DETR (Carion et al.). 100 epochs, 768 px, AdamW at lr 1e-3, seed 42, RTX A4000. Train on BDD100K clear-daytime; test on ACDC fog, rain, snow and night. Classes: car, bus, truck, person | mAP50, precision, recall, Drop %, WRI, ECE with M equal-width bins | No code link found in the inspected article or metadata (not an exhaustive release search) | FT |
| 2 | **arXiv 2412.01782v4**, Park, Sobolewski, Azizan, "Uncertainty Quantification in Detection Transformers: Object-Level Calibration and Image-Level Reliability" (v1 Dec 2024 → v4 20 Apr 2026). | The v4 PDF header reads "IEEE TRANS. ON PATTERN ANALYSIS AND MACHINE INTELLIGENCE", and the repo badge reads "TPAMI 2026". No DOI checked | DETRs learn a "specialist strategy": one query per object is calibrated, while the rest are suppressed to near-zero confidence "even when maintaining accurate localization". AP prefers a threshold near 0, and D-ECE prefers a threshold near 1. Proposes OCE | UP-DETR, D-DETR, Cal-DETR, DINO, Faster R-CNN, YOLOv3. COCO, with Cityscapes and Foggy Cityscapes as OOD sets | OCE (per-GT Brier score at IoU 0.5 and 0.75), D-ECE, LA-ECE0, AP, LRP | `azizanlab/uq-detr` | FT + REPO |
| 3 | **arXiv 2405.20459v1**, Kuzucu, Oksuz, Sadeghi, Dokania, "On Calibration of Object Detectors: Pitfalls, Evaluation and Baselines" (v1 only). | ECCV 2024 (repo README: "accepted to ECCV 2024 for an oral presentation"; OpenReview/Crossref: "ECCV (21) 2024") | Calibration should be evaluated on a thresholded, model-specific operating set. D-ECE-style evaluation (a 0.30 threshold for calibration but top-100 detections for AP) is inconsistent. Platt scaling and isotonic regression beat train-time calibration methods. Operating thresholds chosen on domain-shifted validation sets "do not generalize" (shifted→ID direction). Post-hoc calibrators are "slightly worse" in LaECE0 under the large natural shift of Obj45K | D-DETR and others; COCO, Cityscapes, LVIS, with -C corruption variants, Foggy Cityscapes and Obj45K | LaECE0, LaACE0, LRP, D-ECE | `fiveai/detection_calibration` | FT + REPO |
| 4 | **arXiv 2606.03748v1**, Jocher, Qiu, Liu, Lyu, Akyon, Kalfaoglu, "Ultralytics YOLO26: Unified Real-Time End-to-End Vision Models" (2 Jun 2026). | Preprint; this is the official Ultralytics report | Dual head built on YOLO11. The one-to-many branch uses TAL topk=10 plus NMS. The one-to-one branch uses TAL topk=7 and topk2=1, outputs ≤300 detections and needs no NMS. Progressive Loss decays the one-to-many weight from 0.8 to 0.1. DFL removed; STAL; MuSGD | COCO | AP, latency | `ultralytics` (AGPL-3.0, per docs) | FT + DOC |
| 5 | **arXiv 2509.25164v5**, Sapkota, Cheppally, Sharda, Karkee (Cornell / Kansas State), "YOLO26: Key Architectural Enhancements and Performance Benchmarking…" (v1 Sep 2025 → v5 Mar 2026). | Preprint. **A third-party review, not the Ultralytics paper** | Restates Ultralytics features: no DFL, NMS-free inference, ProgLoss, STAL, MuSGD. Its benchmark figures are sourced from Ultralytics | Re-reported COCO numbers and edge-device latency | mAP, latency | n/a | FT |
| 6 | **arXiv 2609.21822v1**, Penquitt, Klees, van Betteray, Jashnieh, Stehr, Rottmann, Schmarje, "Object Detection Benchmarks are Incomplete: The Role of Label Errors and Annotation Uncertainty" (18 Sep 2026). | **NeurIPS 2026 not verified.** The PDF uses an IEEE-style author block, and OpenReview search returned no match | Re-annotation finds up to +60% objects on KITTI and +40% on COCO, mostly small, occluded or dense instances. Missing annotations are the main error type. Fine-tuned models degrade when scored against the validated labels. Isotonic regression beats Platt scaling for post-hoc ECE | YOLOv8, RT-DETR, Faster R-CNN, plus open-vocabulary detectors. COCO, VOC, Cityscapes, KITTI | AP, ECE, soft-label distances | `JonathanKlees/Uncertainty-aware-Object-Detection` (annotations under CC BY-SA 4.0) | FT + REPO |
| 7 | **arXiv 2104.13395v5**, Sakaridis et al., "ACDC: The Adverse Conditions Dataset with Correspondences for Robust Semantic Driving Scene Perception" (v5, 12 Nov 2025). | T-PAMI 2025 (author-reported arXiv comment); extends ICCV 2021 | 4,006 adverse images. Each condition splits into 400 train / 100 val / 500 test (night: 106 val). **Test annotations are withheld.** The extended version adds instance annotations made by converting the semantic masks to polygons, which annotators then merged or split into instances and exported to COCO format. It also adds 1,503 annotated normal-condition reference images (800 train / 203 val public) and a Cityscapes→ACDC detection benchmark | Faster R-CNN and FCOS UDA methods | AP50, COCO AP | NR (the site is JavaScript-only) | FT |
| 8 | **arXiv 2304.08069v3**, Zhao et al., "DETRs Beat YOLOs on Real-time Object Detection" (RT-DETR, v3 Apr 2024). | CVPR 2024 (repo README: "accepted to CVPR 2024") | Uncertainty-minimal query selection (named "IoU-aware" in earlier versions) selects the top K=300 encoder features. **The v3 text does not name varifocal loss**; VFL use comes from DEIM's description and the code | COCO | AP, FPS | `lyuwenyu/RT-DETR` (Apache-2.0) | FT + REPO; VFL claim SEC |
| 9 | **arXiv 2410.13842v1** D-FINE (Peng et al.) and **arXiv 2412.04234v3** DEIM (Huang et al.) | D-FINE: ICLR 2025 Spotlight (OpenReview API). DEIM: CVPR 2025 (arXiv comment and README) | D-FINE: fine-grained distribution refinement plus GO-LSD self-distillation. DEIM: Dense O2O matching plus MAL, which "scales the penalty based on matchability". DEIM concedes that "YOLOv9-E outperforms D-FINE-L by approximately 1.4 AP on small objects" | COCO; DEIM also CrowdHuman | AP, AP_S | `Peterande/D-FINE`, `ShihuaHuang95/DEIM` (Apache-2.0) | FT + REPO |
| 10 | **arXiv 2611.00077v1**, Vinaykumar, Kamasani, "AegisBench: Auditing Aerial Search-and-Rescue Person Detection Under the Conditions It Is Deployed In" (displayed 17 Oct 2026; November-style identifier) | Preprint; workshop acceptance reported in GPT's metadata check is author-reported, not venue-verified | **Closest framing precedent found.** Confidence thresholds are "frozen on clean validation data as a fielded system would run" (F1-optimal on clean val). A 4.5-stop exposure loss drives recall to 0 for all three detectors; real night images find 2 of 759 people | Faster R-CNN, YOLOv11, RT-DETR. HERIDAL and SARD aerial data with synthetic physics-based corruptions | Recall at the frozen threshold, mAP | Paper names `Altis-2026/SentinelBench` (MIT); not opened | FT (threshold protocol sections) |

## 2. Claim ledger for `RESEARCH_PLAN.md`

| Plan claim | Claude audit verdict | Evidence |
|---|---|---|
| 2611.00071 is by "Mahin, Das et al., Oct 2026" | **Confirmed** | arXiv v1, 15 Oct 2026 |
| 2611.00071 uses BDD100K clear-day → ACDC fog/rain/snow/night; car, bus, truck, person; plain ECE | **Confirmed** | §II–III of the full text |
| "YOLO ECE < 0.03, DETR 0.44 → 0.58" | **Confirmed**: YOLO 0.0125–0.0214; DETR 0.4383 (clear) → 0.5790 (night) | Table XI |
| "Which YOLO version? Is RT-DETR included?" | YOLOv8n, YOLOv8m and YOLO11m. **No RT-DETR, D-FINE, DEIM or YOLO26.** "DETR" refers to Carion et al. [18] | §III-B |
| "How was ECE computed: all queries or thresholded?" | **Unresolved.** The text gives M equal-width bins, with "correct" meaning class match and IoU > 0.5. It states no score threshold, no top-k, no one-to-one GT matching or duplicate handling, and no value of M | Eq. (3) and its surrounding text |
| "ACDC box derivation; released code?" | **Not described; no code link found in inspected sources.** Also, Table I lists ACDC Rain = 1,661 images, but ACDC has 1,000 rain images in total and 500 with public labels. The source does not explain the discrepancy; its cause is unknown | Table I vs ACDC §3 |
| Kuzucu et al. is ECCV 2024, defines LaECE, and finds calibrators degrade under domain shift | **Partly confirmed.** ECCV 2024 holds. LaECE comes from earlier work [51]; Kuzucu proposes **LaECE0/LaACE0**. The degradation is a slight LaECE0 loss on Obj45K, not a general collapse | §3–6 |
| Park et al. 2412.01782 is TPAMI 2026 with code `uq-detr` | **Mostly confirmed** (PDF header and repo badge). The DOI was not checked | v4 PDF, repo |
| "YOLO26 (Ultralytics, Sept 2025; arXiv 2509.25164)" | **Corrected.** 2509.25164 is a third-party review. The official report is **2606.03748**. The docs currently say "released January 2026"; the review says September 2025 | arXiv metadata, docs |
| "YOLO26 is NMS-free, one-to-one, no DFL" | **Head-dependent.** Both heads are trained. The official report calls the one-to-one head "(default)", but the **current docs** say "Prediction and validation default to the one-to-many head… Use `nms=False` for NMS-free inference" | 2606.03748 §3, docs page |
| RT-DETR uses varifocal loss | **Secondary only.** DEIM states "In RT-DETR, VFL is employed". The RT-DETR v3 text does not name it | DEIM §2, RT-DETR v3 |
| DEIM claims MAL "corrects overconfident but inaccurate predictions" | **Wording not found.** The DEIM v3 full text never uses "overconfiden*" or "calibrat*". Its actual claim is that MAL penalizes confidence on low-IoU matches more sharply than VFL (Fig. 4). Its appendix shows D-FINE making "high-confidence duplicated predictions and false positives" | DEIM §3.3, appendix |
| DEIM concedes the YOLOv9-E small-object AP advantage | **Confirmed** | DEIM §4 |
| D-FINE is ICLR 2025 | **Confirmed** (Spotlight) | OpenReview API |
| Penquitt et al. is NeurIPS 2026; fine-tunes YOLOv8-L, RT-DETR and Faster R-CNN; compares isotonic calibration with soft labels | **Venue unverified.** The models and the isotonic vs soft-label comparison are confirmed; the "-L" size was not checked | Full text, appendix C |
| "No one has measured clear-day threshold transfer" | **Weakened.** AegisBench (2611.00077) freezes clean-val thresholds and measures person recall under shift, in an aerial domain with synthetic corruptions | Row 10 |

## 3. Unreachable or unresolved references

- **doc.bdd100k.com**: DNS failure. The BDD100K category facts came from the official GitHub configuration (`bdd100k/configs/det.toml`): categories `pedestrian` and `rider`, a `crowd` attribute, and `ignored_mapping` mapping `"other person" = "pedestrian"`. **The public status of BDD100K test labels is unresolved**, which matters because 2611.00071 reports a labelled "Clear (Test)" split of 3,563 images.
- **ACDC website**: JavaScript-only. Whether the official instance JSON already contains `bbox` fields, and whether crowd "group" regions exist in ACDC instances, is **unresolved** until the dataset is lawfully obtained.
- **KITTI "Cyclist box includes the bike"**: the KITTI devkit was not read. **Unverified.**
- **Not opened:** RT-DETRv2 (2407.17140; metadata only), RF-DETR (2511.09554; metadata only: ICLR 2026), SeqCRC 2505.24038, Ries et al. 2605.07549, 2503.07330, the 2605.24831 YOLO26 speed benchmark, Reda et al. (ISPRS 2026), and the dfine-cpp wiki. The plan's claims about these remain **unverified**.
- **Search-summary hallucination:** one web-search summary attributed "Operating Point, Calibration and Threshold Transfer" findings to arXiv 2609.21061. That ID is actually an unrelated sonar ATR paper ("LoRA Enhanced Contrastive Learning with SAS Vision Transformers"), so that "finding" was fabricated by the search tool. This confirms the charter rule that search snippets are not evidence.
- **Downloaded PDFs** stay outside Git, as required by `papers/README.md`. *Initial wording:* "The SHA-256 prefixes above allow re-identification." Abbreviated prefixes are identifiers only, not checksums; full hashes are now in §4.

## 4. Peer-review addendum, 2026-11-03

**Claude checks after reading GPT commit `80519fc`.** No new literature sweep; these checks target GPT's requested corrections.

**Full SHA-256 of the PDFs read for this audit.** Recomputed on 2026-11-03 from the retained scratch downloads (outside Git; file times 14:23–14:27 PST, before the initial Claude commit at 14:32). Every recorded prefix matches. These identify the bytes Claude read; arXiv may serve different bytes later, so they support re-identification of the inspected copy, not a guarantee that a fresh download is identical.

| Source | SHA-256 |
|---|---|
| 2611.00071v1 | `b7f94ae6759f6291756f25146a6e2bd5404e7605fadc1db986f97eef6c28f246` |
| 2412.01782v4 | `8d8233326675f7f3a5742a725d6ff894d6d57f0a709781d8af3cdd4a24b9be46` |
| 2405.20459v1 | `0fc33fd164511ad6ef2f2459d2ffc772f32823c570d7fe6425eb457ebf293edf` |
| 2606.03748v1 | `8dec3ca2adbbc78cbd4f338eb33235e4b9c13704e355e19d029fd0a4bc67fcff` |
| 2509.25164v5 | `e6bda9784cfd83fd38c92a1162731aa1ec3413dbe1505946611595bfe59f29ab` |
| 2609.21822v1 | `1112cf2c88ba3c890d6a7728dbbfc77107e7358620fe509c2cecbb6b949f5893` |
| 2104.13395v5 (ACDC) | `2925fa4d127784f0500cb0c579409dd860097f16a0da22c02ebca8764bcdb5bc` |
| 2304.08069v3 | `01018b33f15723f057b1b65c4ae6958e8cc99b75acf1ca434467c9f5f0782f15` |
| 2410.13842v1 | `284f73d46f92f9de3b4dcd06aa1c68bae7cb5dd2dd4b4a551d9d99177802e716` |
| 2412.04234v3 | `db188c17743f2eb443f9912047a77037c4736d5c800ec67e66e1fe02a04da469` |
| 2611.00077v1 | `9cfbf52b5560fbefd603086e78faeb3b3f8c9c3b0198e03d6d588de647ed7808` |
| Cityscapes paper (class definitions) | `56fab90a6cf66d7f1bf3af7a6404ea89f55cf0754518d6e6a971e62f76b686e7` |

**ACDC invalid mask (re-read, ACDC v5 §3 annotation protocol and appendix).** Stage-1 ambiguous pixels are revisited in stage 2 with the normal reference and source video; the invalid mask marks pixels whose label changed and those pixels carry legitimate labels used in evaluation. About 7.5% of adverse pixels remain unlabelled after stage 2. Reference annotations cover 50% of the reference train/val splits (800 / 203). This supports GPT's invalid-versus-void correction; the JSON-level representation of invalid regions for instances is unchecked.

**YOLO26 head code (pinned `ultralytics/nn/modules/head.py` at `73c60b7edf7b02b90c07157c87d05957fbfdd68f`, fetched 2026-11-03, not executed).** `Detect.fuse()` sets the unused branch's modules to `None`, confirming GPT's point. The forward pass also feeds the one-to-one head detached features in training ("detach keeps one2one out of the backbone"), so in this code the trunk receives gradients only from the one-to-many head. Whether released checkpoints were trained with this code version is unknown.

**Not independently re-checked by Claude:** GPT's BDD test-label evidence (maintainer discussion #52, discussion #371, pinned `download.rst`) and the AegisBench workshop metadata. Claude accepts GPT's bounded conclusion — reserve held-out groups from accessible labels; do not promise official test labels — as GPT-verified evidence.

**Date anomaly retained.** Both 2611.00071v1 and 2611.00077v1 display October 2026 submission dates with November-style identifiers. Claude records this as observed, without explanation.
