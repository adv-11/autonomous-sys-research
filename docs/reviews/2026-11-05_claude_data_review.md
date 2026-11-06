# GPT formal cross-review: Claude data/cache preflight

**Reviewer:** GPT (gpt-6.1-sol), coordinator-delegated review sub-agent, 2026-11-05.
**Exact reviewed Claude commit:** `198bd1db859ccc61450c69c792e2dac22908966c`, imported from `231c36c940538ed895e21b6b38f77c335e0c7bf2`.
**Prepared checkout:** `b4dcd5e710301b289f052f435c663234c7454d05`. `git diff 198bd1d HEAD -- src/threshold_transfer/data.py tests/test_data.py docs/claude` is empty. Evaluator review fixes are interface context, not the subject of a replacement review.
**Scope:** `data.py`, its 26 tests, compact inventory, implementation/acquisition notes and coordinator integration evidence, against `AGENTS.md`, `CONTRIBUTING.md`, the charter, data contract and GPT/peer protocols.
**Authority:** this is GPT's independent AI review, not my approval of a research merge. I reserve merge approval for GitHub. **G0 remains pending.**

## Recommendation

**Request focused corrections before PR publication.** The recorded file-based development conversions have useful evidence and preserve the main scientific limitations. Reproducible defects remain in source-file protection, JSON failure handling, the direct dictionary interface, category identity, numerical validation and role/policy checks. These need small, local corrections rather than a new experiment or project. The coordinator can fix them directly and add targeted regression checks; no replacement review or review-of-review is requested.

Severity here: **P1** risks loss of source evidence; **P2** is a correctness, provenance or fail-closed interface defect; **P3** is a factual documentation correction. Findings are open at the reviewed SHA; this task makes no implementation edits.

## Findings and reproducible checks

All adversarial inputs below are synthetic. Repros use Python 3.12.14, `PYTHONPATH=src`, and fixture functions from `tests/test_data.py`. Files were created only under the Windows temporary directory. Paths and line numbers refer to the exact reviewed implementation.

### F1 — P1: output paths can overwrite source evidence

**Paths:** `src/threshold_transfer/data.py:84`, `:885`, `:941`.

There is no output/input alias guard. `convert-coco --input gt.json --out gt.json --dataset-tag toy --ignore-policy no_ignore_declared` returns **0** and replaces the native annotation document with canonical output. `convert-legacy --input cache.json --annotations ann.json --out ann.json --map person=person` returns **0** and replaces its annotation input with predictions. `check-roles --annotations ann.json --roles roles.json --mode held_out --out roles.json` overwrites the role configuration even when its result is **FAIL**, exit **3**.

These were actual CLI subprocess checks on disposable fixtures. Code inspection also finds no protection for the inventory configuration or source files reached through that configuration; a full inventory overwrite was not run. The source hash may survive in the result while the hashed source bytes have been destroyed.

**Correction:** reject output paths aliasing any consumed input, including resolved relative paths and existing-file aliases. For read-only inventory, protect the configuration and configured asset tree. Perform this check before opening an output file.

### F2 — P2: the JSON/input error boundary silently accepts ambiguous documents

**Paths:** `data.py:77`, `:367`, `:938`.

`load_json()` uses the permissive stdlib defaults. Replacing a fixture's first `"category_id": 1` with `"category_id": 3, "category_id": 1` still produces **rc=0**, silently choosing `person`. Duplicate keys can likewise conceal contradictory role assignments, vocabulary or policy metadata. JSON `NaN`/`Infinity` and overflowing exponent literals such as `1e309` are accepted by the loader. Nonfinite values outside box/score fields are not consistently checked.

An input containing only `{`, a missing input file and an output directory supplied as `--out` each produced a traceback and **rc=1**, rather than the advertised preflight-error exit **2**. Structurally malformed objects can also escape through ordinary attribute/type errors. Ordinary semantic `PreflightError` cases still correctly return **2**.

**Correction:** reject duplicate keys and nonstandard/nonfinite JSON values, validate expected container/metadata types, and translate expected parse, numeric and filesystem failures into the CLI's concise preflight error. Keep invalid-data exclusions explicit; do not silently select one duplicate value.

### F3 — P2: a failed write destroys an existing result and leaves partial JSON

**Paths:** `data.py:84`, `:189`, `:199`, `:941`.

`write_json()` truncates the destination before serialization finishes, outside the exception boundary. A fixture with native annotation `area: 1e309` converts successfully in memory, then fails during `json.dump(..., allow_nan=False)`. The CLI returned **1**, destroyed a pre-existing output sentinel and left **620 bytes of incomplete JSON**. With `bbox=[0,0,NaN,2]` and `--invalid-box-policy exclude_and_report`, the rejected box is copied unchanged into `invalid_box_examples`, so reporting the exclusion itself makes output serialization fail.

