# Research Plan: Do Clear-Day Detection Thresholds Keep Pedestrians Safe at Night?

**Working title:** *Threshold Transfer Under Shift: Calibration and Vulnerable-Road-User Recall of Modern Real-Time Detectors (YOLO vs NMS-free / DETR-family) on Driving Data*

**Evidence status:** this is my original working plan, including provisional claims from the initial scouts. The subsequent [source audit](docs/gpt/source_audit.md), [peer-discussed protocol](docs/gpt/protocol.md), and [discussion resolution](docs/gpt/review_resolution.md) qualify or supersede conflicting novelty, metric, model-default and experimental-design statements below. I have not frozen the protocol or passed G0.

**Scope:** my personal research project at PhD depth; course context below records the original starting point.
**Prepared:** 3 Nov 2026, from 5 scout agents + 2 adversarial critic agents (summarized in Appendix A)
**Status:** topic selected, nothing implemented yet. This is a living plan. Sections marked **FIXED** are the core commitments; everything marked **FLEXIBLE** can change as results come in, through the decision gates in §7.

---

## 0. How I'm using this plan

1. **This is my personal research project, with no fixed timeline or professor approval requirement.** The original 10-week and 6-week schedules below are historical planning references, not deadlines. My current scope and approval workflow are in `docs/PROJECT_CHARTER.md` and `CONTRIBUTING.md`.
2. **Verify the novelty claims against primary sources.** The original scouts and critics could NOT open arXiv full texts (the cloud network blocked arxiv.org, alphaxiv, Semantic Scholar, OpenReview, Hugging Face). Their literature evidence came from search snippets, abstracts, slides and GitHub READMEs. Check whether arxiv.org is now reachable and obtain the PDFs in §3.1 ("must read") in `papers/`. Any missing sources should be recorded explicitly. The single most important read is **arXiv 2611.00071** (see §2.3).
3. **Respect the compute budget** (§6). One RTX 5060 8 GB locally; $20–30 total cloud. Never start a cloud run without an estimate written in the experiment log.
4. **Work in the order of the phases (§7), and stop at each gate** to record a short status note: what was found, what it means, and the proposed next step. I'll make the decisions at gates G1–G4.
5. **I value honest negative results.** Do not bend the analysis to make the hypothesis come true. Every hypothesis in §2.2 has a pre-written "if false" interpretation.
6. Keep everything reproducible: configs in git, seeds fixed, one CSV row per evaluation (§8).

---

## 1. Context (FIXED)

### 1.1 Original course context (historical)

My initial framing drew on CMPE249 Intelligent Autonomous Systems. The assignment requirements below record that context; they are not requirements for my current personal project.
- Course: CMPE249 Intelligent Autonomous Systems, lectures 1–16 covered the autonomy loop, SAE levels, BEV, end-to-end driving, VLAs, data engines, CNN backbones, FPN/PAN, R-CNN → YOLOv3…v12/YOLO11, anchor-free heads, TAL, DFL, NMS, IoU losses, AP/mAP/AR, TIDE-style error analysis, calibration, KITTI formats and projection, deployment latency/quantization, ViT, DETR → Deformable/DAB/DN/DINO → RT-DETR (varifocal loss, query selection) → D-FINE/DEIM/RF-DETR, LiDAR physics.
- The course explicitly teaches: "Pedestrian/cyclist false negatives matter more than uniform mAP"; "calibrate confidence for tracker/planner"; "INT8/FP16 can hurt small-object recall & calibration"; "threshold = operating point". **This project is the empirical test of those lecture claims on today's detectors.**
- Project format (from Lecture 1): tracks = Algorithm / System / **Research** / Deployment. Course lane: **Safety and evaluation** ("Measure and catch failures: OOD detection, uncertainty, regression tests for long-tail scenarios"). Professor values: blue-ocean topics, read → reproduce → diagnose → extend → communicate, honest negative results.
- Deliverables for every track: proposal, codebase, experiment logs, final report, presentation, demo video.
- **Proposal package** (first assignment):
  - A. GitHub repo; README with title, team names, short abstract, chosen track.
  - B. Literature & SOTA survey in the repo: **5–10 papers from the last 1–3 years**, each with its claim, baseline, data, metric, and whether code is available (the "six lenses": claim, baseline, data, metric, ablation, failure modes).
  - C. Proposal document (problem formulation + approach).
  - D. **AI novelty audit**: ask an AI assistant to find prior work that already does the idea and paste the critique. (Appendix A of this plan is a ready-made starting point; re-run it with full-text access.)

### 1.2 Compute
- **Local:** RTX 5060, 8 GB VRAM, Blackwell (sm_120). Needs **PyTorch ≥ 2.7 with CUDA 12.8 (cu128)**. Pure-PyTorch models work. Custom CUDA extensions may not (spconv, some old deformable-attention ops). D-FINE, DEIM and RF-DETR were checked by the critic: they need only torch/torchvision/faster-coco-eval, and RF-DETR's deformable attention is pure `grid_sample` → expected to work on torch 2.7 cu128. **Verify in Phase 0.**
- **Cloud:** $20–30 total. At typical Vast.ai / RunPod prices for an RTX 4090 (≈ $0.30–0.70/h), that is ≈ 30–60 GPU-hours; A100 time is pricier. Plan for ≈ 25 h of 4090 time and keep a $5 reserve.

---

## 2. The research (core FIXED, details FLEXIBLE)

