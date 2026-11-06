# Coordinator resolution of GPT's data-adapter review

**2026-11-05.** The [GPT review](2026-11-05_claude_data_review.md) requested focused corrections to Claude's adapter at `198bd1db859ccc61450c69c792e2dac22908966c`. The coordinator applied the following directly, with nine regression tests reproducing the reported failures. This is a resolution record, not a fabricated additional model review or my approval to merge.

| Finding | Resolution |
|---|---|
| F1: source overwrite | CLI output/input identity and existing-file aliases are checked before processing/writing. Inventory protects its config and configured asset paths/tree. |
| F2: ambiguous JSON/errors | Duplicate keys, nonstandard/nonfinite JSON and invalid metadata are rejected. Expected parse, structure, numeric and filesystem errors use preflight exit 2. |
| F3: partial writes | Output is JSON-validated and fully serialized before creating a temporary sibling file, then atomically replaced. Failures preserve prior output; invalid-box examples use explicit serializable rejection representations. |
| F4: dictionary interface | Histogram keys are strings. Public converter results are JSON-validated, and a direct converter-to-evaluator regression succeeds without a JSON round-trip. |
| F5: category IDs | Category definitions/references use the same int/string canonical-ID policy and collision checks as other native IDs. Original native category IDs remain in provenance. |
| F6: final geometry | Overflow is caught and final float boxes require finite, representable positive extent/area. Reject/exclude policies apply after conversion too; no coordinates are repaired. |
| F7: role consistency | Duplicate images, invalid group IDs, malformed assignments and empty assignments cannot produce PASS. PASS means consistency of declared groups; verified independence is never asserted by this checker. |
| F8: KITTI policy population | Native neighbour exclusions are determined before invalid-box removal; malformed geometry cannot erase the image-exclusion signal. Native flags/reasons are checked first. |
| F9: reported counts | Eight caches hit their declared 300 cap on every image. The reduced diagnostic subset has 2,382 eligible records outside all official difficulty strata; 3,823 describes the complete derived validation population. |

The cap consistency check also recognizes the adapter's `max_raw_det_per_image` field and rejects conflicting cap aliases. The role-check PASS is not the evaluator's held-out validation, and neither authenticates grouping evidence.

Combined validation after these changes: 67 synthetic tests pass. Real converter/evaluator integration is recorded separately in [the integration note](../integration/tooling_preflight.md), with its development-only scope. G0, dataset acquisition, verified groups/conditions, inference provenance and per-model GPU checks remain pending. My explicit approval is required before PR merges.
