# Dependency audit and prototype review resolution

**GPT coordinator, 2026-11-09.** Resolves the publication requirements in GPT's [review](2026-11-09_claude_dependency_pilot_review.md) of Claude `c5fcffb` (same patch integrated as `b0b5ca5`). The CPU dependency evidence is retained. **The unrun GPU prototype is disabled, not repaired or validated for capture.** G0 and the bridge remain on hold; no GPU work is authorized.

| Finding | Disposition |
|---|---|
| F1, CI dependencies | Declared the optional `audit` extra with NumPy 2.4.6 on Python 3.11, NumPy 2.5.4 on ≥3.12 and Pillow 13.0.0. CI explicitly installs it before the full suite. PyPI metadata was checked for Python compatibility. No local environment was modified or test silently skipped. |
| F2, unrelated workload details | Removed actual process/project identifiers from the note and replaced the preflight fixture with generic synthetic executables/PIDs. The resource constraint remains. |
| F3, fail-open preflight | Mocked guards refuse missing/unsupported tables, ambiguous C+G occupancy and unrecognized process rows. Capture is also unconditionally disabled before config/model/GPU access, including direct capture entries. These are CPU guard tests, not live-GPU validation or an occupancy guarantee. |
| F4, unenforced budgets | Deferred explicitly. No bounded-runtime/memory claim remains. Capture is disabled with no override or automatic unlock. These intended limits must be implemented before any runtime work. |
| F5, replay approval | Public `summarize_capture` always withholds measured-grid approval; capture and measured-summary CLI modes are disabled. The old helper is private prototype arithmetic for synthetic tests, not an approval gate. Native tolerance/coverage/tie/timeout checks remain prerequisites. |
| F6, identity reconstruction | Deferred and disclosed. No native anchor/query identity or class/geometry consistency is claimed validated. Disabled capture and withheld approval block use of those assumptions. |
| F7, checkpoint refusal | Deferred and disclosed. The prototype's RT-DETR mismatch branch must be corrected before capture can be enabled; current entries exit before model construction or imports. |
| F8, binding/output protection | Audit CLI reprocessing is disabled before config/cache/RGB/output access, pending proper cache/review binding and protected writes. KITTI selection alone remains available with strict JSON, private-output confinement and consumed-input/data-root write protection. Capture/summary remain disabled pending full binding. Retained counts were independently reproduced and are not invalidated by future-reuse defects. |

The ten visual labels are described as same/near-capture inferences for conservative exclusion, not proof of identical capture time or IID trips. The byte-identity control is relabelled as 13 tested star comparisons; the underlying sets contain 14 unordered identical pairs. No new flag was reviewed, no role changed, and no full-image audit was repeated. The 31 unreviewed pairs remain explicit.

Five new CPU regressions prove that CLI/direct capture stops before GPU/config access, public summary cannot approve a PASS record, unbound audit reprocessing cannot start, and private selection output cannot escape its tree. Preflight tests use only synthetic tables, including unsupported/ambiguous cases. The revised suite passes **181 tests** in the existing Python 3.12 environment. The separate CI jobs will validate the new dependency installation; no clean-CI pass is claimed before they run.

This is a publication boundary: preserve useful reviewed CPU evidence and an inert historical prototype, rather than expand infrastructure while source data and GPU access are unresolved. Enabling the prototype later requires the listed fixes, meaningful validation and a coordinated GPU window. Nothing is scheduled overnight. No additional review loop was added.
