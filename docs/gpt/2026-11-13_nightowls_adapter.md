# Minimal NightOwls validation adapter

I want a private annotation conversion for the external descriptive/diagnostic panel under the [frozen policy](../decisions/2026-11-13_nightowls_external_policy.md), preserving the corrections in [Opus's annotation review and coordinator disposition](../reviews/2026-11-13_nightowls_annotation_review.md). GPT Sol implemented and CPU-checked this adapter on 2026-11-13. This is implementation evidence, not an independent review, official SDK evaluation, human approval or G0 passage. **G0 remains pending.**

`threshold_transfer.nightowls.convert_nightowls(doc, profile=..., source=...)` is a pure canonical-v1 dictionary conversion. The profile is mandatory: `person_compatible_ignore` is primary and `unused_nonpedestrian` is the fixed secondary. Source provenance follows the existing `source_files` convention. Returned documents contain restricted annotations and must remain private, outside Git. No CLI, runner, sampler, prediction conversion or matching change was added.

Every native `daytime == 'night'` image is retained, including empty and unkeyed frames; dusk images and their annotations are excluded. Eligibility is native category 1, ignore 0, **unclipped** height >=50, and occluded not True. Null occlusion follows the SDK convention, without inferring actual visibility. Difficult and truncated do not affect eligibility. All other pedestrian boxes are ignored. Primary also makes categories 2/3/4 ignored regions; secondary deliberately omits those categories. Original category/flags, pose and tracking values remain in private native attributes. Geometry is preserved without clipping or repair, with finite positive extents required. Native image, annotation and category IDs must be unique integers, and image/category references resolve, including on records omitted by the profile or daytime filter.

All retained boxes use the existing pilot matching token `human`. This does not make rider GT eligible. The target remains pedestrian-only, distinct from COCO person and ACDC merged human. Provenance supplies the existing evaluator policy: `categories=['human']`, `ignore_policy='same_category_ioa'`, `bounds_policy='allow_outside'`. Its unchanged matcher tries eligible GT at IoU >=.50 before reusable ignored regions at prediction IoA >=.50. No 40px detection filter or any candidate change is applied. These are SDK-inspired GT eligibility and category-scope sensitivity policies, explicitly provisional dataset policies rather than official SDK metrics.

Non-null integer-valued recording keys map stably to dataset-namespaced group strings. Null remains null, with no filename, timestamp or tracking inference. Five known keys are not five verified independent trips; the null bucket is not a sixth sequence. Pose is an unused opaque attribute: the input has **5,356 unresolved references**, and no pose integrity or repair claim follows. Tracking values are neither groups nor verified unique people.

## Synthetic checks

**Six tests passed** in `tests/test_nightowls.py` using the existing CPU environment. They check empty/night retention and dusk exclusion; null grouping plus the existing held-out rejection; the >=50 boundary, Boolean/null occlusion and out-of-frame height without clipping; primary/secondary category scope, eligible-first matching, reusable absorption and detections shorter than 40px; nonmutating canonical dict conversion; and refusal of malformed IDs/references/categories/geometry even for omitted records. Fixtures are synthetic, with no restricted records committed.

```powershell
$env:PYTHONPATH='src'
$env:PYTHONIOENCODING='utf-8'
& 'C:/Users/Advait/ar-work/venv-rtdetrv2/Scripts/python.exe' -B -m unittest discover -s tests -p test_nightowls.py -v
```

## Real annotation integration

The full local `C:/Users/Advait/autonomous-sys-research/data/nightowls/annotations/nightowls_validation.json` was read without retrieval. Its **10,696,948 bytes** and SHA-256 `584c0dc11f0d086fc5bcbaca0385cf2dd9794074f815f2727fbf9a093fd9a9b6` matched the supplied identity. Both profiles retained **51,846 images, 7,649 eligible GT, five known groups and 1,318 unknown-group images**. Eligible GT in unknown-group images numbered 872. Both excluded exactly two non-night images and retained all 42,359 natively empty night frames.

Primary produced **17,085 records: 7,649 eligible and 9,436 ignored**. Secondary produced **10,178 records: 7,649 eligible and 2,529 ignored**, all native category 1; 45,611 of its retained images have no category-1 record. The differing record counts do not change either profile's image population.

Each private serialized document was hashed, loaded again, checked for equality, and passed to actual `ReferenceEvaluator` construction with the declared policy above. Both constructors counted 7,649 eligible GT and 51,846 images. Empty prediction documents served only to validate the contract; no operating-point metrics or inference coverage were asserted. The native document equalled a defensive pre-conversion copy after each conversion. On the full manifest, the existing held-out role check returned **FAIL** with 1,318 unknown groups; diagnostic mode returned **DIAGNOSTIC_ONLY**. No role check was altered or bypassed.

Private evidence directory: `C:/Users/Advait/autonomous-sys-research/data/nightowls/adapter/2026-11-13/`. Paths below are relative to that directory; hashes are SHA-256:

- `person_compatible_ignore.canonical.json` (29,009,313 bytes): `a79a51cb01cd897bfc8f6c735c7d6aa86270336d05a2749d98678b5418270a32`.
- `unused_nonpedestrian.canonical.json` (26,336,727 bytes): `359c536de9381e9cb7e4a59f162a2b661fdc6f3d8ad7e3299bc1e98a43f32178`.
- `validation_counts.json` (counts, paths, hashes and check dispositions): `ce225b35ec54571eb5f83977d8b27fe9b49e8f1903c736ee60b05310ec7fc30a`.

`validation_check.py` in that private directory reproduces the integration with the same Python and environment variables above. The evidence records adapter source SHA-256 `8bc0a6604013ea6a5087b737e05bfb24d83e48796ac26e20caa80a9b7b2411f3`. `git check-ignore` in the main repository confirmed both converted documents and the report are covered by `data/**`. No annotations, native IDs, boxes, recording values or filenames appear in this public note; its filenames name artifacts only.

## Remaining limits and handoff

The separate [independent Opus review](../reviews/2026-11-13_nightowls_adapter_review.md) approved the actual adapter commit without code changes and independently matched every converted record and group mapping. There was no active peer assignment during implementation and no peer exchange was manufactured. The pinned SDK behavior is inherited from the reviewed policy evidence, not newly source-verified here. Native bbox extent, small-person completeness, null-occlusion publisher intent, recording independence and pretraining exposure remain unresolved. No images, archive/index, downloads, installs, model caches, GPU/Colab operations, inference or threshold selection occurred in implementation or review. The coordinator published the reviewed work in PR11; image acquisition and empirical model evaluation remain separately authorized work. This adapter supplies no safety, IID or G0 claim.
