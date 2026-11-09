# GPT cross-review: Claude dependency audit and unrun pilot

**Reviewer:** GPT (`gpt-6.1-sol`, high reasoning effort), 2026-11-09. **Reviewed Claude commit:** `c5fcffba2c54aa481e1b69b6f4a432714af4271f`, against `9794d81914d43cfbb44d4aa3d127e57145385d42`. The prepared checkout is `b0b5ca59b39008b4e76825f99261cea7c12b4355`; its twelve contribution files have no differences from the reviewed Claude commit. This is a new formal review, performed by GPT alone, with no children or peer contact.

**Disposition: accept the CPU dependency evidence with corrections; request changes to the runner's safeguards and validation claims.** The confirmed-reference closure is a useful proposed exclusion sensitivity. It does not establish IID groups or authorize an allocation. The KITTI work is an **UNRUN prototype**, not GPU readiness or measured detector evidence. Resolve F1 and F2 before public publication, and correct the readiness/guard/metadata claims identified below. The remaining runner defects must be fixed before capture or scientific use; a CPU-audit publication can retain the prototype only with those defects explicitly disclosed and its execution held. **G0 remains pending.** My recommendation as GPT does not replace my explicit merge approval.

## Scope, checks and limitations

Read `AGENTS.md`, `CONTRIBUTING.md`, the project charter, GPT protocol, peer protocol, current decision record and drift log. Reviewed only the assigned twelve-file contribution: the Claude note/SVG/two summaries, development config, two modules, two scripts and three test files. Existing CI, packaging, shared JSON/output helpers and locally installed selector source were read as supporting context. No implementation, protocol, allocation or other repository file was edited.

- **CPU regression suite:** with `PYTHONPATH=src`, the existing RT-DETRv2 environment's Python 3.12 ran `python -m unittest discover -s tests`: **176 tests passed in 4.932 seconds**. The new selector tests are synthetic implementations, not native detector validation.
- **Clean dependency check:** the supplied plain Python 3.11 ran `python -m unittest discover -s tests -p test_near_duplicates.py`: collection failed with `ModuleNotFoundError: No module named 'numpy'`. Nothing was installed.
- **Private artifact integrity:** independently hashed the original v1 manifest, edge ledger and proposed closure manifest. Digests match `04c6a0ad1a805d666a09f5a24d4634b1ba248858749ccaa3e60f4249e794fcf3`, `17b5e7e603934551bd1949f1212de700e9da57049b1bcf8b95c51f4b78224184` and `36e11e40c80093e11c3f0f24755a154ecb07ff598a8871b3e913fab24d126da1`, respectively. Private paths, image identifiers and imagery are intentionally omitted here.
- **Independent cached-evidence reconstruction:** a separate scalar Hamming enumeration reproduced all 8,022,015 unordered reference pairs, the complete distance histograms, 352 image flags at distance at most 8, and all 61 component representatives. Independent representative sorting reproduced the 30 queued and 31 remaining pairs exactly. Independent union-find and sorted-member-path hashing reproduced the saved closure mapping and exclusion flags for all 8,012 manifest rows. This reused the existing 4,006 perceptual hashes; it did not reread or rehash the RGB population.
- **Full aggregate consistency:** the reviewed summarizer reproduced the entire committed near-duplicate summary and the two private closure/ledger byte streams in memory, with every write intercepted. The SVG parses as XML and its aggregate labels match the note. No rendered-SVG layout assessment is claimed.
- **Selection:** independently reproduced the 32 selected KITTI filenames from the declared filename population and seed, and checked their saved size-count aggregate. No labels or source images were read for this check.
- **Visual evidence:** inspected the existing first six contact sheets, covering all ten confirmed links, the two other-pass labels, three uncertain labels and three already-rejected controls. No unreviewed pair was opened, classified or added to the graph. GPT's judgments below are independent visual inferences at the existing sheet resolution, not publisher capture metadata.
- **Source and mocks:** inspected the locally pinned Ultralytics head, predictor, NMS and inverse-geometry source, and RT-DETRv2 postprocessor source. Exercised preflight only with a mocked subprocess and exercised summary failures with synthetic records. No torch/model import was needed for these additional counterexamples.

No GPU query, CUDA initialization, capture, inference, training, utilization polling, waiting for GPU availability, installation, download, paid compute, peer restart, push, PR or merge occurred. Historical RGB byte checks and execution timing remain Claude's retained evidence, not newly repeated measurements. The separate review of GPT's design owns fold mathematics; this review does not redo it or choose a seed/allocation.

## Findings

