"""Claude Opus, Stage 0 (local CPU, stdlib): BDD100K legacy 2018 labels -> splits.

Writes private manifests, evaluation GT and the Colab packet under
OUT (gitignored), and the frozen public config + aggregate counts in this folder.
No image, box or per-image ID is written to the repository.

    python -I prep.py --labels <bdd100k_labels.berkeley-candidate.zip> --out <OUT>
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import time
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

LABELS_SHA256 = None  # recorded, not asserted: the candidate archive has no official SHA-256
IMAGES_SHA256 = "afd149eadb49657ef5ad7bb6e9d77cc8b7927a576ee2b475b720028274e02784"
IMAGES_URL = ("https://huggingface.co/datasets/Xing1210/bdd100k/resolve/"
              "c45de4b70434647956b4fea75fbbbadc18218f08/bdd100k_images_100k.zip")
WEIGHTS_SHA256 = "85a76fe86dd8afe384648546b56a7a78580c7cb7b404fc595f97969322d502d5"


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def build(labels_zip):
    """Return (manifests, gt, yolo, counts) from the legacy label archive."""
    manifests = {"source_train": [], "selection": [], "val": {}}
    gt, yolo = {}, {}
    counts = defaultdict(Counter)
    drops = Counter()
    with zipfile.ZipFile(labels_zip) as z:
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            parts = info.filename.split("/")
            if info.is_dir() or len(parts) != 3 or parts[1] not in ("train", "val"):
                continue
            doc = json.loads(z.read(info))
            name, split, attrs = doc["name"], parts[1], doc["attributes"]
            assert name == parts[2].removesuffix(".json")
            boxes, d = C.convert_objects(doc["frames"][0]["objects"])
            drops.update({f"{split}:{k}": v for k, v in d.items()})
            peds = [[x1, y1, x2, y2] for c, x1, y1, x2, y2 in boxes if c == 0]
            if split == "train":
                if not C.is_source(attrs):
                    continue
                role = C.source_role(name)
                manifests["source_train" if role == "train" else "selection"].append(name)
                yolo[name] = C.yolo_lines(boxes)
                keys = ["source_train" if role == "train" else "selection"]
                if role == "selection":
                    gt[name] = {"role": "selection", "peds": peds}
            else:
                stratum = C.primary_stratum(attrs)
                sec = C.secondary_strata(attrs)
                manifests["val"][name] = {"stratum": stratum, "secondary": sec}
                gt[name] = {"role": "val", "stratum": stratum, "secondary": sec, "peds": peds}
                keys = ["val:" + stratum] + ["val2:" + s for s in sec] + ["val:all"]
            for key in keys:
                c = counts[key]
                c["images"] += 1
                c["pedestrians"] += len(peds)
                c["riders"] += sum(b[0] == 1 for b in boxes)
                c["boxes_10class"] += len(boxes)
                c["zero_pedestrian_images"] += not peds
                for p in peds:
                    c["ped_h:" + C.height_bin(p[3] - p[1])] += 1
    manifests["source_train"].sort()
    manifests["selection"].sort()
    return manifests, gt, yolo, {k: dict(v) for k, v in sorted(counts.items())}, dict(drops)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--packet-only", action="store_true", help="rebuild packet; keep frozen config")
    args = ap.parse_args(argv)
    out = args.out
    if args.packet_only:
        return packet(out)
    (out / "private").mkdir(parents=True, exist_ok=True)
    manifests, gt, yolo, counts, drops = build(args.labels)
    assert not set(manifests["source_train"]) & set(manifests["selection"])
    assert not set(manifests["selection"]) & set(manifests["val"])

    files = {
        "manifest_source_train.json": canonical(manifests["source_train"]),
        "manifest_selection.json": canonical(manifests["selection"]),
        "manifest_val.json": canonical(manifests["val"]),
        "gt_pedestrian.json": canonical(gt),
        "yolo_labels_source.json": canonical(yolo),
    }
    hashes = {}
    for fname, data in files.items():
        (out / "private" / fname).write_bytes(data)
        hashes[fname] = sha_bytes(data)

    config = {
        "experiment": "bdd_clearday_transfer_20261115",
        "researcher": "Claude Opus 5.5 (designated executor)",
        "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "labels": {"name": "BDD100K legacy 2018 labels (Berkeley candidate archive; not Detection 2020)",
                   "archive_sha256": sha_file(args.labels)},
        "images": {"name": "BDD100K 100k images, Hugging Face mirror (publisher identity unverified)",
                   "url": IMAGES_URL, "archive_sha256": IMAGES_SHA256},
        "classes": list(C.CLASSES), "legacy_to_class": C.LEGACY_TO_CLASS,
        "dropped_legacy_prefixes": list(C.DROPPED_PREFIXES), "label_drops": drops,
        "source": "train split, weather=clear and timeofday=daytime",
        "selection_split": {"rule": "sha256(salt+image_stem)[:8] as int mod 10000 < 1500",
                            "salt": C.SELECTION_SALT, "never_trained_on": True,
                            "ultralytics_val_set": True},
        "test": "all BDD legacy val images; primary strata mutually exclusive",
        "primary_strata": ["clear_day", "cloudy_day", "rainy_day", "snowy_day", "foggy",
                           "night", "dawn_dusk", "undefined"],
        "secondary_strata": ["night_clear", "night_rain_snow", "rainy_all", "snowy_all"],
        "stratum_rules": "night/dawn_dusk pool all weather; foggy pools all times (descriptive only, n<20); "
                         "cloudy_day = overcast|partly cloudy at daytime; undefined = any undefined attribute otherwise",
        "manifest_sha256": hashes,
        "training": {"framework": "ultralytics==8.4.197", "init": "yolo11s.pt (COCO)",
                     "init_sha256": WEIGHTS_SHA256, "imgsz": 640, "batch": 32, "nbs": 64,
                     "optimizer": "SGD", "lr0": 0.01, "seed": 0, "deterministic": True,
                     "cache": "ram", "workers": 8, "patience": 0, "amp": True,
                     "other_hyperparameters": "Ultralytics defaults (mosaic, close_mosaic=10, lrf=0.01, warmup 3 epochs)",
                     "epochs": "chosen after the throughput pilot from measured throughput only; recorded in an amendment",
                     "evaluated_checkpoint": "last.pt (final epoch, EMA); best.pt retained but not used",
                     "update_counting": "wrap trainer.optimizer_step; success = GradScaler scale not decreased"},
        "inference": {"mode": "native Ultralytics predict", "imgsz": 640, "half": False,
                      "conf_floor": 1e-4, "max_det_cap": 3000, "nms_iou": 0.7, "agnostic_nms": False,
                      "class_filter": "all classes through NMS and cap, then pedestrian class kept",
                      "checkpoint": "last.pt"},
        "evaluation": {"evaluator": "threshold_transfer.metrics.ReferenceEvaluator (IoU>=0.5, greedy score order)",
                       "category": "pedestrian", "ignore_policy": "reject (legacy labels have no ignore/crowd)",
                       "gt_bounds": "original legacy pixel boxes; zero out-of-bounds observed",
                       "recall_targets": [0.8, 0.9, 0.95],
                       "threshold_rule": "highest observed selection-split score with recall>=target (whole ties)",
                       "reference_for_loss": "val clear_day",
                       "height_bins_px": [list(b) for b in C.HEIGHT_BINS],
                       "bootstrap": {"unit": "image", "replicates": 1000, "seed": 20261115,
                                     "assumption": "BDD100K images are keyframes from distinct videos; treated as independent",
                                     "selection_and_test_resampled_independently": True}},
        "budget": {"envelope_CU": 20, "stop_if_L4_rate_CU_per_h_exceeds": 3, "max_failures_per_stage": 2,
                   "sessions": "one at a time, Claude-owned, verified teardown"},
    }
    (HERE / "config.json").write_text(json.dumps(config, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: {kk: v[kk] for kk in ("images", "pedestrians")} for k, v in counts.items()}, indent=1))
    (HERE / "stage0_counts.json").write_text(json.dumps(
        {"note": "Aggregate counts only; BDD100K legacy 2018 labels.", "counts": counts,
         "label_drops": drops}, indent=1) + "\n", encoding="utf-8")

    packet(out)


def packet(out):
    """Colab packet: manifests, YOLO labels, scripts. No images (downloaded in Colab)."""
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    for fname, digest in config["manifest_sha256"].items():
        assert sha_file(out / "private" / fname) == digest, f"{fname} changed after freeze"
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for fname in ("manifest_source_train.json", "manifest_selection.json",
                      "manifest_val.json", "yolo_labels_source.json"):
            tar.add(out / "private" / fname, arcname="packet/" + fname)
        for path in (HERE / "config.json", HERE / "common.py", HERE / "remote.py"):
            if path.exists():
                tar.add(path, arcname="packet/" + path.name)
    (out / "packet.tar.gz").write_bytes(buf.getvalue())
    print(json.dumps({"packet_bytes": len(buf.getvalue()), "packet_sha256": sha_bytes(buf.getvalue())}))


if __name__ == "__main__":
    main()
