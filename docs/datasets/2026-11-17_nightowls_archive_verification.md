# NightOwls full validation archive verification

GPT Sol performed CPU-only verification on 2026-11-17 Pacific / 2026-11-18
UTC, from `origin/main` `6d18136`. These are actual archive/annotation checks,
not inference, independent peer review or an empirical research result.
**G0 remains pending.** No images were extracted or committed.

Source: `https://thor.robots.ox.ac.uk/nightowls/python/nightowls_validation.zip`.
Private local archive: `C:/Users/Advait/autonomous-sys-research/data/nightowls/full_validation/nightowls_validation.zip`.

- Exact size: **57,481,286,834 bytes**, matching the task and remote range total.
- SHA-256: `6663dc5099714ffb8c18bb37942ce523de9dfdda44327284bdab12354e8fcf9d`.
  No prior **full image-archive** SHA-256 was found in the base repository's
  NightOwls records (earlier hashes identify labels, pilot manifests or partial
  responses). This is the first local reference, not a publisher-authenticated
  checksum or independent origin attestation.
- Member inventory: **51,849 total** = **51,848 PNG images + one directory**.
  There are **no annotation files** in the ZIP. Total uncompressed image bytes:
  **57,595,824,667**.
- Full member CRC/decompression read: **all 51,849 members passed; zero
  failures**. File size/mtime stayed unchanged throughout verification.
  Started 2026-11-18T07:36:26Z; completed 07:43:03Z; total hash + CRC time
  **397.16 seconds**. Aggregate receipt reports `passed: true`.

Annotations are the separate previously acquired `nightowls_validation.json`,
10,696,948 bytes, SHA-256
`584c0dc11f0d086fc5bcbaca0385cf2dd9794074f815f2727fbf9a093fd9a9b6`,
matching the committed [annotation inventory](nightowls_validation_inventory.json).
The complete annotation table's 51,848 unique image basenames exactly equal
the ZIP's 51,848 unique PNG basenames. No member names/boxes/IDs are published.

Verification ran as one hidden background process, base CPython 3.12 with
`-I -B`, launched from the workspace `scripts/` directory; archive/report paths
were arguments. It hashed the full archive, then read **every ZIP member to
EOF** to validate stored CRCs, without extraction. Reproduce using
[`verify_nightowls_archive.py`](../../scripts/data/verify_nightowls_archive.py)
with `ARCHIVE PRIVATE_REPORT --expected-bytes 57481286834 --expected-sha256 SHA`.
The aggregate receipt and stderr stay private under
`outputs/nightowls_verification_20261117/` in the implementation worktree.

The [external contract](../research/2026-11-17_nightowls_external_contract.md)
was first committed at `d59e2186d8f1983dd5ed31a6236a76deb4bc427d`, before any
NightOwls predictions. Real local adapter integration, with original 64 pilot
exclusions, produced 51,782 images for all four setups. Primary GT counts are
7,631 Reasonable; 2,396 Reasonable_small; 1,165 Reasonable_occ=heavy; 10,142 All.
Reasonable has 9,421 ignored records, five known recording keys, 1,304 unkeyed
frames and 860 eligible GT on unkeyed frames. Its category-scope sensitivity
has the same 7,631 eligible GT and 2,520 ignored records. All 42,316 natively
empty cohort frames are retained. These are label counts, not detections.

Ten synthetic NightOwls/ZIP tests and sixteen existing evaluator tests passed
with the specified base interpreter, without installations/downloads. Fixtures
exercise subset boundaries, exclusions, occlusion/riders, grouping, native
geometry, ignore matching, corrupt CRC continuation and reference mismatches.
The private canonical documents passed existing schema validation. The
preparation CLI checks exact label/pilot SHA and archive coverage and restricts
outputs to private data/output locations. No GPU/Colab operation, predictions,
new review task, PR or merge was performed by GPT Sol.

The unauthenticated **ranged HEAD only** returned HTTP 206, exact total size,
ETag `"5ce813b8-d6226d4b2"` and unchanged Last-Modified on
2026-11-18T07:36:48Z (zero body bytes). Recommend **direct source download
inside Colab only**, followed by the exact size/hash checks above. No datasets
may be uploaded from this PC. Colab reachability and sustained download speed
are not established by this Windows HEAD probe; report a direct-download or
credential failure rather than proposing upload.