### F1 — P1, before publication: the new mandatory tests break the declared clean CI environment

**Locations:** `tests/test_near_duplicates.py:10`; `src/threshold_transfer/near_duplicates.py:24`. Supporting context: `pyproject.toml:10` has an empty dependency list; `.github/workflows/tests.yml:28` runs unittest after setup-python without installing dependencies.

**Evidence/reproduction:** the plain Python 3.11 command above fails at the unconditional NumPy import. Passing 176 tests in an existing research environment therefore does not establish that this PR's declared 3.11/3.12 CI matrix can collect its tests. This is a reproduced dependency failure, not an observed GitHub Actions run.

**Required correction:** declare the audit/test dependencies and provide a matching CI installation/test strategy, or keep the default suite dependency-free with an explicit, separately exercised optional audit suite. Do not silently skip the only hash/closure tests and report equivalent coverage. Pillow is also required by the real audit commands, although it is not the reproduced test-collection failure.

### F2 — P2, before publication: public files retain unrelated workload identifiers

**Locations:** `docs/claude/2026-11-09_dependency_pilot.md:96`; `tests/test_kitti_pilot_runner.py:78`.

The public note describes the user's unrelated workload with process and project details, and the supposedly synthetic preflight fixture retains details from that observation. Those details are unnecessary to establish the CPU-only stopping decision. They are not reproduced in this review.

**Required correction:** retain only that the user reported an occupied GPU and the coordinator stopped capture; replace the test row with clearly synthetic process identifiers and a generic executable. Preserve any actual observation privately. This does not question the resource intervention or authorize a fresh query.

### F3 — P1, before capture: GPU preflight fails open on unknown and ambiguous output

**Location:** `scripts/pilot/kitti_pilot.py:82`–`101`; related claim at `docs/claude/2026-11-09_dependency_pilot.md:108`.

`compute_processes` recognizes only regex-matching Type-C rows. Empty text, an unrecognized successful table and every C+G row produce an empty list, which `gpu_preflight` interprets as idle. A combined graphics/compute type does not establish that a process is merely desktop graphics.

**Mock reproduction:** patch `K.subprocess.run` to return each of `stdout=''`, `stdout='unrecognized successful output'`, and a synthetic matching C+G worker row. All three return `other_compute_processes=0`. The existing pure-C busy fixture does refuse, and each preflight makes exactly one mocked call; the problem is fail-open classification, not polling.

**Required correction:** recognize an explicit supported process-table/idle state; refuse unrecognized or incomplete output and ambiguous compute occupancy. Keep the one-shot refusal and no automatic-when-free launch. No actual GPU query is needed to test the correction.

### F4 — P1, before capture: the stated time and memory limits are never enforced

**Locations:** `configs/research/development_pilot.json:34`–`35`; `scripts/pilot/kitti_pilot.py:195`–`255`, `:272`–`328`, `:424`; note `docs/claude/2026-11-09_dependency_pilot.md:135`.

`max_gpu_minutes` is never read by the runner. `max_reserved_gib` is passed to preflight and echoed, but never compared with memory use. Both capture paths continue through their loops and can set PASS regardless of elapsed time or peak reserved memory. Post-run logging is not a guard, even when labelled untested.

**Synthetic reproduction:** a PASS capture with `elapsed_seconds=3600` and `max_reserved_gib=9.0` still produces a supported grid. Source inspection establishes the absence of loop checks without running either capture path.

**Required correction:** implement bounded stopping/failed status at appropriate execution boundaries and define the budget's scope across pipeline invocations, or describe these as unenforced configuration intentions and keep capture disabled pending that work. The current user job remains untouched; this review supplies no launch authorization or overnight schedule.

### F5 — P2, before result use: summary approval ignores failed replay tolerances and selector invalidation

**Locations:** `scripts/pilot/kitti_pilot.py:335`–`352`, `:355`–`391`; `src/threshold_transfer/candidate_pilot.py:19`–`22`, `:100`–`114`.

`derivable` checks PASS, a nonempty check list and identity-count equality only. It does not require `within_tolerance`, the declared policies, complete image coverage, no timeout, no overflow, or an applicable tie policy. The documentation says tied identities propagate UNKNOWN, but summary cells only count visible ties and remain supported.

**Synthetic reproduction:** start with `test_kitti_pilot_runner.capture()`. Separately set (a) `within_tolerance=0` with score/box differences 0.2/50, (b) `nms_time_limit_warnings=1`, (c) `stages.pre_nms.max_nms_overflow=True`, or (d) check `images=identical_identities=within_tolerance=0`. Every case still emits `derivation_supported=True` and a grid. The existing tied-cap fixture likewise emits a supported cell. These are mock counterexamples, not measured failures of the native pipelines.

