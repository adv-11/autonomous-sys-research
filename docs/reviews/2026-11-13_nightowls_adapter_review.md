# Independent Claude Opus review of the NightOwls adapter and proposed image-access pilot

**Disposition: APPROVE for the adapter, with no changes required. The pilot proposal has no blocking issue; root should make three small P3 fixes before any authorization.** This is a new Claude Opus 5.5 review task. Earlier Opus reviews are historical context only and are not new verification here. It is an AI review: it is not my human merge approval, it does not pass G0 (**G0 remains PENDING**) and it authorizes no image access, inference or compute.

## Scope and provenance

- **Adapter:** GPT Sol commit `a4bf61bd19b632df96d047d2af1c9df638736ded`. It was integrated as `5e9e1d7`, and `git diff a4bf61b 5e9e1d7` is empty. Files reviewed: `src/threshold_transfer/nightowls.py`, `tests/test_nightowls.py`, `docs/gpt/2026-11-13_nightowls_adapter.md`. They were checked against [the policy decision](../decisions/2026-11-13_nightowls_external_policy.md) and the [annotation review and root disposition](2026-11-13_nightowls_annotation_review.md). The current inventory correctly reports five known keys plus null; I did not revisit that question.
- **Pilot plan (proposal only):** commits `2fad2dd` and `aa6ff0d` (HEAD). Files: `docs/decisions/2026-11-13_nightowls_image_access_pilot.md` and `configs/research/nightowls_image_access_pilot_20261113.json`.
- **Private inputs, read only:** the annotation JSON (SHA-256 `584c0dc1…a9b6`, matched) and the root `outputs/nightowls_image_access_pilot_20261113/selection.json` (SHA-256 `4f31e685…de99a`, matched; `git check-ignore` confirms it is covered by `outputs/`). Sol's private adapter outputs were reloaded but not overwritten.
- **Not done:** no image endpoint, archive, index, SDK sample, download, install, GPU or Colab session, child task, push, PR or merge. CPU Python only: `C:/Users/Advait/ar-work/venv-rtdetrv2/Scripts/python.exe -B`, with `PYTHONPATH=src`.

## Adapter inspection

| Aspect | Finding |
|---|---|
| Purity | The input document and `source` are never written. The image native record and the annotation attributes are deep copies, and `bbox` is a fresh list. `validate_documents` returns deep copies. Full-file check: the native document equals its pre-conversion copy after both profiles, and 0 output bboxes alias native lists. |
| Schema/IDs | Image, annotation and category IDs, plus `image_id`/`category_id` references, must be exact `int` (bool is rejected). Duplicates are refused. References and geometry are validated before the daytime/profile skip, so omitted records are still checked. The category table must equal `{1: pedestrian, 2: bicycledriver, 3: motorbikedriver, 4: ignore}`. |
| Category provenance | Every retained record uses the matching token `human`, and the native `category_id` and flags stay in private attributes. Eligibility is computed only from `cid == 1`, so riders can never be eligible. |
| Groups/nulls | Integer-valued keys map to `nightowls:recording:<int>`. Null stays null and nothing is inferred. On the full manifest the existing `check_roles` still returns **FAIL** in held-out mode (1,318 unknown) and DIAGNOSTIC_ONLY in diagnostic mode. |
| Ignore profiles | Primary keeps categories 2/3/4 as ignored records. Secondary omits them. Ineligible category-1 boxes are ignored in both profiles. Both profiles supply `same_category_ioa`, `allow_outside` and `categories=['human']` to the unchanged evaluator. Synthetic test 4 exercises the matcher order: eligible-first IoU, then reusable IoA absorption at the 0.50 boundary, with sub-40 px detections kept. |
| Geometry | Native xywh values are preserved with their native Python types and are never clipped or repaired. Eligibility uses unclipped `bbox[3] >= 50`. The full file has 2,231 out-of-frame records in primary and 158 in secondary, and all are preserved. |

**Tests:** all six pass in 0.008 s. The fixtures are synthetic: there are no restricted records, the fake `pose_id=999` stands in for an unresolved pose, and `difficult`/`truncated` are set to True to show that they do not affect eligibility. Each test checks something that could invalidate a result: dusk exclusion and empty-frame retention, null-group handling with a held-out FAIL, the ≥50 boundary, null occlusion treated as visible, profile scope with eligible-first matching, purity, and refusal of malformed omitted records. Nothing is missing that would change a conclusion.