### 2.1 One-paragraph pitch
Real-time detectors are deployed with a single confidence threshold, usually tuned on clear-day validation data, and the tracker and planner trust scores above it. The newest real-time detectors (YOLO26, RT-DETR, D-FINE, DEIM, RF-DETR) score boxes very differently from YOLO11: one-to-one (NMS-free) assignment and IoU-aware losses (varifocal loss, DEIM's MAL) change what a "0.6" means. Nobody has measured whether **a threshold chosen on clear-day data still delivers the intended pedestrian/cyclist recall at night, in rain and in fog** for these detector families, or whether **proper object-level calibration metrics predict that loss better than mAP**. A recent paper (arXiv 2611.00071) reports that DETR is badly calibrated (ECE 0.44–0.58) while YOLO is near-perfect (ECE < 0.03) under weather shift. That gap may be a **metric artifact** of computing ECE over all of DETR's queries. We will reproduce that claim, diagnose it with localization-aware and object-level calibration metrics, then extend to the safety question that matters: threshold transfer for vulnerable road users (VRUs).

### 2.2 Research questions and hypotheses

| ID | Question | Hypothesis | If the hypothesis is false, we report… |
|---|---|---|---|
| **RQ0 (reproduce + diagnose)** | Does the "YOLO well calibrated, DETR badly calibrated under weather shift" result of 2611.00071 survive when calibration is measured properly (thresholded detections, LaECE, OCE) instead of all-query ECE? | The gap shrinks sharply or reverses under LaECE/OCE; most of DETR's reported ECE comes from low-score suppressed queries. | "The finding is robust to the metric", which independently confirms 2611.00071 with stronger metrics. Still a clean reproduction. |
| **RQ1 (core)** | When each detector's threshold is tuned on clear-day validation data to hit a target VRU recall (e.g., 0.90 pedestrian+rider/cyclist recall at IoU 0.5), how much recall does it lose at night, in rain and in fog, and how many false positives per image does it gain? Does this differ between NMS-based (YOLO11) and one-to-one / IoU-aware (YOLO26, RT-DETR, D-FINE, DEIM) families? | All families lose ≥ 10 recall points at night. IoU-aware/one-to-one heads lose **more** small/far VRU recall at a fixed threshold, because their score folds in box quality, and box quality drops for small, dark, blurry objects. | "Threshold transfer loss is similar across families", meaning architecture choice doesn't matter for this failure, and the fix must come from thresholding/calibration, not the detector. |
| **RQ2** | Which offline quantity best predicts the threshold-transfer loss across models and conditions: clear-day mAP, condition mAP, D-ECE, LaECE, or OCE? (Rank correlation, Kendall τ, with bootstrap CIs.) | Object-level / localization-aware calibration error predicts recall loss better than mAP does. | "mAP is as good a predictor as calibration", which is useful practical guidance. |
| **RQ3 (fix, FLEXIBLE)** | Does post-hoc recalibration fitted on clear-day data (temperature, Platt, isotonic) make thresholds transfer? Does a per-condition (Mondrian) calibration or a simple conformal recall-controlling threshold restore the target VRU recall, and at what false-positive cost? | Clear-day calibrators do **not** transfer (consistent with Kuzucu et al. ECCV'24). Per-condition calibration restores most of the recall at a moderate FP cost. | "Simple global recalibration suffices", a cheap and good-news result for practitioners. |
| **RQ4 (extension, optional)** | Measured on KITTI with true 3D distance: how does VRU recall at the transferred threshold fall with distance (0–15, 15–30, 30–50, 50+ m), and is the drop concentrated within stopping distance? | Recall loss is largest for far, small VRUs, but near-field misses (within stopping distance) exist and differ by family. | Report the distance curves as a diagnostic. |
| **RQ5 (extension, optional)** | Does TensorRT FP16 (all models) / INT8 (YOLO only) change calibration and the VRU threshold? | FP16 ≈ no change. INT8 shifts score distributions enough to move the operating point. | "Deployment precision doesn't affect calibration", a reassuring deployment note. |

**The sharpest one-sentence research question (use in the abstract):**
*"If you tune a real-time detector's confidence threshold on clear-day data to catch 90% of pedestrians and cyclists, how many does it miss at night, in rain and in fog, does that depend on whether the detector is NMS-based or NMS-free, and do calibration metrics (not mAP) warn you in advance?"*

### 2.3 Novelty positioning (verify with full texts!)

| Closest work | What it did | What it did NOT do (our opening) |
|---|---|---|
| **arXiv 2611.00071**, Mahin, Das et al., Oct 2026, "How Reliable Are Object Detection Models Beyond Clear Weather?" | Trained on BDD100K clear-day; tested on ACDC fog/rain/snow/night; YOLO-based, Faster R-CNN, DETR; mAP50, a weather-robustness index (WRI), **plain ECE**; classes car, bus, truck, person. Reported YOLO ECE < 0.03 vs DETR ECE 0.44 → 0.58. | (per snippets) No LaECE/OCE, no D-FINE/DEIM/RF-DETR/YOLO26, no cyclists, no distance, no recalibration, no threshold-transfer analysis, no tracking, no TensorRT. **TO VERIFY:** which YOLO version; whether RT-DETR is included; how ECE was computed (all queries vs thresholded). If they already used a threshold or OCE, the RQ0 "artifact" hook disappears; RQ1–RQ3 still stand. |
| Kuzucu et al., "On Calibration of Object Detectors: Pitfalls, Evaluation and Baselines", ECCV 2024 (arXiv 2405.20459; code `fiveai/detection_calibration`) | Defined LaECE; showed temperature scaling is a weak baseline, isotonic/Platt better; showed in-domain calibrators degrade under large domain shift. | Older detectors, COCO-style data; no real-time NMS-free detectors, no driving VRU threshold transfer. **Partly pre-empts RQ3's "calibrators don't transfer"; cite it and position RQ3 as testing it on VRUs + new detectors.** |
| Park et al., "Uncertainty Quantification in DETRs / object-level calibration", arXiv 2412.01782 (TPAMI 2026, `uq-detr`) | Object-level calibration error (OCE); warns that all-query ECE is misleading for DETRs. | Older DETRs (D-DETR, DINO, UP-DETR) + YOLOv3; no YOLO11/26, RT-DETR, D-FINE, DEIM; no driving threshold transfer. **This is the theoretical basis for RQ0.** |
| Penquitt et al., "Object Detection Benchmarks are Incomplete", NeurIPS 2026 (arXiv 2609.21822; repo `JonathanKlees/Uncertainty-aware-Object-Detection`) | KITTI/Cityscapes re-annotation (up to +60% objects); fine-tunes YOLOv8-L, RT-DETR, Faster R-CNN on KITTI/Cityscapes; isotonic calibration vs soft labels. | No weather/night shift, no threshold transfer, no NMS-free newest models. **We do NOT redo their soft-label evaluation.** Use their finding as a caveat for KITTI results (missing labels inflate FPs). |
| DEIM (arXiv 2412.04234, CVPR 2025) | Claims its MAL loss "corrects overconfident but inaccurate predictions". | Gives no ECE/LaECE/reliability evidence. **We test that claim directly** (a nice "claim check" for the survey). |
| Cal-DETR (2311.03570), BPC (CVPR 2023), Munir et al. NeurIPS 2022 | Train-time calibration losses; BDD100K or Foggy Cityscapes as OOD tests. | Older detectors; no VRU threshold transfer. |
| Ceccarelli & Montecchi 2203.02205; Liao et al. 2209.10368; Safety-Aligned 3D Detection 2604.03325; Kaul et al. 2603.28029 | Safety-aware/criticality metrics reorder **3D LiDAR** detectors vs mAP. | 3D only; no 2D real-time camera detectors. Motivates RQ2/RQ4. |
| Karimov et al. 2508.19600 | YOLO TensorRT INT8 robustness under corruptions, **mAP only**. | No calibration, no DETRs. Opening for RQ5. |
| Conformal detection: SeqCRC 2505.24038; Ries et al. 2605.07549 (COPA 2026, KITTI/BDD/CODA, EfficientDet); Timans et al. ECCV 2024 (2403.07263) | Marginal conformal guarantees for detection. | Per-condition (night) VRU guarantees with modern detectors appear unreported, but **this is crowded; keep it an optional RQ3 add-on.** Read SeqCRC and Ries first. |
| arXiv 2503.07330 | Hallucinated detections on OOD BDD inputs for YOLO and RT-DETR. | OOD hallucination, not calibration/threshold. Cite as related. |

**Novelty verdict from the critics:** "partially scooped" overall. The clear→adverse ECE drift exists (2611.00071), and KITTI soft labels exist (Penquitt). **Open:** (a) object-level / localization-aware calibration of the newest NMS-free/IoU-aware detectors; (b) clear-day threshold transfer for VRU recall under shift (most novel and most safety-relevant); (c) calibration after TensorRT. Critic scores (narrowed version): novelty 3/5, feasibility 4/5, safety relevance 3.5/5, course fit 5/5, low risk of an uninteresting null result.

---

## 3. Reading list (FLEXIBLE; trim to 5–10 for the survey)

### 3.1 Must read before writing the proposal (in this order)
1. **arXiv 2611.00071**: the paper we reproduce. Extract: exact models and versions, training recipe, image size, epochs, class set, how ECE is computed (bins? score threshold? all queries?), ACDC box derivation, released code?
2. Park et al. **2412.01782** (OCE; why all-query ECE misleads for DETRs).
3. Kuzucu et al. **ECCV 2024 / 2405.20459** (LaECE definition, operating-threshold protocol, calibrator baselines). Use their code.
4. **D-FINE** (ICLR 2025) and **DEIM** (CVPR 2025, 2412.04234): how scores are produced (MAL), the overconfidence claim.
5. **RT-DETR** (CVPR 2024) / RT-DETRv2 (2407.17140): varifocal loss = IoU-aware score.
6. **YOLO26** (Ultralytics, Sept 2025; arXiv 2509.25164 per scout): one-to-one/NMS-free head, no DFL.
7. Penquitt et al. **2609.21822** (KITTI label incompleteness caveat).
8. SeqCRC **2505.24038** and Ries et al. **2605.07549** (only if doing the conformal part of RQ3).

### 3.2 Background (cite, skim)
Munir et al. NeurIPS 2022; Cal-DETR 2311.03570; Ceccarelli 2203.02205; Karimov 2508.19600; 2503.07330; RF-DETR 2511.09554; BDD100K (Yu et al. CVPR 2020); ACDC (Sakaridis et al. ICCV 2021); KITTI (Geiger et al. 2012); ByteTrack (if doing tracking).

### 3.3 Survey table template (for deliverable B)
`| Paper | Year/venue | Claim | Baseline | Data | Metric | Ablation? | Failure modes | Code? | Relevance to us |`

---

## 4. Experimental design

### 4.1 Datasets (FIXED core, FLEXIBLE extras)
| Dataset | Role | Notes |
|---|---|---|
| **BDD100K** (detection, 100k images: 70k train / 10k val / 20k test) | Training (clear-day subset) and main evaluation (val, split by `timeofday` and `weather` attributes) | Free with registration. Classes include pedestrian, rider, car, truck, bus, train, motorcycle, bicycle, traffic light, traffic sign. Attributes: weather ∈ {clear, partly cloudy, overcast, rainy, snowy, foggy, undefined}; timeofday ∈ {daytime, night, dawn/dusk}. **Foggy is very rare in BDD** and tags are noisy (critic). Count each slice in Phase 0 and report the counts. |
| **ACDC** (Adverse Conditions Dataset with Correspondences) | Clean adverse-condition test set: fog, night, rain, snow (+ normal-condition reference images) | Instance/panoptic masks → **derive boxes from instance masks** (write and visually verify a converter: render 100 random samples, per the course's format-bug advice). Cityscapes-style classes (person, rider, car, truck, bus, train, motorcycle, bicycle). Same test set as 2611.00071 → enables RQ0. |
| **KITTI 2D object** (7,481 train images, with 3D location per box) | RQ4 distance-binned analysis (daytime only) | True distance from `location` (camera frame, metres). Classes: Car, Pedestrian, Cyclist (+ DontCare regions: exclude predictions overlapping DontCare from FP counts). Caveat: Penquitt shows KITTI misses many small/occluded objects → FP counts are pessimistic. |
| (Optional) BDD100K MOT | Tracking effect of thresholds | Cut unless ahead of schedule. |

**Class mapping (decide in Phase 0, then FIXED):** VRU = {pedestrian, rider} (+ bicycle/motorcycle only if analysing the vehicle too). Main reporting classes: pedestrian, rider/cyclist, car. Map BDD ↔ ACDC ↔ KITTI consistently: BDD "rider" ≈ ACDC "rider" ≈ KITTI "Cyclist" (KITTI Cyclist box includes the bike; note the policy difference in the report).

**Clear-day training subset:** BDD train images with weather ∈ {clear, partly cloudy, overcast?} AND timeofday = daytime. Decide whether overcast counts as "clear" and keep it fixed. Target ≈ 15k images (critic's compute estimate). Also hold out a **clear-day calibration/threshold split** from BDD val (e.g., 50% of clear-day val) that is never used for testing.

### 4.2 Models (core set FIXED at Phase 0 gate, extras FLEXIBLE)
Use small ("S"/"N") variants so training fits in 8 GB locally or a few hours on a 4090. Same input size (640), same training data, same epoch budget (as far as each recipe allows; document deviations).

| Model | Family / score type | Source | Priority |
|---|---|---|---|
| **YOLO11s** | NMS-based, BCE + TAL | `ultralytics` | Core |
| **YOLO26s** | One-to-one (NMS-free), no DFL | `ultralytics` | Core |
| **RT-DETR(v2)-R18 / S** | DETR, varifocal (IoU-aware) score | `lyuwenyu/RT-DETR` (v2) or Ultralytics `rtdetr-l` if R18 is a problem | Core |
| **D-FINE-S** *or* **DEIM-D-FINE-S** | DETR, distribution refinement; DEIM adds MAL | `Peterande/D-FINE`, `ShihuaHuang95/DEIM` | Core (pick one; DEIM preferred because it tests the MAL "fixes overconfidence" claim) |
| RF-DETR-N/S | DETR + DINOv2 backbone | `pip install rfdetr` | Optional (memory on 8 GB may be tight) |
| YOLOv8s | NMS-based (likely used in 2611.00071) | `ultralytics` | Only if needed for RQ0 reproduction |

**Two-stage approach:**
- **Stage A (zero-shot, free):** COCO-pretrained checkpoints, evaluated on BDD val / ACDC with COCO→driving class mapping (person→pedestrian; bicycle/motorcycle; car, bus, truck). This gives fast early signal for RQ0/RQ1. **Caveat:** a scout cited Reda et al. (ISPRS 2026), where RT-DETR-L dropped from 53.0 COCO mAP to 34.3 zero-shot on KITTI while YOLO11-L reached 51.3. Zero-shot class/policy mismatch confounds the comparison, so **Stage A is exploratory only**.
- **Stage B (fine-tuned, main results):** fine-tune each core model on the BDD clear-day subset, then run all experiments.

### 4.3 Metrics (FIXED definitions; implement once, unit-test)
- **Accuracy:** COCO AP, AP50, AP_S/M/L per condition; per-class AP for pedestrian, rider, car.
- **Calibration (compute all three, side by side; this IS RQ0):**
  1. **All-query / all-detection D-ECE** (what 2611.00071 likely did): every output box/query with its score.
  2. **Thresholded D-ECE**: only detections above the model's operating threshold.
  3. **LaECE** (Kuzucu; use `fiveai/detection_calibration`): localization-aware, per class, at operating threshold.
  4. **OCE** (Park; use `uq-detr`): object-level.
  - Reliability diagrams per model × condition (pedestrian class at minimum).
- **Threshold transfer (RQ1 core):**
  - Fix τ\* on the clear-day calibration split so that VRU recall (IoU ≥ 0.5) = target R\* (default 0.90; also report 0.80 and 0.95 for robustness).
  - On each condition c (clear-day test, night, rain, fog, snow, dawn/dusk): **Recall_c(τ\*)**, **ΔR_c = R\* − Recall_c(τ\*)**, **FPPI_c(τ\*)** (false positives per image), **Precision_c(τ\*)**.
  - **Oracle comparison:** τ_c^oracle that achieves R\* on condition c, and its FPPI. The gap "FPPI at oracle vs at τ\*" shows the cost of fixing the threshold.
  - Split ΔR by object size (box height bins, e.g., < 32, 32–64, 64–128, > 128 px) on BDD/ACDC, and by true distance on KITTI (RQ4).
- **Prediction of transfer loss (RQ2):** Kendall τ between each candidate predictor (clear mAP, condition mAP, D-ECE variants, LaECE, OCE) and ΔR across (model × condition) cells. Bootstrap over images (≥ 1,000 resamples) for CIs. Be honest: with ~4–5 models × ~4 conditions = 16–20 cells, statistical power is limited. Say so.
- **Error analysis (for the report, cheap):** TIDE-style breakdown (cls / loc / both / dupe / bkg / missed) for VRUs at τ\*, clear vs night. Explains *why* recall dropped (misses vs low scores vs localization).

### 4.4 Calibrators (RQ3)
Fit on the clear-day calibration split only: temperature scaling, Platt (logistic), isotonic regression (per class). Then:
- Re-measure LaECE/OCE per condition.
- Re-define the threshold on the **calibrated** probability (e.g., choose τ\* in calibrated space) and re-measure ΔR. Does calibrated-space thresholding transfer better?
- **Per-condition (Mondrian) variant:** fit a calibrator per condition, using a small labelled calibration set from that condition. This is an "oracle-ish" upper bound, and its practicality depends on knowing the condition at runtime, which is easy for night via image brightness/time-of-day. Optionally: a simple split-conformal threshold per condition for recall control (only after reading SeqCRC/Ries).

### 4.5 Controls and fairness checks
- Same train set, same input size, same augmentation family where possible (note: each repo has its own recipe; record every deviation in `docs/deviations.md`).
- Report each model's clear-day AP first. If one model is far weaker, its threshold transfer is confounded by accuracy. Consider matching operating points rather than architectures in that case.
- **Seeds:** at least 1 seed per model (budget); 2 seeds for the two most important models if budget allows. Otherwise rely on image-level bootstrap and state that seed variance is unmeasured.
- Leakage check: BDD val/test images never used for training or for calibration except the designated calibration split.

---

## 5. Software setup (Phase 0 details)

- Environment (local): Python 3.10/3.11, **PyTorch ≥ 2.7 cu128**, torchvision matching, `ultralytics` (latest; YOLO11, YOLO26, RT-DETR), `faster-coco-eval`, `pycocotools`, `netcal` (D-ECE), `fiveai/detection_calibration` (LaECE), `uq-detr` (OCE), `pandas`, `matplotlib`, `scipy`, `scikit-learn` (isotonic/Platt).
- Separate conda envs per detector repo if dependency pins conflict (D-FINE / DEIM / RT-DETRv2 / RF-DETR). Convert all predictions to one **common prediction format** (COCO results JSON: `image_id, category_id, bbox[x,y,w,h], score`, plus `model, condition, split`), so evaluation code is shared and model-agnostic.
- **Blackwell check (day 1):** for each repo, run 20 training iterations and one evaluation on 50 images locally. If a repo fails on sm_120, run it on the cloud 4090 only (or drop it at gate G0).
- Cloud: Vast.ai or RunPod, an RTX 4090 with ≥ 24 GB, a PyTorch 2.7 template. Use a persistent volume for data. Copy only the BDD clear-day subset + val (not all 100k images) to save time. **Stop instances immediately after runs; log cost per run.**
- Export (RQ5 only): ONNX → TensorRT 10.x for YOLO11/26 (FP16 + INT8 via Ultralytics/ModelOpt). DETRs FP16 only. **Known pitfall (critic, verified in the dfine-cpp project wiki):** stock `grid_sample` export degraded D-FINE AP 0.551 → 0.446 in TensorRT; naive FP16 collapsed AP on TRT 10.13 (LayerNorm decomposition); D-FINE INT8 was rejected because box decoding needs ≥ FP16. **Treat DETR TensorRT as a reported finding, not a requirement.**

---

## 6. Compute and cost budget (FLEXIBLE, but log every hour)

| Item | Where | Estimate | Cost |
|---|---|---|---|
| Phase 0 smoke tests, data conversion, slice counts | Local | ~5 GPU-h | $0 |
| Stage A zero-shot inference (4–5 models × BDD val 10k + ACDC ~4k) | Local | ~3–5 GPU-h | $0 |
| Stage B fine-tuning: 4 core models × ~15k images × 30–50 epochs (S-size) | Cloud 4090 | ~2–3 h each → **~10–12 h** | ~$5–9 |
| Second seed for 2 models (optional) | Cloud or local overnight | ~5–6 h | ~$3–4 |
| Alternative: train smaller models locally overnight at batch 4–8 with AMP | Local | 6–12 h per model | $0 (slower) |
| Calibration, thresholds, bootstrap, plots | Local CPU/GPU | ~2–4 h | $0 |
| RQ4 KITTI fine-tune (optional; KITTI is small, ~7.5k images) | Local | ~2–4 h per model | $0 |
| RQ5 TensorRT export + eval | Local | ~3–5 h | $0 |
| **Reserve** | | | **≥ $5** |
| **Total cloud** | | | **≈ $10–20** (well under $30) |

Rules: never leave a cloud instance idle; check checkpoints every few epochs; if a run diverges, stop it. Use `close_mosaic`/EMA defaults from each repo.

---

## 7. Phases, deliverables and decision gates

### 7.1 Default 10-week schedule

**Phase 0: Setup and verification (Week 1)**
- Read the must-read papers (§3.1), especially 2611.00071.
- Create the repo (§8 layout); README with title/abstract/track (**Research track**, safety & evaluation lane).
- Download BDD100K (images + labels), ACDC, KITTI 2D. Write converters to the common format. **Render ~100 random samples per dataset with boxes to catch format bugs.**
- Count images and VRU instances per slice (BDD timeofday × weather, ACDC conditions). Decide the final condition set (drop slices with too few VRUs, e.g., if BDD foggy has < ~100 pedestrians, use ACDC fog instead).
- Smoke-test every model repo on the 5060 (§5).
- **Gate G0 (end of week 1):** Which models run where? Is 2611.00071's protocol clear enough to reproduce? Are the slice counts adequate? → Freeze the core model list and class mapping.

**Phase 1: Zero-shot exploration + RQ0 first pass (Week 2)**
- Run COCO checkpoints on BDD val and ACDC (Stage A).
- Implement all metric code (§4.3) and unit-test it on a toy example (e.g., hand-made predictions where the ECE is known).
- Compute all-query ECE vs thresholded ECE vs LaECE vs OCE for YOLO vs DETR-family checkpoints.
- **Gate G1:** Does the metric choice change the YOLO-vs-DETR calibration ranking?
  - **Yes** → RQ0 is a headline result; keep it prominent.
  - **No** → RQ0 becomes a short "confirmed with stronger metrics" section; lean on RQ1/RQ3.
  - Either way, continue.

**Phase 2: Proposal package (Week 2–3, overlaps)**
- Survey of 5–10 papers using the §3.3 table. AI novelty audit (start from Appendix A; re-run with full texts). Proposal document: problem, RQs, hypotheses, datasets, models, metrics, plan, risks. Submit.

**Phase 3: Fine-tuning (Weeks 3–4)**
- Build the BDD clear-day training subset and clear-day calibration split.
- Fine-tune the 4 core models (cloud 4090, §6). Log everything.
- Evaluate clear-day AP and per-condition AP.
- **Gate G2:** Are models within a reasonable AP band (e.g., within ~5 AP of each other on clear-day VRUs)?
  - If one is far behind → retrain with a fixed recipe, or present it with a caveat, or drop it.
  - If budget is overrunning → drop the second seed and RF-DETR.

**Phase 4: Core analysis RQ1 + RQ2 (Weeks 5–6)**
- Threshold transfer tables and plots: ΔR and FPPI per model × condition × size bin. Reliability diagrams. TIDE breakdown at τ\*.
- RQ2 rank correlations with bootstrap CIs.
- **Gate G3 (my mid-project review):** what's the story so far?
  - **(a)** Families differ a lot → emphasise architecture insight.
  - **(b)** All similar → emphasise thresholding/calibration fix (RQ3).
  - **(c)** Calibration metrics predict ΔR well → emphasise "monitor calibration, not mAP".
  - Choose 1–2 extensions from Phase 5 accordingly.

**Phase 5: Fix + extensions (Weeks 7–8), choose from the menu**
- **RQ3 (recommended):** clear-day calibrators vs per-condition calibration vs conformal threshold; recall restored vs FP cost.
- **RQ4:** KITTI distance-binned VRU recall at transferred thresholds (fine-tune core models on KITTI or evaluate BDD-trained models zero-shot on KITTI; state which). Mark which misses fall within stopping distance (e.g., at 50 km/h ≈ 25–30 m).
- **RQ5:** TensorRT FP16/INT8 effect on calibration and the VRU threshold (YOLO INT8; DETRs FP16 only).
- **Stretch: "does it matter in closed loop?"** Inject the measured night-time miss-rate-vs-distance curve into the rule-based PDM-Closed planner on 50–100 nuPlan-mini scenarios (CPU only). This is a demo, not a full study. Only attempt if Phases 1–4 finished early. Expect environment pain: the nuplan-devkit pins Python 3.9 / torch 1.9.
- Small demo for the video: side-by-side clear vs night clip with boxes at τ\*, missed VRUs highlighted.

**Phase 6: Write-up and demo (Weeks 9–10)**
- Final report (paper format: intro, related work, method, experiments, results, limitations, conclusion), slides, demo video, cleaned repo with a reproduce script.
- **Gate G4:** decide which negative results to include, how to frame them, and the final title.

### 7.2 What each gate can change
| Gate | Can change | Cannot change without my approval |
|---|---|---|
| G0 | Model list, class mapping, condition set, which repos run locally vs cloud | The core question (RQ1) |
| G1 | Prominence of RQ0 | — |
| G2 | Number of models/seeds, training recipe | Dropping all DETR-family models (the comparison would collapse) |
| G3 | Which extensions; emphasis of the story | Switching topics. If RQ1 is infeasible (e.g., data unusable), propose **Backup Plan C** (Appendix B) for my review. |
| G4 | Framing, title | Results (report what happened) |

### 7.3 Compressed 6-week version (if the semester ends mid-December)
- Week 1: Phase 0 + start Phase 1 (zero-shot).
- Week 2: Phase 1 + proposal package.
- Week 3: fine-tune **3 models only** (YOLO11s, YOLO26s, one DETR-family model) on the cloud; seed 1 only.
- Week 4: RQ1 + RQ2 core analysis.
- Week 5: RQ3 with global calibrators + per-condition (no conformal); skip RQ4/RQ5 unless trivial.
- Week 6: write-up, slides, demo.
- If even this is too tight: **zero-shot only (Stage A) + RQ0 + RQ1 on COCO checkpoints**, clearly labelled as exploratory. That is still a complete, honest study.

---

## 8. Repo layout and logging conventions

```
repo/
  README.md                 # title, team, abstract, track, how to reproduce
  RESEARCH_PLAN.md          # this file (keep updated; log gate decisions at the bottom)
  docs/
    survey.md               # 5–10 paper table (deliverable B)
    novelty_audit.md        # AI novelty audit (deliverable D)
    deviations.md           # per-model recipe deviations
    gate_log.md             # one entry per gate: date, evidence, decision
  papers/                   # PDFs (gitignored if licensing requires)
  data/                     # gitignored; scripts only
  src/
    convert/                # bdd_to_coco.py, acdc_masks_to_boxes.py, kitti_to_coco.py
    infer/                  # one runner per model family → common results JSON
    metrics/                # ap.py, calibration.py (dece, laece, oce wrappers), transfer.py, tide.py
    calibrate/              # temperature.py, platt.py, isotonic.py, mondrian.py
    analysis/               # make_tables.py, make_plots.py, bootstrap.py
  configs/                  # one YAML per experiment (model, data split, seed, epochs, imgsz)
  results/
    runs.csv                # one row per training run: id, model, data, epochs, seed, gpu, hours, cost, clear AP
    evals.csv               # one row per (model, condition, metric): value, CI_low, CI_high
    figures/
  tests/                    # metric unit tests on toy predictions
```

- Every training run gets an ID and a YAML config committed **before** the run starts.
- Every number in the report must be traceable to a row in `results/*.csv`.
- Update `docs/gate_log.md` at each gate.

---

## 9. Risks and mitigations

| Risk | Likelihood | Mitigation / pivot |
|---|---|---|
| 2611.00071 already used thresholded ECE/OCE or already includes RT-DETR → RQ0 hook weakens | Medium | RQ1–RQ3 remain open per critics; reposition RQ0 as a brief confirmation. |
| A newer paper (Oct–Nov 2026) does VRU threshold transfer for NMS-free detectors | Low–medium | Re-run the novelty search in Phase 0 with full-text access; if scooped, pivot emphasis to RQ3 (fix) + RQ5 (deployment), or to Backup C. |
| D-FINE/DEIM/RT-DETRv2 won't run on the RTX 5060 | Low (pure PyTorch) | Cloud 4090 for those models; or use Ultralytics RT-DETR as the DETR representative. |
| Fine-tuned models differ too much in accuracy (confound) | Medium | Report matched-recall operating points; show results conditioned on clear-day AP; possibly add a second, better-matched model. |
| Too few night/fog VRUs for stable estimates | Medium for fog | Use ACDC for fog; report bootstrap CIs; merge rare conditions into "adverse" if needed. |
| ACDC box conversion errors | Medium | Visual audit of 100 samples; compare box counts with the instance count. |
| KITTI label incompleteness inflates FPs | Known | Report recall-centric metrics on KITTI; cite Penquitt; optionally re-score with their corrected labels if downloadable. |
| TensorRT DETR export breaks accuracy | High | RQ5 is optional; report failures as findings; YOLO-only INT8. |
| Cloud budget overrun | Low | §6 rules; local overnight training fallback; drop second seeds first. |
| Semester too short | Medium | §7.3 compressed plan; Stage-A-only fallback. |

---

## 10. My next steps

1. Confirm lawful access to BDD100K/ACDC/KITTI and the must-read papers. I have no fixed deadline; progress depends on the research gates, not the historical schedules.
2. Check network access to arxiv.org. If it's blocked, log which PDFs still need to be obtained. Read 2611.00071 first; fill in its row in §2.3 with verified facts; update RQ0 if needed.
3. Maintain the repo skeleton (§8), README and environment files. I've authorized commits and pushes; research PRs require GPT–Claude discussion first and my approval before merging.
4. Write `bdd_to_coco.py` with attribute filtering and the slice counts table, then the ACDC mask-to-box converter, with visual audits.
5. Smoke-test models on the RTX 5060 (§5); fill in the G0 decision.
6. Implement and unit-test the metrics module before running any real evaluation.
7. Keep this plan updated: when something changes, edit the relevant section and log the reason in `docs/gate_log.md`.

**Things not to do:**
- Don't claim novelty in writing until the full-text check is done.
- Don't train on test data or tune thresholds on test conditions.
- Don't silently drop a model or condition: log it.
- Don't spend cloud money on DETR INT8 export.
- Don't expand scope (tracking, RF-DETR, nuPlan) before G3.

---

## Appendix A: How the topic was chosen (evidence ledger)

**Process:** 5 parallel scouts (real-time detectors; safety/evaluation; data engine/VLMs; 3D/BEV/LiDAR; end-to-end/world models) each proposed 3–5 gaps with literature checks. 2 adversarial critics then tried to scoop and break the 4 strongest candidates. **Network caveat: all of this was done without full-text access to arXiv; treat novelty claims as provisional.**

**Candidates and verdicts:**
| Candidate | Critic verdict | Scores (novelty / feasibility / safety meaning / course fit / null-result risk; 5 = best, last: lower = better) | Outcome |
|---|---|---|---|
| **A. Calibration & VRU threshold transfer of modern real-time detectors** (3 scouts converged on it) | Partially scooped (2611.00071 did clear→adverse ECE with plain ECE; Penquitt did KITTI soft labels). Open: object-level calibration of new NMS-free detectors, VRU threshold transfer, calibration after TensorRT. | 3 / 4 / 3.5 / 5 / 2 | **Selected (narrowed)** |
| B. Matched-mAP perception error types → nuPlan closed-loop planners | Partially scooped (40–50%: PKL CVPR'20, Schreier 2308.12779, TIP ICML'23, Sadeghi 2311.12722, EMPERROR 2411.07719). Matched-mAP multi-planner nuPlan design looks open. Blockers: nuplan-devkit pins Python 3.9/torch 1.9; 160–480 CPU-hours for a full grid; synthetic confidence scores are a methodological target. | 3.5 / 2.5 / 4 / 4 / 3 | Kept as a **stretch demo** (Phase 5) and Backup B |
| C. Low-beam LiDAR + depth foundation model densification → 3D detection AP by distance | Partially scooped (Pseudo-LiDAR++ 2019, 2105.01765, 2404.06715 did the pipeline with older depth). Open: zero-shot 2025–26 foundation completers × beam reduction × distance-binned detection AP. Blockers: spconv on Blackwell (use cloud), KITTI leakage in depth checkpoints, point-pattern domain gap. | 3 / 3 / 4 / 5 / 2 | **Backup plan** (Appendix B) |
| D. Label-policy mismatch in open-vocabulary auto-labeling | Partially scooped *recently* (Klees 2610.29788, Penquitt 2609.21822; adapters pre-empted by LGPL ICLR'24, AutoExpert 2506.02914, Guideline-Seg 2509.04687). Measurement of "policy vs perception" is contestable. | 2–3 / 5 / 3 / 3 / 3 | Rejected |

**Other ideas considered and rejected (crowded or infeasible):** open- vs closed-loop metric correlation (NAVSIM v2 2506.04218, 2605.00066, 2510.14677); VLM-as-judge for trajectories (DriveCritic, DriveJudge); VLA chain-of-thought faithfulness (several 2026 benchmarks); camera/latency perturbation of E2E models (Bench2Drive-Robust 2605.18059); foundation-model distillation into tiny detectors (DEIMv2, RF-DETR); weather robustness of BEV/occupancy (RoboBEV, MultiCorrupt, nuScenes-C); 905 vs 1550 nm comparison (no paired public dataset); cross-LiDAR beam transfer alone (LiDAR Distillation, Robo3D, 2503.15087); 4-bit quantization and grounding of small driving VLMs (feasible but less central; a possible side project); generator-agreement for safety-critical scenario generation (interesting, engineering-heavy).

**Useful verified facts gathered along the way:**
- YOLO26 (Ultralytics, Sept 2025) is NMS-free with one-to-one assignment and no DFL. An independent benchmark (2605.24831) found YOLOv8 faster than YOLO26 on GPU at matched scale (VOC/VisDrone).
- The DEIM paper concedes YOLOv9-E beats D-FINE-L by ~1.4 AP_S on COCO small objects.
- D-FINE/DEIM/RF-DETR have no custom CUDA extensions (pure PyTorch) → should run on Blackwell with torch 2.7 cu128.
- spconv has no sm_120 wheel (issue traveller59/spconv#746 open) → 3D sparse-conv detectors need a non-Blackwell GPU.
- The Penquitt et al. repo fine-tunes YOLOv8-L, RT-DETR and Faster R-CNN on KITTI/Cityscapes with isotonic calibration vs soft labels.

---

## Appendix B: Backup Plan C (if A collapses at G0/G3)

**Question:** *"On KITTI, at what range and at what points-per-box does zero-shot foundation depth completion of 16/8/4-beam LiDAR stop recovering 64-beam PointPillars AP? Is the bottleneck depth error or the point-pattern domain gap?"*
- **Data:** KITTI 3D (3,712 train / 3,769 val). Simulate beams using the Pseudo-LiDAR++ / LiDAR-Distillation sparsify code; don't hand-roll (the HDL-64E has non-uniform elevation spacing).
- **Densifiers:** raw low-beam (baseline), IP-Basic (classical), 2 foundation completers (e.g., scale-aligned Depth Anything V2 relative, PromptDA or Prior Depth Anything); a KITTI-DC-trained completer only as a labelled "oracle-ish" row.
- **Leakage audit:** Depth Anything metric-outdoor was fine-tuned on KITTI depth (overlaps KITTI 3D val), so avoid it or label it.
- **Detector:** PointPillars only (OpenPCDet). Three conditions: (1) frozen 64-beam-trained detector; (2) densified depth re-rendered into a virtual 64-ring pattern; (3) PointPillars retrained on densified input. This separates depth error from the domain gap.
- **Metrics:** AP3D/APBEV (R40) by distance bin (0–20, 20–40, 40+ m) and by points-in-box; latency/VRAM per pipeline.
- **Compute:** densification locally (~5–10 h); PointPillars training/eval on a cloud 4090 (~15–25 h; tight but fits). Verify the OpenPCDet pillar path builds; spconv is not needed for PointPillars itself but may be pulled in by the install.
- **Must-check first:** read 2603.26759 (Physics-Aware Diffusion LiDAR densification) in full; it is the most likely scoop. Search for 2026 papers citing 2105.01765 and LDCM (2605.30115).
- Cut: PV-RCNN, SECOND, calibration add-on (GACE ICCV'23 already covers it), nuScenes.

## Appendix C: Backup Plan B-lite (only if I choose to focus on planning)
At equal NDS, compare closed-loop collision/TTC violations for 4 error profiles (distance-dependent misses, temporal flicker, pose noise, latency) on PDM-Closed + PlanTF, about 100 nuPlan-mini scenarios, non-reactive mode first. Run planners on CPU in a Python 3.9 env. Pre-register how synthetic confidence scores are generated. Kendall τ of offline metrics vs closed-loop outcome. Budget: mostly CPU-hours (cut the grid to fit).

---

*Gate decisions log (append below):*
- 2026-11-03: Topic A selected (narrowed). Backups: C, then B-lite. D rejected.