**Correction:** validate/sanitize report values explicitly, serialize before replacing the destination, and use a temporary file plus atomic replacement for completed output. On any validation/serialization/write failure, preserve existing bytes and leave no purported completed artifact. F2's strict loader prevents some cases, but does not make writes atomic or validate public dictionary API inputs.

### F4 — P2: normal prediction dictionaries fail the agreed evaluator interface

**Paths:** `data.py:474`, `:598`; interface check at `schema.py:40`.

`scan_legacy_rows()` creates `label_index_histogram` with integer dictionary keys. That report is embedded in prediction provenance. For an otherwise normal fixture:

```python
ann = D.convert_coco(coco_doc(), dataset_tag="toy", split=None,
                     ignore_policy="no_ignore_declared")
pred = D.convert_legacy_predictions(legacy_cache(),
    category_mapping={"person": "person"}, annotations=ann)
ReferenceEvaluator(ann, pred, categories=["person"],
    ignore_policy="same_category_ioa", bounds_policy="allow_outside")
```

The final call raises `ValueError: expected JSON-compatible value`. Merely stringifying the histogram keys makes the direct call succeed. JSON writing/reloading also stringifies them, and that path succeeds. Thus the coordinator's unchanged-file integration evidence is consistent with this finding; it does not establish the dictionary-to-dictionary interface recorded in the peer discussion.

**Correction:** emit JSON-compatible string keys from the converter and test a direct converter-to-evaluator call, without a serialization workaround.

### F5 — P2: category references bypass native-ID validation

**Paths:** `data.py:148`, `:182`, `:206`.

Image and annotation IDs use `canonical_id`, but category IDs and references use raw Python dictionary equality. In `coco_doc()`, setting the first annotation's `category_id` to **`True`** or **`1.0`** silently resolves to integer category **1**, producing `person`. Setting the category's ID and its references to **`None`** also succeeds. A category with ID `1` and another with ID `"1"` are accepted simultaneously despite the implementation note's general canonical-collision claim.

**Correction:** apply an explicit native category-ID policy to both definitions and references, rejecting bool/float/null identities and detecting collisions under the chosen normalization. Preserve the original native IDs in provenance. Clarify the documented int/string collision rule if categories intentionally differ from other IDs.

### F6 — P2: validation before float conversion does not ensure valid output geometry

**Paths:** `data.py:65`, `:100`, `:207`, `:438`, `:554`.

The following finite, positive-extent legacy rows pass the scan with `invalid_rows={}` and return invalid canonical boxes:

| Native xyxy coordinates | Returned xywh defect |
|---|---|
| `[-1e308, 0, 1e308, 1]` | width becomes `inf` during subtraction |
| `[2**53, 0, 2**53+1, 1]` | distinct integer endpoints become the same float; width becomes `0.0` |

An integer coordinate `10**400` raises uncaught `OverflowError` in `_is_number`. Annotation boxes `[1e308,0,1e308,1]`, `[2**53,0,1,1]` and `[0,0,1e-300,1e-300]` also pass conversion but fail canonical validation because of overflowing edges, unrepresentable positive extent or underflowing area. The downstream evaluator rejects these cases; no incorrect measured result was obtained.

**Correction:** catch numeric overflow and validate the final float box, including representable positive extents, finite edges and positive finite area. Route failures through the existing reject/exclude-and-report policy. Ordinary out-of-bounds boxes should continue to be reported without clipping under the declared report-only policy.

### F7 — P2: malformed role manifests can receive an independence PASS

**Paths:** `data.py:609`, `:618`, `:641`.

`check_roles()` does not validate collection uniqueness or nonempty group identifiers before building its dictionary. This input returns **PASS**, `independent_split_declared=true`, and no limitations:

```python
manifest = {"images": [
    {"image_id": "1", "group_id": "shared"},
    {"image_id": "2", "group_id": "shared"},
    {"image_id": "1", "group_id": "other"}]}
roles = {"1": "source_selection", "2": "clear_test"}
D.check_roles(manifest, roles, mode="held_out")
```

The last duplicate image hides the known shared group. A group ID of `""` or whitespace also counts as known. An empty assignment over an unknown-group manifest receives the same independence PASS with zero checked groups. Actual `None` groups correctly fail when assigned, and ordinary known-group leakage correctly fails in both modes.

**Correction:** validate unique canonical image IDs, valid group IDs and assignment structure before checking overlap; do not make an independence claim for an empty assignment. Describe successful checks as consistency of declared groups, with external grouping evidence still required. This is the adapter's standalone checker, not a re-review of the evaluator safeguards.

### F8 — P2: invalid-box exclusion bypasses KITTI's image-exclusion policy