## Independent full-JSON recomputation

[`2026-11-13_nightowls_adapter_check.py`](2026-11-13_nightowls_adapter_check.py) restates the policy over native records without using the adapter. It then compares every record's (image, bbox, ignore) triple and the full image→group map with both adapter outputs. It prints aggregates only and runs in about 10 s.

| Quantity | Primary | Secondary |
|---|---:|---:|
| images (native night; 2 dusk excluded) | 51,846 | 51,846 |
| records / eligible / ignored | 17,085 / 7,649 / 9,436 | 10,178 / 7,649 / 2,529 |
| native category mix of records (1/2/3/4) | 10,178 / 326 / 261 / 6,320 | 10,178 / 0 / 0 / 0 |
| known groups / unknown-group images | 5 / 1,318 | 5 / 1,318 |
| eligible in unknown group; per known key (sorted) | 872; 149/291/332/1,006/4,999 | same |
| images without records (natively empty night 42,359) | 42,359 | 45,611 |
| record set and group map equal to independent restatement | yes | yes |
| `ReferenceEvaluator` constructed from provenance policy: GT / images | 7,649 / 51,846 | 7,649 / 51,846 |

Sol's private canonical files (`a79a51cb…`, `359c536d…`) and counts file (`ce225b35…`) have the recorded hashes. Reconverting with Sol's `source` gives documents equal to both saved files.

## Pilot selection check (no endpoint access)

The manifest contains **64** unique night images: **10 in each of the 5 known keys and 14 null**. It has 64 distinct file names. Every record equals its native image record, and none carries annotation or bbox fields. I reproduced the selection exactly from native IDs and recording keys alone, ranking by `SHA256(seed + ":" + str(native_image_id))` within each bucket, ties broken by ID; this is the existing `candidate_pilot.select_images` convention. After the selection was already fixed, I counted only for information: 43 of the 64 frames have no native annotation, and they hold 18 eligible GT in total. Excluding them later is negligible next to the smallest per-key count of 149, and nothing in this review changes the selection.

The limits are as stated in the brief: 150,000,000 body bytes including ≤16 MB of index, 30 minutes, 0 GPU/Colab, 0 retries, no full-archive fallback, and a fixed exclusion of all 64 regardless of retrieval. The plan remains `PROPOSED_NOT_AUTHORIZED` (my explicit consent so far covers annotations only). A rough estimate, which I have not verified: 64 PNGs at about 1.1 MB each (57.5 GB / 51,848) plus a ZIP64 central directory of roughly 5–7 MB fits the caps. Throughput and selective ZIP access remain unverified, and partial completion would be an access outcome, not a research result.

## Findings

No P0–P2 findings in either the adapter or the plan.

- **P3, pilot reproducibility.** The `selection_rule` names "image-ID SHA256 ranks" but does not give the hash input or the tie-break, and no selection script is committed. *Root fix:* add the reproduced formula above to the config.
- **P3, pilot transport guard.** "Stable archive identity" is not defined. *Root fix (one sentence):* any status other than 206, or a missing or mismatched `Content-Range`, stops the run before the body is read, and any bytes read count toward the cap. Every 206 must report the same total length, and `ETag`/`Last-Modified` must not change when the server sends them.
- **P3, pilot privacy.** The private destination for PNGs and logs is not named. *Root fix:* name a gitignored `data/**` path in the config before authorization.
- **P3, cosmetic.** Missing spaces: "All64planned", "all64images", "plus14", "All64".
- **Note, adapter evidence.** The recorded adapter hash `8bc0a660…` matches the LF git blob of `a4bf61b`. The CRLF checkouts in root and this worktree hash to `46390b40…`, which is the same content. A reader should compare blob content, not working-file bytes; this is not a defect.

## Remaining limits

The SDK semantics come from the earlier policy evidence and were not re-verified here. Native box extent, completeness below 50 px, what the publisher means by null occlusion, recording independence and pretraining exposure all remain open. No detection, frozen external validation or IID claim follows from this review. Image acquisition and inference resources need separate explicit authorization from me.

Reproduce: `$env:PYTHONPATH='src'; & 'C:/Users/Advait/ar-work/venv-rtdetrv2/Scripts/python.exe' -B docs/reviews/2026-11-13_nightowls_adapter_check.py PRIVATE_JSON --manifest PRIVATE_SELECTION_JSON`.
