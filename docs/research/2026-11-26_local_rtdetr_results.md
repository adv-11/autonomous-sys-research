# Local RT-DETRv2 measured results

GPT Sol executed this locally amended study; Claude Opus medium contributed
scientific design and interpretation limits. Independent completed-result
review remains separate. G0 remains pending. No merge approval is implied.

Declared baseline: 20 epochs; both continuations: five
epochs / 8,000 images; physical batch 16; training seed zero.
Final declared EMA only. All selection/validation images remain outside training.

| Arm | Source threshold (FPPI ≤ 1) | Night recall | Night FPPI | Clear recall | Clear FPPI | Night ceiling |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.344468 | 0.5916 | 0.6503 | 0.6898 | 1.0913 | 0.8196 |
| day_control | 0.349570 | 0.5899 | 0.6859 | 0.6865 | 1.0896 | 0.8160 |
| adaptation | 0.338108 | 0.5955 | 0.5912 | 0.6931 | 1.1026 | 0.8354 |

## Paired changes at the source-selected FPPI policy

Intervals use 1,000 paired image bootstrap replicates with source threshold
reselection. They condition on the trained seed and do not cover route or
training-seed variation. Recall and actual FPPI changes are reported together.

| Contrast | Condition | Recall change [95% interval] | FPPI change [95% interval] |
|---|---|---:|---:|
| adaptation_minus_day_control | clear_day | +0.0065 [-0.0040, +0.0160] | +0.0130 [-0.0471, +0.0624] |
| adaptation_minus_day_control | night | +0.0056 [-0.0087, +0.0159] | -0.0947 [-0.1217, -0.0624] |
| day_control_minus_baseline | clear_day | -0.0033 [-0.0088, +0.0055] | -0.0017 [-0.0380, +0.0317] |
| day_control_minus_baseline | night | -0.0018 [-0.0090, +0.0053] | +0.0356 [+0.0153, +0.0580] |
| adaptation_minus_baseline | clear_day | +0.0033 [-0.0056, +0.0142] | +0.0113 [-0.0448, +0.0533] |
| adaptation_minus_baseline | night | +0.0039 [-0.0098, +0.0123] | -0.0590 [-0.0835, -0.0283] |

## Source-recall sensitivities

| Arm | Source target | Status | Night recall | Night FPPI | Clear recall | Clear FPPI |
|---|---:|---|---:|---:|---:|---:|
| baseline | 0.8 | FEASIBLE | 0.7548 | 4.5442 | 0.8249 | 6.8503 |
| baseline | 0.9 | INFEASIBLE | — | — | — | — |
| baseline | 0.95 | INFEASIBLE | — | — | — | — |
| day_control | 0.8 | FEASIBLE | 0.7524 | 5.0896 | 0.8257 | 7.3475 |
| day_control | 0.9 | INFEASIBLE | — | — | — | — |
| day_control | 0.95 | INFEASIBLE | — | — | — | — |
| adaptation | 0.8 | FEASIBLE | 0.7668 | 4.1476 | 0.8339 | 6.8764 |
| adaptation | 0.9 | INFEASIBLE | — | — | — | — |
| adaptation | 0.95 | INFEASIBLE | — | — | — | — |

## Execution evidence

| Arm | Epochs | Seconds | Attempted updates | Successful updates | AMP skips |
|---|---:|---:|---:|---:|---:|
| baseline | 20 | 28464.8 | 13300 | 13289 | 11 |
| day_control | 5 | 2849.1 | 2500 | 2494 | 6 |
| adaptation | 5 | 2835.6 | 2500 | 2494 | 6 |

Aggregate results SHA256: `289547702fcbfa2051d51fa461d2f9979c17069b37eca12e9ba638dee191c2cb`.
Private evidence retains raw query logits/boxes/native candidates, checkpoint
hashes, optimizer/scaler/EMA state, full curves, runtime records and failures.

Ordinary adaptation is not a novel method. The mixed arm adds 4,000 unseen
night images while day training images are reused; this combines night content
with image novelty. A recall gain with increased FPPI or lower clear recall is
a tradeoff. An interval crossing zero leaves a difference unestablished, not
equivalent. Candidate-ceiling improvement is useful but not required for a
better ranking/tradeoff. Test curves are descriptive, not replacement policies.
The local environment differs from Colab; numerical equivalence is not claimed.
Exact YOLO1280 seed repeats remain deferred because their original memory
requirement exceeds this GPU. No external-dataset inference was added.
