# Independent night-data route: conditional NightOwls acquisition

**GPT Sol; 2026-11-13; base `0cca68e`. G0 pending.** I want additional data for transferred human recall without treating overlapping ACDC frames as independent confirmation. This bounded primary-source investigation establishes a concrete access blocker, not a ready dataset. No dataset payload, account action, terms acceptance, GPU operation or Colab execution occurred.

**Decision:** prioritize official NightOwls, conditional on my personal license acceptance. Stop endpoint investigation here. Its public validation download responds, but lawful acquisition remains outside this task's authorization. BDD has no materially new official route established.

## Access and versions

The [official download page](https://www.nightowls-dataset.org/download/), read directly on 2026-11-13, publishes PNG/JSON train, validation and test-image packages. It lists annotations for train (32 MB) and validation (10 MB), and test **image IDs** (14 MB), not test boxes. Those are publisher-stated sizes. The homepage alone is generic and was insufficient evidence; the intact download page corrected that initial observation.

HEAD requests to the page's exact Oxford [validation-label](http://thor.robots.ox.ac.uk/~vgg/data/nightowls/python/nightowls_validation.json) and [validation-image](http://thor.robots.ox.ac.uk/~vgg/data/nightowls/python/nightowls_validation.zip) links returned HTTP 200 after redirects to HTTPS paths recorded in the [access record](2026-11-13_independent_data_access.json). Reported lengths are **10,696,948** and **57,481,286,834 bytes** respectively; both advertise byte ranges. No login challenge occurred. Headers establish public metadata access, not successful payload retrieval, integrity, Colab connectivity or a working evaluation server. No version/checksum manifest was established; Last-Modified/ETag are recorded as server metadata.

The download page's license permits noncommercial research with citation and prohibits redistribution of original/modified data; recoverable data must stay private. Its operative condition is “given that you agree”. No registration or click-through form was observed on that page. Public HTTP access does not supply my agreement. Required input is: **I have read and accept the NightOwls download-page conditions and authorize private retrieval of its validation annotation JSON for this research.** Account creation is not presently indicated.

## Documented policy versus inspected schema

The [Oxford author manuscript](https://www.robots.ox.ac.uk/~vedaldi/assets/pubs/neumann18nightowls.pdf), ACCV 2018, documents 40 recordings, dawn/night acquisition, 1024×640 images, 15 fps annotations, pedestrians/cyclists/motorcyclists above 50 pixels, and ignored posters, sculptures and inseparable groups. It states approximately 32k positive frames overall; this is **not** a verified night-only or project-eligible image count. Test annotations are withheld for server evaluation.

Inspected **SDK code**, pinned to Oxford's [`ad0f18f`](https://github.com/ox-vgg/nightowlsapi/tree/ad0f18fc95e093e86036f055ab210a3de46021b7), demonstrates xywh boxes in [the loader](https://github.com/ox-vgg/nightowlsapi/blob/ad0f18fc95e093e86036f055ab210a3de46021b7/python/load_training_data_demo.py). Its [evaluator](https://github.com/ox-vgg/nightowlsapi/blob/ad0f18fc95e093e86036f055ab210a3de46021b7/python/eval_MR_multisetup.py) uses native ignore, height and occlusion/visibility fields, with ignored-region intersection-over-prediction-area matching. Its Reasonable height/visibility filters are not automatically our policy.

**Actual annotation schema remains uninspected.** Class IDs, rider-versus-vehicle extents, visible versus amodal boxes, ignore/crowd representation, recording-key encoding, and eligible-positive image counts are unavailable here. A human-union mapping is plausible, not accepted. COCO compatibility does not settle these differences.

## Bounded acquisition and grouping plan

After acceptance, retrieve only the 10.7 MB official validation JSON privately, hash it and inspect categories, extents documentation, ignore records and recording keys. No image download is needed for that step. Keep validation entirely external: source calibration/selection stays in its existing source roles; do not select NightOwls partitions by detector performance. Freeze selection using recording identity and a declared frame cadence; retain zero-human frames. Block/resample whole recordings, expanding to shared trips/routes if documented. Tracking IDs are not independent groups; distinct datasets or IDs cannot prove training nonoverlap.

Direct HTTPS-to-Colab transfer could eliminate local re-upload. Full validation images require 57.5 GB compressed plus unverified extraction space, making that a poor default. Future selective ZIP range retrieval is conditional on verifying range behavior/member metadata; advertising ranges is insufficient. No selective-transfer size is established. Allocate no GPU for acquisition; the coordinator must bound later storage/transfer/inference separately.

## BDD and peer disposition

Current [official download documentation](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/doc/source/download.rst) and API-reported repository HEAD remain `9ac17c6` (2024-03-09): same ETH route, 53 MB revised-label claim and train/val tree. Saved [GPT](bdd_acquisition.md)/[Claude](../claude/dataset_acquisition_preflight.md) dead-host/mismatch findings stand; no dead hosts were retried. No new revised labels/access/schema were verified.

Actual Opus question and two Sol findings are preserved in the access JSON. The second finding corrects the homepage-only access uncertainty and supplies the license blocker. No peer assent or formal review is inferred. Next action is the single annotation retrieval after the specific acceptance above; broader protocol design belongs to Opus/coordinator.
