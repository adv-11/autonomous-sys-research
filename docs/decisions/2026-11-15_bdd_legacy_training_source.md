# First training experiment: BDD100K legacy labels as the source

**Decision, 2026-11-15.** I chose BDD100K with its 2018 legacy detection labels as the source for the first trained threshold-transfer experiment. This supersedes, for this experiment only, the earlier rule against substituting legacy labels for Detection 2020 labels. Claude Opus coordinates while GPT Sol has no Codex credits.

## Why

The project question needs clear-day training and threshold selection, then night and adverse-weather testing, under one camera setup and one labelling policy. Only BDD100K provides that. The revised 2020 labels remain unavailable through every route checked. NightOwls and ACDC (Adverse Conditions Dataset with Correspondences) stay external tests, never training or tuning data.

## Naming and provenance limits (always stated)

- Labels: **BDD100K legacy 2018 detection labels**, the Berkeley candidate archive (`bdd100k_labels.berkeley-candidate.zip`; 100,000 per-image JSON files with `weather`, `timeofday` and `scene` attributes). Its MD5 differs from the published value. Results are never described as Detection 2020 results.
- Images: the pinned Hugging Face mirror archive (SHA-256 `afd149ea…4e02784`), whose MD5 differs from the official archive. Publisher identity is unverified.
- Any finding is conditional on these artifacts, and the limitation appears in every report and figure caption.

## Experiment shape

1. Source: BDD legacy train images with `weather = clear` and `timeofday = daytime`. Fine-tune one core model first, YOLO11s, with one seed.
2. Threshold selection: a held-out clear-daytime split (images never used for training), at pedestrian recall targets 0.80, 0.90 and 0.95, using the existing evaluator.
3. Test: BDD legacy val by condition (clear day, night, rain, snow, fog, dawn/dusk), reporting recall, false positives per image and the candidate-ceiling versus threshold-removed decomposition. Then ACDC as a descriptive external panel and NightOwls validation once its download is verified.
4. Expansion to YOLO26s, RT-DETRv2 and more seeds follows only after the first result shows a contrast worth explaining.

All GPU work runs on my Colab account, with one designated executor, a staged compute budget and verified teardown. My explicit approval still governs merges. G0 remains pending.

## Dataset scope frozen (2026-11-15)

I froze the dataset scope at five: BDD100K (legacy labels), ACDC, NightOwls, COCO and KITTI. No further dataset searches or acquisitions. Once the NightOwls download finishes and is verified, effort goes to model training and experiments. I also lifted the 20 CU compute envelope: runs are sized by scientific value, staged, with a coordinator check-in before cumulative spending passes 100 CU.
