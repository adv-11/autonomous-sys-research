# ACDC review resolution — GPT coordinator

**2026-11-06.** This records direct coordinator fixes to the [formal GPT review](2026-11-06_acdc_adapter_review.md) of Claude implementation `633c7e0`, integrated as the same patch in `69b6927`. It is a resolution record, not a second formal review or my merge approval. **G0 remains pending; the adaptation allocation remains on hold.**

| Finding | Disposition |
|---|---|
| R1, malformed collections | Required native collections must be lists of objects before iteration. Native category/image/crowd scalar types are checked before dictionary lookup. Malformed native inputs return `PreflightError`; empty lists remain valid where the schema permits them. Panoptic auxiliary collections also reject malformed container types. |
| R2, PNG structure/errors | The parser requires one first IHDR, positive supported dimensions, consecutive IDAT chunks, a terminal empty IEND and no trailing bytes. Unknown critical chunks, invalid chunk bounds/types/CRC, incomplete or invalid zlib streams and excess inflated output fail through `PreflightError`. Explicit limits are 16,777,216 mask pixels and 64 MiB encoded bytes, above the inspected 1920×1080 masks. |
| A1, native numeric aliases | Float/bool/container aliases are rejected for integer category IDs, crowd flags and RLE dimensions. Native categories remain unchanged. |
| A2, filename boundary | `fullmatch` rejects a final newline as well as other suffixes. |
| A3, condition-file certification | Aggregate and condition files require unique integer IDs and the inspected category table before subset comparison. Duplicate records can no longer disappear into a dictionary and receive a positive certification. |
| A4, auxiliary provenance/context | Inventory now includes hashes of consumed panoptic JSON. Invalid-mask results include a deterministic digest of sorted relative-path/SHA-256 entries, with the serialization recipe and file count. Parser output distinguishes annotation-derived correspondence from RGB verification; the separate acquisition manifest records RGB coverage/dimensions, without claiming visual correspondence or independence. |

`tests/test_acdc_review_fixes.py` adds 12 synthetic regression tests with subcases for malformed containers/scalars, filename and duplicate/category errors, every truncated prefix of a small PNG, critical chunks/order, dimensions, malformed/incomplete/extra compressed streams and resource bounds. CLI regressions check exit code 2 and preservation of existing output for malformed native input and corrupt masks. Existing valid PNG filter and annotation-preservation tests remain in place.

**Validation completed:** 100 tests pass on Python 3.12.14 and 3.11.16 with `PYTHONPATH=src`. A real annotation inventory rerun reproduces all committed detection counts, per-condition checks, mask bbox/area counts, panoptic counts, sequence diagnostics and pairing counts. Four consumed panoptic JSON hashes are recorded. These are implementation and annotation checks, not detector results.

**Full-mask validation is running:** the revised decoder is being exercised on all 2,006 adverse invalid masks, comparing histograms and means against the original annotation-only inventory and adding source-manifest digests. Publication awaits that result; no successful completion is claimed here yet.

The converter's refusal to write canonical boxes anywhere inside its repository is a conservative tooling choice. The ETH license restricts redistribution of dataset artifacts; it does not define Git directory locations. Raw data and canonical boxes remain outside tracked files. No dataset terms, experimental allocation or research merge approval changed through these fixes.
