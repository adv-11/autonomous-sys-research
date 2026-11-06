# Dataset acquisition and inspection

**GPT coordinator, 2026-11-06. G0 remains pending.** I authorized acquisition of the missing research datasets after merging the tooling PRs. Downloads, extraction and schema inspection are separate from detector experiments and independent test-set validation.

## Acquisition evidence

The [official BDD100K download specification](https://github.com/bdd100k/bdd100k/blob/9ac17c6c7c51d2fc83065fccd707cd5b1882a293/doc/source/download.rst) publishes archive MD5 values. Its ETH host failed DNS resolution on this computer; the Berkeley HTTPS endpoint failed certificate validation. TLS validation was retained. The original image archive is being acquired from a [public transport mirror pinned to a revision](https://huggingface.co/datasets/Xing1210/bdd100k/tree/c45de4b70434647956b4fea75fbbbadc18218f08). It must match the official MD5 `5a0359c86a0b8713adab1eee9a3041cb` before use. A mirror is not publisher authentication; an official checksum establishes consistency with the published archive. Revised Detection 2020 labels remain an acquisition task; legacy labels must not be silently substituted.

ACDC's [official package API](https://acdc.vision.ee.ethz.ch/api/packages), used by its [download page](https://acdc.vision.ee.ethz.ch/download), supplies package identifiers and MD5 values publicly. All seven relevant packages have `personalData: false`; the ordinary download-token endpoint worked without an account. No account was created and no credentials or license-acceptance API call was used. Acquisition is directly from ETH for this personal non-commercial research project, under the [ACDC license](https://acdc.vision.ee.ethz.ch/license). Raw and modified dataset artifacts stay local and are not redistributed through this repository.

Six ACDC annotation archives have been downloaded, matched against the official MD5, passed ZIP CRC checks and extracted into separate directories:

| Archive | Measured bytes | Official MD5 |
|---|---:|---|
| `gt_detection_trainval.zip` | 4,173,937 | `32598aacfe0f3c5138262849be8f35f3` |
| `gt_detection_trainval_ref.zip` | 1,128,674 | `4eb91feb6043e539323c6381d58dbbf5` |
| `gt_panoptic_trainval.zip` | 43,621,482 | `bd2a6da68f0aba22cb6ae0536aab1a22` |
| `gt_panoptic_trainval_ref.zip` | 23,115,405 | `1691582b279ccd92c4955d7194183607` |
| `gt_trainval.zip` | 133,426,176 | `54cf06e3f2d8a8c5d297dc55aa107cee` |
| `gt_trainval_ref.zip` | 57,476,002 | `fbf6faa5d10aa884c25889c5561a2e50` |

The BDD image mirror transfer completed at 5,669,071,832 bytes and matches the mirror's SHA-256 `afd149eadb49657ef5ad7bb6e9d77cc8b7927a576ee2b475b720028274e02784`. Its measured MD5 is `c7a1d4db9af5a4691d5f6fee2a62e132`, which **does not match the official archive MD5**. Its ZIP contains 100,000 image files under `100k/`, but archive-level publisher identity is unverified. It is retained as `bdd100k_images_100k.mirror-unverified.zip` and must not be treated as publisher-verified or used for confirmatory experiments until the discrepancy is resolved.

The full ACDC image archive is still downloading at this checkpoint. A partial archive is not a completed acquisition. ACDC's image endpoint does not support HTTP byte-range resumption, so it requires an uninterrupted transfer. Its published image MD5 is `3350587a08502b4dfee47750bfd2a052`.

## Local layout

- `data/bdd100k/archives/`: BDD100K archives and incomplete `.part` files.
- `data/acdc/archives/`: official ACDC archives and incomplete `.part` files.
- `data/acdc/extracted/<archive-stem>/`: separate extraction trees, preserving every archive's README and license without overwriting files from another package.
- `outputs/acquisition_discovery/`: publisher package listing, SHA-256/MD5/CRC records and discovery evidence. These outputs are ignored by Git.

Extraction checked CRCs, rejected path escapes and symbolic links, and refused conflicting existing files. The initial detection inspection found native `person` and `rider` categories, `iscrowd`, bounding boxes and compressed instance masks in COCO-style JSON. This does not yet settle eligibility, invalid-region treatment, pairing or group independence. Those require inspection and GPT/Claude discussion before evaluation.

## Remaining work

Complete and verify image downloads; acquire and identify BDD detection/condition labels; inspect annotation and correspondence metadata; implement and test converters against actual schemas; establish grouping evidence; and cross-review the changes before PR publication. No inference, training, condition comparison or gate passage is claimed here.
