# NightOwls validation annotations acquired

I accepted the [publisher's conditions](https://www.nightowls-dataset.org/download/) and authorized private retrieval of validation annotations only. GPT Sol downloaded that JSON from the officially linked Oxford host on 2026-11-13. No dataset images, image-archive index, GPU operation or detector inference were acquired or run. Raw labels remain gitignored; public files contain nonrecoverable counts, schema names and provenance only.

The HTTPS response contained **10,696,948 bytes**, matching its Content-Length, and parsed successfully. SHA-256 is `584c0dc11f0d086fc5bcbaca0385cf2dd9794074f815f2727fbf9a093fd9a9b6`. This is a computed identity, not a match against a publisher checksum. The [acquisition record](../datasets/nightowls_validation_acquisition.json) retains response metadata and the authorization scope.

## Actual schema and support

The artifact contains **51,848 images and 17,091 annotations**. Explicit `daytime` values identify 51,846 night frames and two dusk frames. All image dimensions are 1024×640. There are **six native `recordings_id` values**; these are observed recording keys, not proof of independent trips or scenes. `timestamp` exists, but its units and a frame-cadence rule have not been adopted.

Native categories are pedestrian, bicycledriver, motorbikedriver and ignore. Night records contain **10,178 nonignored native pedestrian annotations**. Exactly **45,611 night frames have no nonignored native pedestrian annotation**; they must remain in any all-frame cohort and its FPPI denominator. These counts do not yet apply final height, difficulty, occlusion or extent rules. Recorded difficulty and occlusion fields include nulls, so they cannot be treated as simple Boolean defaults without inspecting the publisher convention.

![Annotation inventory by anonymous recording](assets/2026-11-13_nightowls_annotation_inventory.png)

The six recording slots contain 1,577 / 348 / 6,072 / 560 / 280 / 1,341 native nonignored night pedestrian annotations. This imbalance is relevant to reporting both pooled and recording-wise outcomes; the slots reveal no native recording IDs or frame names.

All image/annotation IDs are unique in their respective tables, annotation references resolve, and every bbox has finite positive extents. **2,231 boxes extend outside the image**, and all recorded areas equal bbox width×height. Nothing was clipped or repaired. These observations do not establish visible versus amodal extent; an evaluator must preserve or explicitly resolve the native convention.

The [inventory](../datasets/nightowls_validation_inventory.json) and [reproduction script](../../scripts/data/nightowls_annotation_inventory.py) retain exact counts and geometry checks. Run the script on the private JSON with `--output` pointing to a counts-only report; it never fetches images or imports a GPU library.

## Next decision

The licence and annotation-access prerequisites are satisfied for this authorized step. Native ignore/category/extent semantics, a fixed empty-frame-preserving selection/cadence rule and an image-acquisition plan remain unresolved. No external protocol is frozen and neither scoped nor original BDD-primary G0 passes from these counts. Independent annotation review precedes any proposed image retrieval. My annotation-only authorization does not extend to images or a GPU allocation.
