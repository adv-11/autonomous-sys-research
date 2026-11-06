# BDD acquisition and schema inspection

**GPT researcher, 2026-11-06; parent `63ab281cd13b2c4ee2bbf21e759195d6b4e93901`. G0 remains pending.**

I need the revised Detection 2020 annotations before freezing the BDD pedestrian population. GPT acquired a real legacy-format candidate and inspected every JSON, but did **not** acquire authenticated Detection 2020 labels. Legacy boxes are not substituted. The new tool exports condition metadata and an inventory only; it cannot create canonical detection ground truth.

## Sources and identity

The [official download specification at `9ac17c6`](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/doc/source/download.rst) distinguishes the deprecated 2018 labels from quality-checked Detection 2020. Published archive MD5 values are `e21be3e7d6a07ee439faf61e769667e4` and `b86a3e1b7edbcad421b7dad2b3987c94`, respectively. Its image MD5 is `5a0359c86a0b8713adab1eee9a3041cb`. Access date for all checks below: 2026-11-06.

The live [Berkeley HTTP download page](http://bdd-data.berkeley.edu/download.html) links the [IP-hosted directory](http://128.32.162.150/bdd100k/). Its active Detection 2020 button points to `bdd100k_det_20_labels.zip`; the older `/2021/bdd100k_det_20_labels_trainval.zip` button is commented out. The active file is 231,196,019 bytes. GPT retrieved its complete ZIP directory: **2,003 members, comprising 2,000 JPG names and three directories, with no JSON**. A decompressed sample passed its member CRC and begins with JPEG magic `ffd8`; it is not merely a misleading extension. This verifies the wrong-package symptom directly, rather than adopting a discussion comment as evidence. The full wrong package was not downloaded or hashed.

The actual acquired [legacy-format candidate](http://128.32.162.150/bdd100k/bdd100k_labels.zip) is retained under the absolute shared ignored path:

```text
C:/Users/Advait/autonomous-sys-research/data/bdd100k/archives/bdd100k_labels.berkeley-candidate.zip
```

- Bytes: **189,638,612**; all 100,000 JSON members read successfully with ZIP CRC verification.
- MD5: `2d0165fd89b11025206e21a25ae1089d` — **does not match** the official legacy archive MD5.
- SHA-256: `7f1f9043c70a6ff0788a323cfb914aeced109a37b7150740d670a347c881394a`.

The primary page associates this public transport endpoint with BDD, but HTTP transport and a mismatching archive checksum do not authenticate the original release. It is a **legacy-schema candidate**, not publisher-verified legacy data and not revised 2020 data. The [pinned data license](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/doc/source/license.rst) permits educational, research and not-for-profit use; GPT used public downloads without an account or acceptance API. Raw files and the derived index remain local and ignored.

### Image discrepancy

The existing [Hugging Face mirror at `c45de4b`](https://huggingface.co/datasets/Xing1210/bdd100k/tree/c45de4b70434647956b4fea75fbbbadc18218f08) has 5,669,071,832 bytes, SHA-256 `afd149eadb49657ef5ad7bb6e9d77cc8b7927a576ee2b475b720028274e02784` matching its LFS object, and MD5 `c7a1d4db9af5a4691d5f6fee2a62e132`, differing from the official image checksum. GPT compared the complete ZIP central directory (including ZIP64 records) and sixteen deterministic 1 MiB payload ranges against the current HTTP Berkeley image archive: all **17 ranges matched**, totaling 27,227,705 bytes. The remote length also matches. Every candidate condition filename joins an image archive member in the same split, with no missing names in either direction.

This supports consistency with the current HTTP host; it does not establish full-file equality, original JPEG identity, or cryptographic publisher authentication. A changed container is plausible, not demonstrated. No publisher checksum for the current HTTP bytes was found (`.zip.md5` returned 404). The image archive remains quarantined. Parent-owned CRC work was not interrupted or independently claimed here.

## Real schema and inventory

All 100,000 JSON documents contain exactly `name`, `attributes`, and `frames`. Every document has one frame with `timestamp: 10000` and `objects`. All contain native `weather`, `scene`, and `timeofday` strings. Objects use integer IDs, native categories, attributes, and either `box2d` or `poly2d`. Box keys are `x1/y1/x2/y2`; native box names include `person`, `rider`, `bike`, and `motor`, alongside vehicles and traffic objects. There are also lane and drivable-area objects. The [official pinned configuration](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/bdd100k/configs/det.toml) contains aliases and ignored mappings, but applying those aliases would not turn these legacy boxes into the revised annotations.

Real candidate counts, **not final eligible denominators**:

| Split | JSON images | Native box objects | Nonpositive boxes | Native `person` boxes | Images without native `person` |
|---|---:|---:|---:|---:|---:|
| train | 70,000 | 1,288,405 | 395 | 91,435 | 47,896 |
| val | 10,000 | 185,578 | 52 | 13,265 | 6,780 |
| test | 20,000 | 367,728 | 107 | 24,650 | 13,787 |

All images have at least one native box; zero-person images are retained in the metadata index. This public candidate unexpectedly includes boxes for the 20,000 filenames under `test`; that does **not** authenticate official revised test labels or authorize a held-out eligibility claim. All 1,841,711 boxes lie within the nominal 1280×720 coordinate range, including degenerate ones; dimensions were not independently read from every image, so this is not full image-coordinate validation. No box was repaired.

Observed box attributes are `occluded`, `truncated`, and `trafficLightColor`. No native `crowd`, `ignore`, `videoName`, recording ID, or trip ID appears in the inspected label schema. Crowd absence is not an official eligibility policy. Unknown recording independence stays unknown; basename prefixes are not groups. Full native flag counts and weather×timeofday image counts are in [the machine-readable summary](bdd_acquisition_inventory.json). Scene-specific counts remain in the ignored full inventory.

## Tool and validation

GPT added `threshold_transfer.bdd_legacy_conditions`, separately named to prevent substitution for a Detection 2020 converter. It requires `--source-kind legacy2018_candidate`, preserves condition values and null group IDs, checks every member CRC, rejects duplicate JSON keys and names, unsafe/duplicate/symlink ZIP members, unknown outer schemas, multi-frame inputs, nonfinite coordinates and ambiguous object IDs. Finite degenerate boxes are counted as defects, never emitted as GT. The output format is **not** `threshold-transfer-v1`; it contains no canonical `images` or `annotations` collections. Ignore policy is explicitly inapplicable because no detection conversion occurs.

Eight synthetic tests cover empty scenes, native names and unknown conditions, geometry defects, malformed JSON, CRC corruption, member attacks, duplicate IDs/names, deterministic member-inventory hashing, CLI behavior, and input preservation. The complete suite passed **75 tests** with `PYTHONPATH=src`. An initial full-suite invocation without that environment variable failed an existing subprocess import; no package installation was used. An initial attack fixture exposed Windows `ZipInfo.filename` normalization; the reader now validates `orig_filename` and the corrected test passes.

The real CLI pass produced 100,000 condition rows in ignored `outputs/acquisition_discovery/bdd_legacy_condition_index.json` (24,029,644 bytes, SHA-256 `42c7732fa375e8b6469e43399088a34e5a293646666f9685ee0565a20a497a6c`). The ordered per-member path/hash inventory digest is `b1320dcc534a0eecb8522a30575b4319e40ec856fd2c9b6dae4e51b2ce93aff5`. These are locally observed reproducibility hashes, not publisher attestations. The raw condition index is not committed.

Reproduce from a checkout without installing anything:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) src)
$python = 'C:/Users/Advait/AppData/Roaming/uv/python/cpython-3.14-windows-x86_64-none/python.exe'
& $python -m unittest discover -s tests -v
& $python -m threshold_transfer.bdd_legacy_conditions `
  C:/Users/Advait/autonomous-sys-research/data/bdd100k/archives/bdd100k_labels.berkeley-candidate.zip `
  --source-kind legacy2018_candidate --include-index `
  --output C:/Users/Advait/autonomous-sys-research/outputs/acquisition_discovery/bdd_legacy_condition_index.json
```

## Direct peer exchange and unresolved work

GPT and Claude exchanged actual scoped messages in their active tasks; [the preserved exchange](bdd_acquisition_peer_exchange.json) records the proposal, responses, correction, and dispositions. Both accepted native category preservation, unknown canonical groups, explicit ignore policy for future detection conversion, and separated archive/JSON/policy provenance as conventions, without changing the shared contract. Claude corrected an initial RLE representation claim; the correction is preserved and the erroneous claim is not accepted as a finding. Claude's reported ACDC sequence overlap is an open protocol issue for the coordinator, not a GPT-verified result or a grouping choice made here. This exchange is not the separate formal review.

Remaining blockers:

- Acquire authenticated revised Detection 2020 JSON. ETH DNS fails locally and Google DNS returns authoritative NXDOMAIN; Berkeley HTTPS fails hostname certificate validation, retained throughout. The live wrong ZIP and commented `/2021/` paths do not provide revised labels; the latter return 404. Guessed old S3 paths returned 404. Public HF repository listings did not reveal the revised label files; the previously reported combined mirror requires authentication. Internet Archive's ETH-file CDX query returned no capture. Public Kaggle discovery did not yield a downloadable revised-label artifact. These checks do not prove no lawful copy exists elsewhere.
- Resolve official image and legacy archive checksum discrepancies before confirmatory use. Partial range matches and filename joins do not resolve them.
- Verify grouping metadata and its semantics before selecting groups. The completed [Info acquisition inspection](bdd_acquisition_info.md) records full archive CRC, JSON parsing denominators, one empty member and native `rideID` reuse across official train/val. Neither the legacy index nor a native field alone establishes independent trips.
- Only after verified revised schema inspection should a separately named detection converter freeze aliases, crowd/ignore behavior, positive-box eligibility, and the exact join to legacy conditions. No final split, inference, training, paid compute, PR, push, merge, or G0 pass occurred in this GPT task.
