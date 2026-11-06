# BDD Info candidate: integrity and grouping evidence

**GPT researcher, 2026-11-06. Annotation and metadata inspection only; G0 remains pending.**

I need verified recording groups before making held-out threshold-transfer claims. GPT completed the current Info acquisition and inspection; no grouping policy or canonical group assignment is selected here. This note contains aggregate counts and hashes only. Individual identifiers, filenames, coordinates, telemetry traces, and raw JSON remain in the shared ignored data/output directories.

The [live Berkeley download page](http://bdd-data.berkeley.edu/download.html) supplies the Info link to [the public HTTP archive](http://128.32.162.150/bdd100k/bdd100k_info.zip). Access date: **2026-11-06**. The [pinned official download specification](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/doc/source/download.rst) describes GPS/IMU metadata and publishes MD5 `043811ff34b2fca6d50f37d263a65c93` for a 3.9 GB package. The downloaded current bytes differ:

- Local archive: `C:/Users/Advait/autonomous-sys-research/data/bdd100k/archives/bdd100k_info.berkeley-candidate.zip`.
- Bytes: **5,116,983,841**.
- Measured MD5: `befea4df5719118c7a2471ca3ee87220` — **official MD5 mismatch**.
- Measured SHA-256: `862f878ccb6916a36a4628953584a8a7147bc3e88250c2176f91448c270c9c28`.
- All **100,000 non-directory members** were fully decompressed for CRC verification: **pass**, zero unreadable ZIP members. Their total uncompressed size is 59,600,610,595 bytes. Directory structure has 70,000 train, 10,000 val, and 20,000 test JSON names; there are no duplicate member names or basenames.

An interrupted sequential transfer was completed with exact validated HTTP byte ranges; completion was tracked per range rather than inferred from sparse file size. Final hashes and full CRC were computed only after every range completed. HTTP association with the publisher's page does not authenticate the pinned original release. No TLS validation was disabled. This archive remains a candidate with unresolved publisher identity.

## Scope and denominators

The existing scan read the anchored first root `rideID` string from a 4,096-byte JSON prefix when available. It fully parsed fallback documents when that field was not first, plus twelve initial sample documents. Full CRC validation is a separate pass over every member; it does not establish JSON syntax validity.

| Verification | Count |
|---|---:|
| All member records attempted | 100,000 |
| Complete JSON parse attempts | 27,529 |
| Complete JSON parse successes | 27,528 |
| Observed invalid JSON | 1 |
| Zero-byte JSON members | 1 |
| Remaining prefix-only records; complete JSON syntax unverified | 72,471 |
| Unreadable ZIP members in full CRC pass | 0 |
| Successful native `rideID` observations | 99,999 |
| Records without a usable `rideID` observation | 1 |

The zero-byte member is in train and accounts for the single observed JSON decoding failure and missing observation. No missing `rideID` key occurred in successfully fully parsed JSON. The **total invalid-JSON count across all 100,000 records is not established**, because 72,471 records received prefix inspection rather than complete syntax parsing. Successful observation means a native string was read; it does not claim a fully validated document for every such record.

The twelve fully parsed initial documents contain `rideID`, accelerometer/gyro arrays, `timelapse`, `locations`, `filename`, `startTime`, and `endTime`; nine also contain `id` and `gps`. This is a sampled schema observation, not an assertion that every record has every field. The raw sample is not published.

## Native reuse and joins

Among **99,999 successful observations**, there are **60,137 distinct native `rideID` values**. Of these, 20,072 values occur in multiple records; 59,934 records belong to those reused values, and 39,862 observations repeat a value beyond its first occurrence. The largest observed value occurs in 48 image records. These are native field values, not groups inferred from basename prefixes.

Successful observations by official split: 69,999 train, 10,000 val, and 20,000 test. Distinct native values by split: 42,166 train, 5,931 val, and 12,041 test. **One value is shared between train and val**, covering four train and five val records. No observed value is shared between train and test or val and test. This overlap is conditional on the acquired candidate and successful observations; the empty train member has no observed value.

A direct comparison of split-qualified ZIP member paths, replacing only `.json` with `.jpg`, matches **all 100,000 Info names to all 100,000 candidate image names**, with zero missing on either side. All Info basenames likewise match the legacy-condition index. Name agreement does not resolve either archive's official checksum mismatch or verify the revised detection labels.

The field's recurrence is grouping evidence. Its exact semantics, larger route/capture dependencies, and publisher identity remain unresolved; distinct native values are **not proven independent trips**. Canonical `group_id` remains null. The train/val reuse must be addressed in an explicit future grouping policy rather than silently trusting the official split.

Aggregate details are in [the acquisition inventory](bdd_acquisition_inventory.json). Reproducible local evidence, the native index, and the inspection script remain under `C:/Users/Advait/autonomous-sys-research/outputs/acquisition_discovery/` (`bdd_info_inventory.json`, `bdd_info_native_ride_index.json`, `bdd_info_invalid_records.json`, `bdd_info_inventory_probe.py`). These raw/derived files are not committed. No extra acquisition or delegation is required to finish this task. [Detection 2020 access remains unresolved](bdd_acquisition.md); no legacy boxes were substituted and no model run or gate passage is claimed.
