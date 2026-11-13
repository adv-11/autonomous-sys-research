# Information versus processing scale

GPT Sol, 2026-11-11; base `f95952e2da74ca71102a922032c1583cfbe84d4a`. Design only; no inference or fresh empirical verification. I want to explain the retained resolution gain before proposing a method. G0 remains pending; I approve merges explicitly.

The [checkpoint](../research/2026-11-10_checkpoint.md), coverage [diagnosis](2026-11-10_astra_coverage_diagnosis.md)/[opportunity note](2026-11-10_astra_scale_opportunity.md), and recovered [Astra publication review](../reviews/2026-11-10_empirical_checkpoint_review.md) establish whole-pipeline sensitivity, including normal-reference gains. They do not establish that additional image detail was necessary. Prior results/review remain attributed to their original models; the publication review is not repeated.

## Prior overlap and decision

Two primary methods checked on 2026-11-11:

- Hu/Ramanan, *Finding Tiny Faces*, CVPR 2017, pp. 951–959: [venue record](https://openaccess.thecvf.com/content_cvpr_2017/html/Hu_Finding_Tiny_Faces_CVPR_2017_paper.html) and [indexed method text](https://openaccess.thecvf.com/content_cvpr_2017/papers/Hu_Finding_Tiny_Faces_CVPR_2017_paper.pdf) describe scale-specific templates, context and an inference pyramid including 2× upsampling with specialized heatmaps.
- Singh/Davis, *An Analysis of Scale Invariance in Object Detection—SNIP*, CVPR 2018, pp. 3578–3587: [primary PDF](https://openaccess.thecvf.com/content_cvpr_2018/papers/Singh_An_Analysis_of_CVPR_2018_paper.pdf), indexed §3, explicitly compares downsampled/upsampled inputs and resolution-specific classifiers; SNIP selects valid object-size ranges across pyramid scales.

Identities and these excerpts were checked; both direct PDFs returned 403. Full-method/code inspection and replication were **not** completed; no mirror hunt followed. Neither excerpt establishes this exact frozen-YOLO control. Nevertheless, recovering detection through enlargement without new captured detail is established prior art. Reject that generic novelty hypothesis; using recall thresholds instead of AP creates no novelty. The sole unresolved question is how much of this checkpoint's gain survives removal of additional detail. This supports one explanatory diagnostic, with no demonstrated residual method contribution.

## Decisive three-arm control

Reuse the frozen 700-image packet/metadata; no new scan. Construct all three inputs anew:

1. Decode once using the retained decoder; assert manifest dimensions; RGB float32 `/255`. For original W₀,H₀, set r=1280/max(W₀,H₀), w=floor(rW₀+.5), h=floor(rH₀+.5). Resize to w,h with CPU torch bilinear, antialias=True, align_corners=False; edge replication. Pad to 1280² with 114/255: left=floor((1280−w)/2), top analogously; remainder right/bottom. Call this H.
2. L=resize(H,640²), same antialiased operator. U=resize(L,1280²), bilinear, antialias=False, align_corners=False, edge replication. No intermediate quantization. All sampling uses half-pixel centers: source index=(j+.5)/scale−.5. Feed contiguous RGB NCHW tensors directly; bypass automatic resizing/letterboxing.
3. Convert GT xywh to continuous xyxy with x₂=x+width, y₂=y+height. Map edges once: x'=left+x·w/W₀, y'=top+y·h/H₀. Preserve eligibility, crowd/ignore and out-of-frame policy; no rounding/clipping of GT or integer/+1 area convention. Evaluate every arm against these identical canvas GT. After native NMS, clip predictions to their own full canvas, then multiply L coordinates by exactly two; never round/unpad. Padding detections receive ordinary FP/ignore handling; zero-area outputs remain explicit FP. Reversed/nonfinite outputs invalidate the run.

Reuse existing native inference/evaluators and retained torch 2.14.1/Ultralytics 8.4.197. Freeze checkpoint, float32, batch eight, class-0 decoding/NMS, floor .0001, cap 3000, IoU .70 and tie rules. Save pre-NMS per-GT best-IoU/count summaries after floor/before cap, post-NMS outputs and cap/timeout events. H−U measures degradation at fixed grid; U−L measures enlargement without new image information, including anchors, interpolation and NMS—not isolated stride. Constructed L differs from historical native640; old counts cannot substitute for its measurements.

## Hypothesis, metric and stopping rule

Let M be one-to-one IoU≥.50 all-output recall on pooled adverse GT. Hypothesis: M_H>M_L and M_U−M_L≥0.5(M_H−M_L)>0. The half-gain criterion is prospective for this diagnostic. Kill if either fails; retain signed gained/lost GT and H−U. Candidate-reusing pre-NMS coverage diagnoses suppression/localization; it is not evaluator recall or an isolated anchor effect.

Secondary: per-arm .90 thresholds selected only on COCO source at highest feasible observed boundaries, inclusive whole ties, with infeasibility preserved; report recall/FPPI including empty images, normal/COCO-reference controls. No target-tuned rescue. Retain provisional human/crowd/zero-area task, COCO exposure/non-clear-day uncertainty and exploratory dependent ACDC limits. Output agreement cannot expose common misses; no causal-night/population guarantee follows.

If explanation merits compute, next run is these three arms only: coordinator-owned Colab L4, ≤40 minutes including retrieval/teardown, estimated ≤1.294 CU at last measured 1.94 CU/hour; rate must be rechecked. Historical empirical use .98 CU; throughput unknown. No allocation now, framework, training, fusion/gating reopening or publication claim.