**Paths:** `data.py:193`, `:294`, `:297`.

In `kitti_doc()`, replace the neighbour record's box with `[1,1,0,9]` and call `convert_kitti_derived(..., policy=D.KITTI_DIAGNOSTIC_POLICY, invalid_box_policy="exclude_and_report")`. The converter retains image **"2"** and reports no neighbour-image exclusions. Without that box mutation, it excludes image "2". `_base_annotations()` removes invalid boxes before the diagnostic policy discovers neighbour records.

The declared policy removes every image containing a neighbour record because the unsupported one-to-one ignore semantics cannot be represented. An invalid box must not silently erase the record's population-exclusion signal and retain other eligible objects from its scene.

**Correction:** derive neighbour-image exclusions from validated native record identities/reasons before box exclusions, or fail explicitly on an invalid neighbour record. Retain the invalid-row and excluded-population accounting.

### F9 — P3: two prose counts do not match the evidence

**Paths:** `docs/claude/data_preflight_implementation.md:50`, `:69`.

- The compact inventory supports **8**, not **11**, caches with `max_raw_det_per_image=300` and `images_at_cap == evaluated_image_count`. The three COCO torchvision caches have null declared raw caps and a maximum of 100 rows/image; do not describe them as hitting a declared 300 cap.
- **3,823** eligible records with `kitti_difficulty=None` belong to the complete derived validation population. Reading the hashed derived JSON and applying the declared neighbour-image exclusion yields **2,382** such records in the diagnostic subset. Its eligible-record difficulty counts are easy **2,589**, moderate **3,566**, hard **2,055**, none **2,382**, totaling **10,592**. Together with **11,646** DontCare copies these reconcile to **22,238** records. Correct Q2's subset count; its qualitative limitation remains valid.

## Contract and provenance checks that hold

- Image/annotation int-to-string coercion, rejection of bool/float IDs there, duplicate canonical image/annotation detection and unknown references are covered by passing tests. Category validation is the exception in F5. All manifest images, including empty images, are preserved. Cache `evaluated_image_ids` must equal the manifest image set; the explicit restriction rejects manifest images never inferred.
- Mappings are explicit and checked against the vocabulary and, when supplied, manifest categories. Unmapped rows are counted. Duplicate torchvision `N/A` entries remain legal only while unmapped; mapping that name is rejected as ambiguous. `person` is not silently equated to `Pedestrian`. Zero-padded original-row candidate IDs preserve deterministic score-tie order, including after exclusions leave gaps.
- Manifest restriction records a SHA-256 of `json.dumps(manifest, sort_keys=True, allow_nan=False)`, not the annotation file's raw bytes. That distinction explains differing digest values and is appropriately named. `excluded_row_count` counts valid rows removed for population restriction; invalid rows were already counted globally, and unmapped rows are counted separately. These counters should be read together, not as interchangeable totals. Scan cap/empty-output counts describe valid scanned rows, not final mapped predictions.
- COCO crowd flags remain explicit; neither provisional policy claims official COCOeval equivalence. KITTI default conversion is blocked. Its ordinary diagnostic path retains DontCare copies per class, preserves native difficulty/occlusion/truncation, removes neighbour-containing images and labels the non-random exclusion. No difficulty, minimum detection height or official per-class IoU rule is applied. F8 concerns the interaction with invalid-box exclusions, not the recorded clean real document.
- Missing groups/condition attributes remain unknown. No converter manufactures recording IDs, weather, clear/shift roles or a held-out inference pipeline. A historical image-level KITTI split is not independent drive grouping. Even a structurally valid caller-declared grouping needs external evidence and an exposure audit.

## Claude Q1–Q4 and integration disposition

The actual implementation prompts were exchanged directly. Claude's final Q1–Q4 message was undeliverable after the GPT implementation task ended; this review received it automatically. No new peer reply was solicited or invented, and silence is not agreement. The answers below are GPT's checks of the coordinator's recorded disposition.

| Question | Review disposition |
|---|---|
| Q1: explicit ignore policy | **Supported.** Default evaluator ignore rejection refuses the crowd fixture; explicit `same_category_ioa` accepts the serialized converter fixtures. The coordinator reports the same refusal/acceptance for both unchanged real pairs. This is diagnostic IoA, not an official benchmark claim. |
| Q2: difficulty limitation | **Supported with F9's count correction.** Code retains native eligible records regardless of difficulty. The diagnostic subset includes 2,382 outside all strata, not 3,823. No difficulty-filtered variant or official-equivalence claim is warranted. |
| Q3: visible cache/exclusion provenance | **Supported for file-based integration.** A synthetic diagnostic transfer preserves the complete annotation and prediction provenance dictionaries exactly in `input_provenance`, including cache policy, invalid-row counts and population restriction. F4 affects direct returned dictionaries. Missing checkpoint/pipeline/group evidence cannot be reconstructed from these fields. |
| Q4: strict-known prediction bounds | **Supported.** Separate synthetic GT and prediction boxes beyond known bounds both fail `ReferenceEvaluator(..., bounds_policy="strict_known")`. The coordinator reports both unchanged real pairs passed this mode. |

