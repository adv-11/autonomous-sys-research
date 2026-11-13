# Head-transfer mechanism checkpoint

I want to explain why a source-selected recall operating point transfers differently between YOLO26's heads before claiming a new method. GPT Sol completed this batch and a separate Sol reviewer reproduced its decisive results. My merge approval remains required; G0 is pending.

- **Measured:** 933 images under four learned-head × postprocessing cells. At the original source thresholds, the night O2O-minus-O2M gap remains eight TP under common top-k and eleven TP under common NMS bundles. Their ceiling-count gaps shrink to minus one and plus one TP. The native ceiling gap therefore cannot be assigned to learned heads alone.
- **Tradeoff:** O2M under top-k has 40 night TP and 461 FP, versus native O2M's 37 TP and 37 FP. This precludes a matched-FPPI or whole-frontier improvement claim. Source-reselected results, every condition and shared/unique object coverage remain reported.
- **Controls:** exact same-forward native replay; corrected historical aggregate reproduction; the original final-five batch correction and unresolved broader historical tensor identity are explicit. Cached post-clipping NMS is an approximation, separately labelled.
- **Incomplete:** expanded ACDC train replication produced no inference results because two transfers failed. The coordinator stopped transport development. This is an execution failure, not a negative detector result or independent replication.
- **Resources:** 2.90 displayed CU, 5,659.954 allocated seconds, two owned sessions stopped. The 30-minute recovery schedule is disabled after research finalization and review; it has no next run.

The [research report](../gpt/2026-11-13_sol_head_policy_mechanism.md), [aggregate](../gpt/2026-11-13_sol_head_policy_mechanism.json), [measured figure](../gpt/2026-11-13_sol_head_policy_factorial.png), [conceptual architecture](../gpt/2026-11-13_sol_head_policy_pipeline.svg), [cached diagnosis](../gpt/2026-11-13_sol_mechanism_diagnosis.md) and [independent review with resolution](../reviews/2026-11-13_head_policy_review.md) preserve evidence and attribution.

The remaining scientific question is whether an identified head-specific ranking signal can improve transferred recall at a comparable false-positive cost on additional data. A global monotone calibrator with source reselection cannot supply that improvement. These observations establish neither a novel method nor causal darkness, independent-scene generalization or driving safety. Another upload-repair loop or a posthoc threshold sweep would not answer that question.

At the original checkpoint, publication stayed on the research branch while PR8 awaited approval. **Publication update, 2026-11-13:** PR8 and the queued dependency-audit PR9 are now merged. The Colab checkpoint is next in the sequential integration queue. No merge bypasses my approval.