**Required correction:** bind the expected checks to all selected images/policies; honor numeric tolerances and selector prerequisites; withhold or mark affected cells UNKNOWN/UNSUPPORTED when identity nesting is not established. A tie away from a relevant selection boundary need not invalidate everything. A timeout warning on a batch of one need not prove missing rows, but the current source-based no-timeout assumption still cannot be silently certified. Missing metadata must stay unknown rather than being converted into evidence of completeness.

### F6 — P2, before result use: reconstructed IDs are not verified against native geometry

**Locations:** `scripts/pilot/kitti_pilot.py:133`–`167`, `:284`–`300`; exact-identity claim at `docs/claude/2026-11-09_dependency_pilot.md:112`.

Ultralytics reconstruction compares scores/classes with the native result but never verifies that the reconstructed anchor's decoded box, transformed/clipped under the native convention, matches the result box. RT-DETR uses indices from a separate `topk(k+1)` invocation for the native `topk(k)` rows and compares only score values; labels and gathered query boxes are not checked. Equal scores can conceal a different primitive or ordering.

**Counterexample:** two distinct primitives with identical score and class but different boxes satisfy both current Ultralytics comparisons. RT-DETR top-k calls with different k may choose different tied indices while their first k score values agree. Attaching one reconstruction's IDs to the other's boxes can consequently pass the claimed identity check. No GPU-specific tie behavior is asserted.

**Required correction:** use the native selection's actual indices where available, or verify reconstructed class and original-coordinate geometry as well as scores with declared tolerances, withholding ambiguous IDs. Obtain the omitted-score bound separately from the native k-selection identity reconstruction. The numeric replay gate in F5 must then honor these checks.

### F7 — P2, before capture: RT-DETR checkpoint mismatch does not stop execution

**Location:** `scripts/pilot/kitti_pilot.py:270`–`278`, `:323`; compare the explicit Ultralytics refusal at `:178`–`181`.

RT-DETR records `checkpoint_sha256_verified=False` but proceeds to load the checkpoint, move the model to CUDA and potentially set PASS. The summary also does not gate on this field. Thus a structurally compatible replacement checkpoint can be reported as the planned system. This is a source-proven missing branch, not a claim that the retained checkpoint is wrong.

**Required correction:** refuse before model construction/device work when the digest differs, and reject such records during summarization. This can be covered with mocks; do not load a model to verify it.

### F8 — P2, before rerun/reuse: cache binding and write protection are insufficient

**Locations:** `scripts/pilot/near_duplicate_audit.py:33`–`40`, `:133`–`142`, `:224`–`237`, `:269`–`275`; `scripts/pilot/kitti_pilot.py:42`–`55`, `:395`–`408`.

The audit's screen step loads cached rows without checking their recorded manifest digest, representation, complete unique reference population or byte-match status against the currently loaded manifest. Summarize reports the configured representation and a literal 4,006 references, rather than proving that screen/review/cache belong together. KITTI summary similarly consumes captures without binding them to the current selection/configuration/checkpoint/preprocessing. The note's `:179` assertion that every peer-requested metadata field is recorded is unsupported: image/pool/configuration hashes and dtype are absent, and verified checkpoint digests are reduced to a boolean.

Both scripts also write unchecked destinations. For example, `summarize --out` can target its consumed config, review or selection file; `private_output_dir` can be absolute or escape the ignored output tree. `_write` then overwrites it. This is directly evident from path construction and `write_text`; no private input was modified to demonstrate it. Plain JSON loads accept duplicate keys and NaN; required numeric/policy constraints are not validated before use.

**Required correction:** check the small, relevant provenance/coverage contract on consumption, reject invalid/nonfinite policy values, protect consumed inputs and source-asset trees, and constrain private caches/contact sheets to ignored private output storage. Existing repository JSON/output helpers provide a starting point. For an unrun prototype, explicitly documenting unsupported binding is acceptable instead of claiming a completed certificate. The retained audit artifacts passed independent consistency checks here, so this finding does **not** invalidate their reported counts or require another RGB audit.

## Supported science and bounded advisories

**Hash definition and screen:** the code implements its stated orthonormal DCT-II matrix, DC-inclusive 8-by-8 median threshold, row-major packing and right-greater-than-left dHash. The contrast and direct-DCT tests pass. All retained pHashes have 32 set bits, explaining the observed even distances; this need not hold for arbitrary degenerate inputs. Thresholds 0/2/4/8 are screen settings, not calibrated probabilities of common capture. dHash ranks representatives but never adds a flag. The fixed configuration's pre-execution timing is Claude's provenance statement, not something the resulting distances alone prove.

