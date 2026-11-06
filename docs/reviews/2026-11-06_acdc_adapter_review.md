# ACDC adapter formal review — GPT

**Reviewer:** GPT (gpt-6.1-sol), 2026-11-06. This is a new formal review of Claude's implementation, not a continuation or reconstruction of the earlier peer exchange.

**Implementation reviewed:** `633c7e05645a49d1dadcf1dde506f7c609c559af`, against `63ab281cd13b2c4ee2bbf21e759195d6b4e93901`. **Coordinator hold reviewed:** `8c73ffdf85fac7e3adf34c3f7fff04c1a1e5cdd2`.

The isolated checkout started at the hold commit. GPT locally merged the implementation for testing; the resulting test tree was `618e2761c2e32ff578a63e62ef7c8e8a8212340d`. Only this review document is authored in the review commit. No implementation, shared/GPT/Claude document, or source asset was edited. No peer/child was contacted, acquisition restarted, package installed, inference/training run, push, PR, or research/main merge occurred.

**Recommendation: request changes on two P2 robustness findings before accepting the adapter's fail-closed guarantee.** The verified snapshot's annotation-only counts and mask geometry are supported. These findings do not invalidate those counts. The protocol hold is appropriate and remains necessary; this review does not authorize adaptation allocation, independent-group inference, or G0 passage. The project owner's explicit GitHub merge approval remains required.

## Must fix

### R1 — P2: malformed collection types can silently discard all annotations

