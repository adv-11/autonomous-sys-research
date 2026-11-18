"""Claude Opus, amendment 4: freeze the BDD train-night calibration manifest (local CPU, stdlib).

First 2000 BDD legacy TRAIN images with timeofday=night (any weather), ordered by
sha256('bdd-night-calibration-v1:' + stem). None was trained on (training used clear-day only).
Private manifest/GT go to OUT/private; the public record holds counts and hashes only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import common as C  # noqa: E402

SALT = "bdd-night-calibration-v1:"
N = 2000


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    train_source = set(json.loads((a.out / "private/manifest_source_train.json").read_text()))
    selection = set(json.loads((a.out / "private/manifest_selection.json").read_text()))
    night = {}
    with zipfile.ZipFile(a.labels) as z:
        for info in z.infolist():
            parts = info.filename.split("/")
            if info.is_dir() or len(parts) != 3 or parts[1] != "train":
                continue
            doc = json.loads(z.read(info))
            if doc["attributes"].get("timeofday") == "night":
                night[doc["name"]] = doc
    order = sorted(night, key=lambda n: hashlib.sha256((SALT + n).encode()).hexdigest())[:N]
    assert not (set(order) & (train_source | selection)), "calibration overlaps training/selection"
    gt, weather = {}, {}
    for n in order:
        boxes, _ = C.convert_objects(night[n]["frames"][0]["objects"])
        gt[n] = {"role": "nightcal", "peds": [[x1, y1, x2, y2] for c, x1, y1, x2, y2 in boxes if c == 0]}
        w = night[n]["attributes"].get("weather")
        weather[w] = weather.get(w, 0) + 1
    manifest = json.dumps(sorted(order), sort_keys=True, separators=(",", ":")).encode()
    gtb = json.dumps(gt, sort_keys=True, separators=(",", ":")).encode()
    (a.out / "private/manifest_nightcal.json").write_bytes(manifest)
    (a.out / "private/gt_nightcal.json").write_bytes(gtb)
    record = {"rule": f"first {N} train timeofday=night images by sha256('{SALT}'+stem)",
              "train_night_pool": len(night), "images": len(order),
              "pedestrians": sum(len(v["peds"]) for v in gt.values()),
              "weather": dict(sorted(weather.items())),
              "overlap_with_training_or_selection": 0,
              "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
              "gt_sha256": hashlib.sha256(gtb).hexdigest(),
              "labels": "BDD100K legacy 2018 labels"}
    (HERE / "nightcal_manifest_record.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=1))


if __name__ == "__main__":
    main()