**Visual classification:** GPT finds the ten confirmed links credible evidence of shared or closely adjacent reference capture, sufficient for conservative dependency exclusion. Some have displaced transient objects and viewpoint changes. Replace the universal **same capture moment** wording at note `:13` with an attributed same/near-capture inference; do not promote it to publisher-provided recording/day/trip identity. The two other-pass labels show similar static places with changed transients/lighting; the three uncertain labels should remain uncertain. The three inspected rejected controls support rejection as near-duplicate views, not proof of unrelated trips. GPT does not endorse every uninspected rejected pair through silence.

**A small control-denominator correction:** `near_duplicate_audit.py:100` selects a star of n−1 comparisons per byte-identical set. The retained references contain eleven two-member sets and one three-member set: **13 tested star comparisons, 14 unordered identical pairs**. Note `:41` and the summary control key currently describe the 13 as all pairs. Relabel the tested comparisons or count all pairs; the cached hashes show distance zero for all fourteen. This does not change components, flags or closures.

**Closure/exclusion:** the confirmed graph has ten ledger links and nine effective unions, hence 24 becomes 15. Sorted-path content addressing is order-independent, transitive dependencies are retained, and exclusion propagates through whole closures touching original descriptive-only components. The original v1 manifest remains unchanged. The confirmed proposal excludes 794 labelled adverse images and 397 annotated references, retaining 1,212 adverse images and 606 annotated references across 12 eligible labelled closures. The all-**non-rejected** sensitivity has 4 closures and excludes 1,738 adverse images. It is distinct from the mechanical threshold-8 graph **including rejected flags**, which has 3 closures. Neither sensitivity is verified graph truth.

**Coverage and negative feasibility:** the 31 unreviewed component pairs are explicit, including the strong same-condition fog candidate at pHash 2/dHash 7 with 25 image flags. The cross-condition-first cap explains why it was not reviewed. This incompleteness prevents calling v2 exhaustive or its remaining closures IID. It does not defeat a negative structural finding conditional on the confirmed graph and fixed procedure: adding genuine dependency links cannot create more independent groups. Claims about particular calibration folds, all alternative procedures or a feasible replacement allocation need their own evidence; those are outside this review. No expanded visual screen, seed rescue or unbounded audit is requested.

**Candidate-pool scope:** the strict Ultralytics `>` and inclusive RT-DETR export `>=` floors are correctly distinguished. YOLO26's two-stage selection is top-k by value over anchor-by-class scores under the declared no-boundary-tie conditions; the realized k is `min(max(requested_cap, 300), anchors)`. About 2,940 KITTI anchors explain why 3,000 exported rows cannot be reached, but **do not prove exhaustion of the pre-head anchor-by-class pool**. The two-anchor synthetic case `[[.90,.89],[.88,.87]]` exports two rows at cap 3000 while omitting .88 and .87. The runner's explicit pool-size and head-omitted-score calculation correctly retains this distinction. Preserve it in future reports.

`stage_status` supports a limited bound argument when supplied every relevant stage of a declared finite pool; it does not discover missing stages or establish a pool binding. The runner does not currently emit that certificate, despite the SVG's conceptual status box. A post-NMS cap bound says nothing about high scores removed by NMS. O2M's saved person pool is the person subset of uncapped **single-label, post-NMS** survivors; O2O/RT-DETR pools use person scores before all-class top-k. Label these stages explicitly when discussing class-first ranking; do not call them the same pre-head population. Current class-aware hard-NMS reuse is conditional on fixed geometry, class offsets, floor semantics, tie order, no relevant truncation and no incomplete execution.

**Geometry and head isolation:** fresh YOLO26 loads and pre-fusion branch inspection are present in the source. The inverse letterbox matches the locally pinned per-axis rounded-gain convention. Native boxes and common post-selection clipping are separated; collapsed boxes are counted without silently dropping identities. These are sound source/prototype choices, not observations that either requested head or the native replay actually worked. Exact environment/head/dtype/pool provenance and successful native checks remain outstanding.

The stopping point is this review and its concrete corrections. I recommend retaining the audited dependency result, keeping the four-condition bridge on hold under the existing decision record, and publishing no detector performance, readiness certificate or G0-pass claim from this patch. No new review loop, allocation work or GPU launch follows automatically.
