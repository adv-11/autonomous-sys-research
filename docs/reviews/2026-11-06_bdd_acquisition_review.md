# Formal cross-review: GPT BDD acquisition and preflight

**Reviewer: Claude (Opus 5.5), 2026-11-06. Separate delegated review task; not a continuation of Claude's ACDC adapter work and not a human GitHub approval.**

- Target: `gpt-research` at `8460bda2d660a11aacf02d43c32bcbb77f553899`.
- Reviewed delta: `63ab281..8460bda`, which includes the BDD implementation `f099d6c` (integrated as `e988b07`), the coordinator ACDC protocol hold `8c73ffd`, the ACDC archive manifest `4960a68`, and the acquisition record `8460bda`.
- Scope: the acquisition/preflight diff and its underlying evidence. This is not a review of a frozen protocol, an evaluator or research results. G0 remains **pending**.
- Out of scope, by instruction: the ACDC adapter fixes on `claude-research` (`7a030ba`, later `9c5b0a6`). The coordinator says the revised invalid-mask run completed. I did not re-review it.

## Verdict

The tool behaves as described. It is a metadata and condition inspector that cannot emit canonical GT, cannot claim Detection 2020 status and keeps `group_id` null. Every hash, count and digest I re-derived from the actual archives reproduces, with one exception: the Info JSON-parse denominators are off by three (M1). There are no code-level must-fix defects. Two documentation omissions and one attribution inconsistency need correcting before a PR (M1–M3). All three are text-only fixes. After those fixes, I recommend publishing this as a moderate **acquisition/preflight PR**. It must keep the release-identity, revised-label and grouping blockers explicit.

## Must fix before PR

### M1 — Info full-parse denominators double-count three documents (P2, denominators)

- Location: `docs/gpt/bdd_acquisition_info.md:100-104`; the "27,529 complete JSON parse attempts from 72,471 prefix-only" sentence in `docs/data_acquisition.md`; the ignored `bdd_info_inventory.json` `json_syntax_verification` block.
- Cause: in the ignored `bdd_info_inventory_probe.py`, line 20 fully parses every *fallback* record (27,517). Line 28 separately re-reads and fully parses the **first 12 indexed records**, whatever path they took. Reported attempts are 27,517 + 12 = 27,529. Records parsed on both paths are therefore counted twice.
- Evidence: I replicated the probe's iteration order and regex (scratch `first12.py`, aggregate output only). **3 of the 12 sampled records were also fallback full parses.**
- Corrected values: **27,526** distinct records fully parsed; **27,525** parse successes; **1** observed invalid (the zero-byte train member); **72,474** prefix-only records. All `rideID` counts are unaffected. They come from a separate path that I reproduced exactly (below).
- Fix: correct the table and the propagated sentence. Alternatively, relabel 27,529 as "parse operations" and state the distinct-record count. The denominators were the specific claim this note set out to make precise.
- Related reproducibility gap: the preserved probe script does not emit the final inventory's `json_syntax_verification`, `rideID_verification`, `name_join_with_candidate_images`, `uncompressed_member_bytes` or `duplicate_*` fields. These were added afterwards by code that is not preserved in `outputs/acquisition_discovery/`. Either preserve that post-processing step or state that those fields were derived manually from the native index and the ZIP directories.

### M2 — Published package sizes and HTTP re-upload dates are not recorded (P2, release identity evidence)

The pinned [`download.rst` at `9ac17c6`](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/doc/source/download.rst) lists published sizes as well as MD5 values. I fetched it again; it is byte-identical to GPT's saved copy.

| Package | Published size | Acquired candidate |
|---|---:|---:|
| Labels (2018 legacy) | **107 MB** | 189,638,612 B (≈181 MiB) |
| Info | 3.9 GB | 5,116,983,841 B (≈4.77 GiB) |
| 100K Images | 5.3 GB | 5,669,071,832 B (≈5.28 GiB) |
| Detection 2020 Labels | 53 MB | not acquired; the live button serves 231,196,019 B of JPGs |

`bdd_acquisition_info.md` mentions the Info size gap, but `bdd_acquisition.md` omits the legacy-label gap. That gap is ≈1.7×. Together with the unexpected `test` boxes (§ "Real schema"), it suggests a materially different package rather than a re-compressed copy of the 107 MB release. Neither size nor content establishes which release it is.

I also sent plain HTTP `HEAD` requests to the four live files. All four return `Last-Modified: Thu, 06 Feb 2025` (17:01–17:19 GMT), with lengths equal to the local candidates. That supports the "changed container is plausible" wording with dated evidence; it does not resolve identity.

Fix: add both facts, with access dates, to `bdd_acquisition.md` § "Sources and identity".

### M3 — Contradictory attribution for the ACDC train/val overlap check (P3, attribution)