**Location:** [acdc.py:256–266](../../src/threshold_transfer/acdc.py#L256-L266), [298](../../src/threshold_transfer/acdc.py#L298), and [630–632](../../src/threshold_transfer/acdc.py#L630-L632).

The document check verifies the presence of `images`, `annotations`, and `categories`, but never requires list-valued collections. Iterating an empty object succeeds with zero records. With the existing synthetic fixture, replacing `annotations` with `{}` returns a valid canonical document containing three images and **zero annotations**. Replacing both `images` and `annotations` with `{}` returns a valid empty dataset. Canonical validation cannot recover the discarded native collection type. This can silently change denominators and turn labelled frames into empty frames.

Reproduce using `PYTHONPATH=src;tests` and the existing fixture:

```python
from threshold_transfer import acdc as A
from test_acdc import adverse_doc
d = adverse_doc()
d['annotations'] = {}
r = A.convert_acdc(d, split='train', reference=False,
                   ignore_policy='no_ignore_declared')
assert len(r['images']) == 3 and len(r['annotations']) == 0
```

Related malformed values are not normalized into the declared error channel: `annotations=None` and an annotation `category_id=[]` raise uncaught `TypeError`. GPT exercised `main()` against a temporary synthetic extraction with `annotations=null`: the exception escaped, rather than returning 2; no output was written.

**Required disposition:** validate each native collection as a list of objects before iteration, including empty collections, and validate scalar field types before hashing/indexing. Translate malformed-input failures into `PreflightError` at the appropriate parser boundary. Add regression cases for `{}`, `null`, and scalar collections and verify the CLI returns 2 without replacing an existing output. An empty *list* remains valid where intended. Merely catching `TypeError` would not fix the silent-success case.

### R2 — P2: PNG parsing accepts invalid structure and leaks decoder exceptions

**Location:** [acdc.py:171–195](../../src/threshold_transfer/acdc.py#L171-L195); CLI error handling at [630–632](../../src/threshold_transfer/acdc.py#L630-L632).

CRC verification and scanline filter reconstruction work on the inspected valid masks. The chunk parser nevertheless accepts a missing `IEND`, duplicate `IHDR`, unknown critical chunks, and zero-width images. It does not enforce PNG chunk ordering or bounded decompression. A truncated chunk header raises `struct.error`; a CRC-valid `IDAT` containing invalid compressed bytes raises `zlib.error`. Neither is caught by the CLI handler. Thus malformed annotations can be accepted as valid masks or abort inventory outside the documented error handling.

Minimal missing-terminator reproduction, entirely synthetic:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
from test_acdc import png_gray8
from threshold_transfer import acdc as A
with TemporaryDirectory() as tmp:
    p = Path(tmp) / 'mask.png'
    p.write_bytes(png_gray8(2, 1, [[0, 1]], [0])[:-12])
    assert A.read_png_gray8(p) == (2, 1, b'\x00\x01')  # IEND removed
```

Additional executed mutations: insert a second copy of the 25-byte `IHDR` chunk, or insert a CRC-valid `ABCD` critical chunk before `IDAT`; both still return the same pixels. A CRC-valid header declaring width 0, height 1 with one decompressed filter byte returns `(0, 1, b'')`. Truncating the valid file to 37 bytes raises `struct.error`; substituting a CRC-valid `IDAT` body `b'bad'` raises `zlib.error`.

**Required disposition:** enforce a single first `IHDR`, positive supported dimensions, legal critical-chunk/IDAT ordering and a valid terminal `IEND`; reject unsupported critical chunks and incomplete streams. Check chunk bounds before unpacking, bound inflation by the expected scanline size, and report corrupt compressed/chunk data as `PreflightError`. Add structural and truncation tests alongside the existing five-filter/CRC tests. No large allocation or decompression-bomb test was attempted.

## Advisory findings

- **A1 — P3, strict native scalar types:** [acdc.py:226–235](../../src/threshold_transfer/acdc.py#L226-L235), [98–101](../../src/threshold_transfer/acdc.py#L98-L101), [308–311](../../src/threshold_transfer/acdc.py#L308-L311). Python numeric equality allows category-table ID `24.0`, annotation category `24.0`, crowd flag `1.0`, and segmentation dimensions `[8.0, 10.0]` in the fixture. Each mutation was accepted. This is weaker than an exact inspected native schema, although these examples preserve numerical meaning. Require explicit integer/non-bool types where the native schema promises integers; test float/bool aliases separately from unknown values.
- **A2 — P3, filename boundary:** [acdc.py:64–65](../../src/threshold_transfer/acdc.py#L64-L65), [78–84](../../src/threshold_transfer/acdc.py#L78-L84). Regex `$` accepts a final newline. Appending `\n` to both the fixture's `file_name` and `segm_file` passes conversion and retains an unusable Windows path. Use `fullmatch` or an absolute end anchor. Ordinary traversal, mismatched directory/sequence names, and mismatched reference markers are otherwise excluded by the grammar; no traversal bypass was found.
- **A3 — P3, condition-file certification:** [acdc.py:439–447](../../src/threshold_transfer/acdc.py#L439-L447). Building dictionaries by ID hides duplicate records, and category tables are not compared. GPT duplicated the fixture's first fog image and annotation and changed a category name; `exact_aggregate_subset` was still true. Validate uniqueness and compare categories, or narrow the certification's name and document its scope. This does not affect current conversion because aggregate files are the source, and the real rain packaging defect is correctly reported.
- **A4 — P3, provenance completeness/current context:** [acdc.py:579–598](../../src/threshold_transfer/acdc.py#L579-L598) records no consumed panoptic JSON hash or invalid-mask source manifest in the resulting sections. Aggregate detection files and condition files do carry hashes; archive authenticity is separately documented. Referencing auxiliary hashes/manifests would make the complete inventory independently traceable. `PAIR_STATUS` at [52–55](../../src/threshold_transfer/acdc.py#L52-L55) and Claude's historical download-status prose now lag coordinator evidence: preserve their original inspection context, but distinguish RGB path/dimension verification from unverified visual correspondence in future outputs.

## Verification and evidence

GPT read `AGENTS.md`, `CONTRIBUTING.md`, `docs/PROJECT_CHARTER.md`, `docs/collaboration/peer_protocol.md`, `docs/data_contract.md`, and `docs/gpt/protocol.md`, including the allocation hold at line 52. GPT inspected all five implementation-diff files, the inherited JSON/output/schema helpers and held-out group check, the packaged README, and local annotation inputs read-only.

Tests used the existing interpreters, with `PYTHONPATH=src`:

```powershell
& 'C:/Users/Advait/det-eval-2d/.venv/Scripts/python.exe' -m unittest discover -s tests
& 'C:/Users/Advait/AppData/Roaming/uv/python/cpython-3.11-windows-x86_64-none/python.exe' -m unittest discover -s tests
```

**Results:** 88 tests passed on Python 3.12.14 and 88 on Python 3.11.16, including all 21 ACDC tests. Expected negative-test stderr appeared. These are implementation validations, not research results. The existing tests meaningfully exercise geometry, preservation policies, empty images, ID namespaces, pairing, crowd, filters, and output protection; they miss R1/R2 and the advisory edge cases. The new review reproductions were executed as temporary/stdin scripts; implementation tests were not edited.

**Real annotation inventory:** inputs were read from `C:/Users/Advait/autonomous-sys-research/data/acdc/extracted/`. GPT ran `A.inventory(root)` with invalid-mask reading skipped (about 6.8 seconds). Every returned section equalled its committed counterpart, including file hashes, per-condition summaries, mask checks, panoptic comparisons, pairing and sequence diagnostics. GPT also counted raw JSON directly:

| Role | Images | Instances | Person | Rider | Crowd, all classes | Empty images |
|---|---:|---:|---:|---:|---:|---:|
| train | 1600 | 10135 | 1692 | 227 | 304 | 27 |
| val | 406 | 2794 | 529 | 49 | 63 | 8 |
| train_ref | 800 | 9631 | 2045 | 505 | 32 | 1 |
| val_ref | 203 | 2211 | 552 | 71 | 18 | 0 |

**Independent geometry/RLE checks:** the existing environment contains pycocotools 2.0.11, NumPy 2.5.4 and Pillow 13.0.0; nothing was installed. For all 24,771 native annotations, GPT passed their compressed RLE to pycocotools `area` and `toBbox`: zero native area or bbox disagreements. For 51 distinct real instances selected across roles/conditions using smallest/largest human mask area, longest human RLE and smallest crowd masks by category, pycocotools raster decoding equalled reconstruction through the adapter's RLE column iterator pixel-for-pixel. This independently supports compressed signed/delta decoding and original bbox use. A further 500 deterministic random binary masks (NumPy seed 20261106, dimensions 1–44), encoded by pycocotools, passed adapter area, extent and pixel reconstruction checks, including empty masks. The custom decoder was not used as its own encoder oracle.

**Independent PNG/invalid-overlap samples:** GPT selected one image with maximal total person/rider mask area per adverse condition/split: eight PNG decodes matched Pillow bytes, and all per-condition/category invalid-fraction histograms matched independent pycocotools/Pillow calculations for 80 human instances. A second selection used the smallest person per condition/split and smallest person/rider crowd instances where present: six train and four val PNGs, 52 human instances, with exact independent histogram agreement. Fifteen instances in that second selection had more than half their labelled mask pixels invalid (12 train, 3 val). These samples support the policy against automatically ignoring invalid pixels. Selections can overlap; these are sample checks, not new full-population invalid-mask counts. GPT did not repeat the approximately 9.5-minute full invalid-mask pass or independently certify its complete committed histograms/means.

**Panoptic comparisons:** independent counters keyed by full filename, native category, crowd flag, bbox and area confirmed thing-segment totals/exact matches: train 10481/9615, val 2878/2653, train_ref 9630/9625, val_ref 2209/2205. The inventory rerun reproduced the committed near-match and unmatched counts. The code preserves multiplicity, matches exact records first, and limits near matches to the same frame/class/crowd with one-to-one removal. Near matches are greedy bbox comparisons, not mask equivalence, an optimal assignment, or evidence of identical label extent. GPT did not independently audit every near-match pairing or panoptic PNG. Retaining detection boxes and reporting differences is appropriate; the phrase “typically differing by one pixel” was not independently quantified here.

## Protocol and phase disposition

Native `person`/`rider` and the other categories are retained; neither BDD aliasing nor a human union is introduced. `iscrowd` survives conversion, ignore requires an explicit provisional policy, and invalid masks do not modify ignore. Both policies correctly disclaim official evaluator equivalence. Choosing crowd exclusion/IoA absorption and ontology alignment remains protocol/evaluator work before a research run, not a converter decision. Canonical output validation, source relative paths/hashes, and inherited atomic JSON writing are appropriate. Existing CLI tests confirmed refusal to write converted boxes inside the extraction or this repository. Public aggregate inventory and protected canonical dataset output remain distinct.

Independent string-based adverse/reference joins confirmed 800 train and 203 val annotated references, all unique and without orphans: 1003 annotated pairs under the documented stem convention. The packaged README supports scene correspondence, not pedestrian identity or independent recordings. Canonical pair keys are attributes; every group stays null. An exercised `check_roles(..., mode='held_out')` on converted synthetic ACDC returned `FAIL`.

Independent raw filename counts confirmed val frames sharing train sequence tokens: fog 100, night 56, rain 80, snow 92. The hold in `8c73ffd` correctly blocks the earlier train-to-val adaptation allocation until a justified grouping policy and new allocation address sequence/chapter and adverse/reference dependencies. GoPro-number similarity is diagnostic; it does not establish trip boundaries. Source-only descriptive use also does not establish independent groups or bootstrap validity.

**Later acquisition context, not an expanded review target:** GPT read coordinator commit `4960a68`'s `docs/datasets/acdc_archive_manifest.json` using `git show`, plus the shared ignored `acdc_verified_archives.json` and `acdc_image_join.json`. They record all seven archives with official MD5 matches, SHA256 and ZIP CRC checks, completed extraction of 8012 PNGs, and all 3009 detection-manifest paths/dimensions matching. RGB MD5 is `3350587a08502b4dfee47750bfd2a052`. These are coordinator acquisition records; GPT did not repeat the archive/extraction audit. They close the earlier availability/path-dimension limitation, not visual viewpoint correspondence or group independence. The coordinator's `69b6927` integration/test report is context only and was not a new review target.

**Disposition:** retain the supported annotation-only evidence and allocation hold; fix R1/R2 within the adapter's existing scope. Advisory items can be handled directly by the coordinator. No follow-up review task is launched or required by this document. Label completeness, visual extent/occlusion alignment with BDD, official evaluator equivalence, independent recording groups, detector feasibility and all G0 empirical prerequisites remain outside this validation. Only code, synthetic reproductions and aggregate evidence appear here; no dataset images or annotation geometry are redistributed.
