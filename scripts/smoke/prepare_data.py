"""Prepare deterministic COCO val2017 smoke inputs outside Git (Claude, G0 smoke).

Usage: python scripts/smoke/prepare_data.py --config configs/smoke/smoke_config.json

Writes under <work_root>/smoke/data: the selection manifest, canonical annotation
subsets (all 50 images and three disjoint evaluator roles), native COCO subsets for
RT-DETRv2, and a YOLO-format training set. Reads only COCO val2017; no ACDC/BDD.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from threshold_transfer import smoke  # noqa: E402
from threshold_transfer.data import convert_coco  # noqa: E402


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dump(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, allow_nan=False), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    cfg = json.loads(args.config.read_text(encoding="utf-8"))
    det = Path(cfg["det_eval_root"])
    ann_path = det / cfg["coco_annotations"]
    img_dir = det / cfg["coco_images"]
    digest = sha256(ann_path)
    if digest != cfg["coco_annotations_sha256"]:
        raise SystemExit(f"COCO annotation hash mismatch: {digest}")
    coco = json.loads(ann_path.read_text(encoding="utf-8"))
    out = Path(cfg["work_root"]) / "smoke" / "data"

    selection = smoke.select_eval_images(coco, seed=cfg["selection_seed"], quotas=cfg["quotas"])
    eval_ids = [r["image_id"] for r in selection]
    train_ids = smoke.select_train_images(coco, eval_ids, seed=cfg["train_seed"], total=cfg["train_pool_size"])
    roles = smoke.split_roles(selection)

    canonical = convert_coco(coco, dataset_tag="coco-val2017", split="val2017",
                             ignore_policy="coco_iscrowd_v1_provisional",
                             source={"path": str(ann_path), "sha256": digest})
    eval_doc = smoke.canonical_subset(canonical, eval_ids, note="Claude smoke 50-image deterministic selection")
    dump(eval_doc, out / "annotations_eval50.json")
    for role, ids in roles.items():
        dump(smoke.canonical_subset(canonical, ids, note=f"Claude smoke evaluator-CLI role split ({role}); "
                                    "not a condition population"), out / f"annotations_{role}.json")

    dump(smoke.coco_subset(coco, eval_ids), out / "coco_eval50.json")
    dump(smoke.coco_subset(coco, train_ids), out / "coco_train128.json")

    # YOLO-format training set (images copied so the earlier project stays untouched).
    cat_ids = smoke.coco80_category_ids(coco)
    names = {c["id"]: c["name"] for c in coco["categories"]}
    by_image = {}
    for a in coco["annotations"]:
        by_image.setdefault(a["image_id"], []).append(a)
    images = {img["id"]: img for img in coco["images"]}
    yolo = out / "yolo"
    skipped_crowd, label_rows = 0, 0
    for split in ("train",):
        (yolo / "images" / split).mkdir(parents=True, exist_ok=True)
        (yolo / "labels" / split).mkdir(parents=True, exist_ok=True)
    for image_id in train_ids:
        img = images[image_id]
        src = img_dir / img["file_name"]
        dst = yolo / "images" / "train" / img["file_name"]
        if not dst.exists():
            shutil.copyfile(src, dst)
        lines, skipped = smoke.yolo_label_lines(by_image.get(image_id, []), width=img["width"],
                                                height=img["height"], category_ids=cat_ids)
        skipped_crowd += skipped
        label_rows += len(lines)
        (yolo / "labels" / "train" / (Path(img["file_name"]).stem + ".txt")).write_text(
            "".join(line + "\n" for line in lines), encoding="utf-8")
    yaml_lines = [f"path: {yolo.as_posix()}", "train: images/train", "val: images/train", "names:"]
    yaml_lines += [f"  {i}: {names[cid]}" for i, cid in enumerate(cat_ids)]
    (yolo / "data.yaml").write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    strata = {}
    for r in selection:
        strata[r["stratum"]] = strata.get(r["stratum"], 0) + 1
    manifest = {
        "researcher": "Claude", "dataset": "coco-val2017 (local development asset)",
        "annotation_sha256": digest, "selection_seed": cfg["selection_seed"], "train_seed": cfg["train_seed"],
        "rule": "Strata in order, each skipping images already claimed: crowded_count = most non-crowd "
                "person annotations (ties by sha256(seed:image_id)); iscrowd_person = >=1 iscrowd person; "
                "small_person = >=1 non-crowd person with COCO area < 1024; empty = no annotations; "
                "no_person_nonempty = annotations but no person/crowd-person; general = any. Within each "
                "non-count stratum, order by sha256(seed:image_id).",
        "quotas": cfg["quotas"], "strata_counts": strata, "selection": selection,
        "train_pool": {"size": len(train_ids), "includes_eval_images": True, "image_ids": train_ids,
                       "yolo_label_rows": label_rows, "crowd_annotations_skipped_for_yolo": skipped_crowd},
        "evaluator_role_split": {k: v for k, v in roles.items()},
        "eval_population": {"images": len(eval_ids),
                            "person_gt_noncrowd": sum(r["n_person"] for r in selection),
                            "person_crowd_regions": sum(r["n_crowd_person"] for r in selection),
                            "images_without_annotations": sum(r["n_ann"] == 0 for r in selection),
                            "images_without_person": sum(r["n_person"] == 0 for r in selection)},
    }
    dump(manifest, out / "selection_manifest.json")
    print(json.dumps({k: manifest[k] for k in ("strata_counts", "eval_population")}, indent=1))
    print(f"train pool {len(train_ids)} images, {label_rows} YOLO rows, {skipped_crowd} crowd skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