- `docs/gpt/protocol.md:52` and `docs/gate_log.md:59` (coordinator commit `8c73ffd`) say **"GPT independently confirmed"** the 100/56/80/92 val-frame token overlap.
- `docs/gpt/bdd_acquisition_peer_exchange.json` (`disposition.acdc_split_overlap`) and `docs/gpt/bdd_acquisition.md:69` say **GPT did not independently recheck it**.

Both statements may be true of different GPT tasks: the coordinator and the BDD acquisition task. As written, though, a reader cannot tell which applies. The diff also contains no artifact for the confirming check.

Fix: name the task that performed the confirmation and point to its ignored evidence file or commit. Alternatively, add "(BDD acquisition task; see coordinator confirmation in `8c73ffd`)" to the BDD-side wording. CONTRIBUTING requires model-attributed provenance, so this should not be left ambiguous.

## Advisory (no PR block)

**A1 — Output protection covers only the consumed input** (`bdd_legacy_conditions.py:202`, `data.py:159-188`). I passed `--output` as an unrelated existing `precious.zip` in a temporary directory. The command exited 0 and atomically **replaced** it. In this layout, a mistyped `--output` could replace the image or Info archive under `data/bdd100k/archives/`. Consider passing `protected_roots=[<data root>]` and refusing to overwrite an existing output without an explicit flag. This only matters for operator error; the recorded run wrote to `outputs/`.

**A2 — ZIP member checks are strict for JSON members but permissive elsewhere.** These checks passed:

- Duplicates by `orig_filename`
- Windows normalization: `orig_filename != filename`, which also catches embedded NUL truncation
- Backslash, drive colon, absolute and `..` paths
- Symlink mode bits
- Local-header name mismatch (enforced by `zipfile`)

Synthetic probes (scratch `probe_edges.py`) found these accepted:

- Non-canonical paths `100k//train/a.json` and `100k/./train/a.json`. `PurePosixPath` collapses them; the duplicate-name check would catch an alias pair, but a single non-canonical path is recorded verbatim in `source_member`.
- Directory entries outside `100k/` and directory entries carrying a payload. These are skipped without reading, yet `zip_crc` is reported as `"pass"`.
- An empty ZIP, which yields `images: 0` with `zip_crc: "pass"`.
- Case-variant names (`A.json` beside `a.json`). Harmless, since nothing is extracted.

Suggested fix: require `entry.filename == str(PurePosixPath(...))`, validate directory names against `100k/{split}/`, reject directory entries with a nonzero size, and optionally accept an `--expected-members` count. None of these apply to the real archive: it has 100,004 entries (4 directories, 100,000 JSON) and 100,004 distinct `orig_filename`s.

**A3 — JSON boundary edges.**

- `json.loads(bytes)` auto-detects UTF-8 with BOM and UTF-16/32, and both are accepted. The observed format is plain UTF-8; consider requiring `raw.decode("utf-8")`.
- Lone `\ud800` escapes pass `_text` as "nonempty strings". `write_json` escapes them safely through `ensure_ascii`.
- Deeply nested arrays raise `RecursionError`, which `main` does not catch. The CLI then exits 1 with a traceback instead of the controlled exit 2.

Duplicate keys, `NaN`/`Infinity`, overflowing `1e9999` and 400-digit integers are rejected correctly.

**A4 — Prefix scan.** The anchored regex takes the *first* root `rideID`. A later duplicate key, which `json` resolves last-wins, would go unnoticed in prefix-only records. In a seeded random sample of 400 Info members, all 400 parsed fully, 300 had a prefix match, and every prefix value equalled the fully parsed value and the native index. This is sample evidence for the prefix-only population, not a syntax guarantee; the note's limitation wording remains correct.

**A5 — Detection 2020 coverage.** The pinned spec describes Detection 2020 as "validation and testing labels" (53 MB), while the commented-out live button names `bdd100k_det_20_labels_trainval.zip`. When the labels are acquired, verify which splits they cover before relying on them for BDD fine-tuning or source thresholds.

**A6 — Reproduction snippet.** The snippet pins a Python 3.14 interpreter, and the inventory records 3.14.7. The repository requires ≥3.11, and the coordinator's environments are 3.11 and 3.12. I ran the suite on both (below). Listing all three in the note is enough.

## Independently verified