The four real canonical documents are not present in this prepared checkout. Their exact output hashes agree between the compact evidence and integration note; this review did not independently rerun their complete evaluator pass. The coordinator's recorded COCO **5,000 images / 123,897 predictions** and KITTI **2,427 images / 101,660 predictions**, explicit-ignore acceptance and unknown-group held-out FAIL remain attributed to coordinator validation. F1–F8 do not establish that those particular clean files or measured counts are wrong.

## Checks performed and evidence limits

- **Tests:** `$env:PYTHONPATH=(Join-Path (Get-Location) src); & C:/Users/Advait/det-eval-2d/.venv/Scripts/python.exe -m unittest discover -s tests` passed **58 tests** (26 data, 32 evaluator/safeguard), Python **3.12.14**. An initial invocation without `PYTHONPATH` had one subprocess import failure; the correctly configured invocation passed. Existing data tests do not cover F1–F8.
- **Synthetic adversarial checks:** CLI source/output aliases, role-config overwrite on FAIL, duplicate keys, malformed/missing JSON, invalid output path, nonfinite native metadata, partial writes, excluded NaN-box reporting, category identity aliases, extreme/underflowing geometry, direct converter/evaluator compatibility, blank/duplicate/empty role inputs, invalid neighbour exclusion, restriction accounting and Q1/Q3/Q4. Nonzero invalid-row counts and a nonnull restriction record survive the Q3 transfer check exactly. Scratch scripts: `%TEMP%/gpt_data_review_repro.py`, `gpt_data_review_evidence.py`, `gpt_data_review_extra.py`, `gpt_data_review_provenance.py`. Repro definitions above do not depend on keeping those temporary files.
- **Real read-only checks:** sibling HEAD is `39c6f6d87df7775c3bf1dd36b8de3990d6a4b217`; Git status was clean before and after inspection. Rehashed both annotation JSONs, YOLO11s and RT-DETR-L weights and the selected `coco__yolo11s` / `kitti__yolo11s_640_ft` compressed caches: all six match compact evidence. The selected cache hashes are `27e3ae0c4feae14cd4884dacb2831f77101d991a81ae1520619b245ea1228187` and `bbd190a38d4bb80d873ba7c7b1452a827e27e3eeb6d4a30b70e5e18f3b41e98b`. Parsed only the existing derived KITTI JSON for the bounded population/difficulty recount. Read the sibling conversion, difficulty/ignore and inference-rounding source without importing its model stack.
- **Inventory limits:** the compact file contains 25 cache entries, six with duplicate `N/A` placeholders, and the five reported zero-area-row counts (2, 90, 3, 26, 8). Hashes identify local bytes, not official origin, licenses or correctness. Image-directory digests are explicitly name/size listings, not content hashes. The all-image dimension audit, raw-label audit and all-cache scans remain Claude's evidence; this review did not repeat a full inventory or infer corruption from not repeating it.
- **Acquisition limits:** the acquisition note distinguishes publisher-stated sizes/schema claims from acquired artifacts, records BDD DNS/TLS failures and unverified registration/download access, and leaves ACDC login requirements, archive layout, extents and masks unresolved. This review did not recheck live sites, independently certify licenses or verify archive contents/MD5s. Source-page observations and agreement-text summaries do not establish lawful access, current availability, usable condition counts or verified independence.

## Publication blockers and remaining prerequisites

Resolve F1–F8 with focused corrections and meaningful regression checks, and correct F9's prose before publishing this implementation as satisfying the stated fail-closed contract. Preserve these original findings and record the coordinator's disposition; do not relabel this review as an approval of later code. No paid compute, new dataset, expanded evaluator feature or replacement delegated review is required to address them.

I still need a reachable official BDD route, my own license/access decisions, exact acquired-and-hashed BDD/ACDC archives, real schema/ontology/ignore/extent inspection, verified recording/correspondence groups and condition counts, grouped role manifests and exposure history, complete frozen inference provenance, and pinned model-specific forward/backward plus evaluation smoke checks. Subsequent statistical validation remains separate. Existing COCO/KITTI replay is development-asset integration, not a held-out/weather experiment. Official AP, OCE and bootstrap implementation are outside this review. **G0 remains pending.**

Only this review document is changed and committed by GPT. No implementation edits, subagents, downloads, accounts, package changes, training, paid compute, push, PR or merge were performed.