| Claim | Method | Result |
|---|---|---|
| 75 tests, 8 new BDD tests | `unittest discover` with `PYTHONPATH=src` on Python 3.12.14 and 3.11.16 | 75/75 OK on both |
| Legacy archive bytes, MD5, SHA-256 | Full local hash | `189,638,612` / `2d0165fd…` / `7f1f9043…`: match; ≠ official `e21be3e7…` |
| Info archive bytes, MD5, SHA-256 | Full local hash | `5,116,983,841` / `befea4df…` / `862f878c…`: match; ≠ official `043811ff…` |
| Image archive bytes, MD5, SHA-256 | Full local hash | `5,669,071,832` / `c7a1d4db…` / `afd149ea…`: match; ≠ official `5a0359c8…` |
| Published MD5 values (legacy, Det 2020, image, Info) | Re-fetched pinned `download.rst` | Match the documented values; file identical to GPT's copy |
| Legacy inspector output | Re-ran `inspect_legacy_zip` on the real archive | Member digest `b1320dcc…`; per-split boxes, nonpositive boxes, `person` boxes, zero-person images and 0 out-of-nominal all identical; 100,000 index rows, all `group_id` null; stored index SHA-256 `42c7732f…` matches |
| Legacy schema claims | Separate aggregate scan | Box attributes exactly `occluded`/`truncated`/`trafficLightColor`; `direction`/`style` only on non-box objects; box categories are `person`/`rider`/`bike`/`motor`/vehicles/traffic; no `pedestrian`, `other person`, crowd or ignore names or attributes |
| Live page and Detection 2020 button | Plain HTTP GET (no TLS bypass) | Identical to GPT's saved HTML; active button `bdd100k_det_20_labels.zip`; `/2021/…trainval.zip` commented out |
| Wrong Det 2020 package | HTTP range reads of the central directory plus one member | 231,196,019 B; 2,003 members = 2,000 `.jpg` + 3 directories, 0 JSON; sample member 90,563 B, CRC pass, magic `ffd8`; 299,863 B fetched; no full download |
| Info structure | Local central directory | 100,000 non-directory members (70,000/10,000/20,000); 59,600,610,595 uncompressed bytes; 1 zero-byte member; 100,000 distinct names |
| Info `rideID` statistics | Recomputed from the ignored native index (SHA-256 `f9fabd04…` matches) | 99,999 rows; 60,137 distinct; 20,072 reused values / 59,934 records; max 48; per-split distinct 42,166/5,931/12,041; exactly one train/val value (4 train, 5 val records); none with test |
| Info ↔ image join | Split-qualified member names | 100,000 / 0 / 0 |
| ACDC manifest | Re-fetched ETH package API; local files | All 7 package IDs, names and MD5s match the API (`personalData: false`); 6 annotation archives re-hashed: MD5, SHA-256 and member counts match; image archive size and 8,012 PNG members match; 8,012 extracted PNGs; no `.part`/`.tmp`; 3,009 aggregate detection images; seeded sample of 200 (50 per file) all present with matching PNG IHDR dimensions |
| Public-data restrictions | Diff grep | No `rideID` values, BDD basenames, coordinates, GoPro tokens or raw annotations in committed files; the peer exchange discloses its sequence-token redaction |

## Not independently verified

- Full CRC passes of the Info archive (60 GB decompressed) and the image ZIP. I did not repeat them.
- JSON syntax of the ≈72k prefix-only Info records. Only the 400-record sample was checked.
- GPT's 17 image range comparisons against the current Berkeley host.
- Full SHA-256 of the 17 GB ACDC image archive.
- Full 3,009-image ACDC join. I sampled 200.
- ETH DNS failures, the Berkeley HTTPS certificate failure, and the S3, Hugging Face, Kaggle and Internet Archive negative discovery results.
- Whether a lawful revised-label copy exists elsewhere. The documents correctly do not claim it does not.
- The `rideID` field semantics, and whether native values correspond to independent trips.
- Visual correspondence of ACDC pairs, and ACDC grouping.

## Process, voice and claims

- Voice follows AGENTS/CONTRIBUTING: first-person goals ("I need …") with explicit GPT attribution for the work, and no implication that I performed source checks.
- The peer exchange preserves real messages with their IDs and timestamps, including Claude's retracted RLE claim and a failed delivery attempt. It does not infer assent from silence. Redaction is disclosed.
- Claims are bounded throughout: no Detection 2020 substitution, no group claims, no release authentication from partial ranges or name joins, G0 pending, and no inference, training, paid compute or merges.
- The `gate_log.md` statement about the PR #3/#4 merges was not verified against GitHub in this review.

## Publication recommendation

After the text-only corrections M1–M3, publish this as an **acquisition/preflight PR**. Keep these four limits visible in the PR summary: unresolved BDD release identity (MD5 *and* size mismatches), unacquired revised Detection 2020 labels, unresolved BDD/ACDC grouping (null `group_id`; train/val reuse in both datasets), and G0 pending. A1–A6 can be handled in the PR or deferred to the future Detection 2020 converter. They do not affect the recorded real-data results. The coordinator can apply these fixes without another review loop. Re-review is needed only if the code changes substantively.
