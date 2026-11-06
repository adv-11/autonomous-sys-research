"""GPT: inspect the observed Berkeley legacy BDD JSON ZIP; never convert its GT.

This deliberately separate metadata tool cannot stand in for Detection 2020.
It reads ZIP members without extraction, checks CRCs by reading every member,
and emits an optional condition index outside the canonical annotation schema.
Archive identity and recording independence remain separate evidence questions.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import stat
import zipfile

from .data import PreflightError, _json_value, write_json

OFFICIAL_LEGACY_MD5 = "e21be3e7d6a07ee439faf61e769667e4"
SOURCE_KIND = "legacy2018_candidate"


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise PreflightError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _constant(value):
    raise PreflightError(f"nonstandard JSON constant: {value}")


def _text(value, what):
    if not isinstance(value, str) or not value.strip():
        raise PreflightError(f"{what} must be a nonempty string")
    return value


def inspect_legacy_zip(path, *, source_kind, include_index=False):
    """Inventory observed legacy shape and preserve conditions, without aliasing.

    ``source_kind`` must explicitly acknowledge legacy candidate status. No
    supplied label, filename, hash, or metadata index authenticates 2020 boxes.
    Unknown condition values remain native; missing keys are counted separately.
    Dimensions are unknown; bounds counts use only a labelled nominal reference.
    Invalid finite geometry is counted, never repaired or made evaluation GT.
    """
    if source_kind != SOURCE_KIND:
        raise PreflightError(f"source_kind must be {SOURCE_KIND}; Detection 2020 unsupported")
    path = Path(path)
    with path.open("rb") as stream:
        sha256 = hashlib.file_digest(stream, "sha256").hexdigest()
    with path.open("rb") as stream:
        md5 = hashlib.file_digest(stream, "md5").hexdigest()
    counts = defaultdict(Counter)
    conditions = defaultdict(Counter)
    fields = defaultdict(Counter)
    names = set()
    seen_members = set()
    index = []
    source_digest = hashlib.sha256()
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        # Reject ambiguous or unsafe archives before consuming any JSON.
        for entry in entries:
            name = entry.orig_filename  # ZipInfo normalizes Windows backslashes in filename.
            parts = PurePosixPath(name).parts
            if (name != entry.filename or name in seen_members or "\\" in name or ":" in name
                    or name.startswith("/") or ".." in parts
                    or stat.S_ISLNK(entry.external_attr >> 16)):
                raise PreflightError(f"duplicate or unsafe ZIP member: {name}")
            seen_members.add(name)
        for entry in sorted(entries, key=lambda e: e.filename):
            if entry.is_dir():
                continue
            parts = PurePosixPath(entry.filename).parts
            if (len(parts) != 3 or parts[0] != "100k"
                    or parts[1] not in {"train", "val", "test"}
                    or not parts[2].endswith(".json")):
                raise PreflightError(f"unexpected legacy member: {entry.filename}")
            raw = archive.read(entry)  # zipfile verifies this member's CRC.
            doc = json.loads(raw, object_pairs_hook=_unique, parse_constant=_constant)
            _json_value(doc)
            if not isinstance(doc, dict) or set(doc) != {"name", "attributes", "frames"}:
                raise PreflightError("expected observed legacy name/attributes/frames object")
            name = _text(doc["name"], "native name")
            if name != PurePosixPath(entry.filename).stem or name in names:
                raise PreflightError("duplicate name or ZIP member/name mismatch")
            names.add(name)
            attrs = doc["attributes"]
            if not isinstance(attrs, dict):
                raise PreflightError("image attributes must be an object")
            for key, value in attrs.items():
                _text(value, f"image attribute {key}")
            frames = doc["frames"]
            if (not isinstance(frames, list) or len(frames) != 1
                    or not isinstance(frames[0], dict)
                    or set(frames[0]) != {"timestamp", "objects"}):
                raise PreflightError("expected exactly one timestamp/objects legacy frame")
            frame = frames[0]
            if type(frame["timestamp"]) is not int or frame["timestamp"] != 10000:
                raise PreflightError("expected inspected keyframe timestamp 10000")
            objects = frame["objects"]
            if not isinstance(objects, list):
                raise PreflightError("objects must be a list")
            split = parts[1]
            c = counts[split]
            c["images"] += 1
            c["frames"] += 1
            conditions[split][json.dumps(attrs, sort_keys=True)] += 1
            for key in ("weather", "timeofday", "scene"):
                c[f"missing_condition:{key}"] += key not in attrs
            local_ids = set()
            boxes = people = 0
            for obj in objects:
                if not isinstance(obj, dict):
                    raise PreflightError("object must be a dictionary")
                fields["object"].update(obj.keys())
                category = _text(obj.get("category"), "native category")
                oid = obj.get("id")
                if (type(oid) not in {str, int} or (isinstance(oid, str) and not oid.strip())
                        or str(oid) in local_ids):
                    raise PreflightError("invalid or duplicate native object id")
                local_ids.add(str(oid))
                oa = obj.get("attributes")
                if not isinstance(oa, dict):
                    raise PreflightError("object attributes must be an object")
                fields["object_attributes"].update(oa.keys())
                c[f"category:{category}"] += 1
                for key, value in oa.items():
                    c[f"native_attribute:{key}:{json.dumps(value, sort_keys=True)}"] += 1
                if "box2d" not in obj:
                    c["objects_without_box2d"] += 1
                    continue
                box = obj["box2d"]
                if not isinstance(box, dict) or set(box) != {"x1", "y1", "x2", "y2"}:
                    raise PreflightError("box2d must have exactly x1/y1/x2/y2")
                xy = [box[k] for k in ("x1", "y1", "x2", "y2")]
                if any(type(v) not in {int, float} or not math.isfinite(v) for v in xy):
                    raise PreflightError("box coordinates must be finite numbers")
                x1, y1, x2, y2 = xy
                boxes += 1
                people += category == "person"
                c[f"box_category:{category}"] += 1
                c["nonpositive_boxes"] += x2 <= x1 or y2 <= y1
                c["outside_nominal_1280x720"] += min(x1, y1) < 0 or x2 > 1280 or y2 > 720
            c["boxes"] += boxes
            c["zero_box_images"] += boxes == 0
            c["zero_native_person_images"] += people == 0
            fields["document"].update(doc.keys())
            fields["frame"].update(frame.keys())
            fields["image_attributes"].update(attrs.keys())
            # This digest is a reproducible ordered member/hash inventory, not
            # the hash of an official source JSON or proof of authenticity.
            source_digest.update((entry.filename + "\0" + hashlib.sha256(raw).hexdigest() + "\n").encode())
            if include_index:
                index.append({"file_name": name + ".jpg", "split": split,
                              "attributes": attrs, "group_id": None,
                              "source_member": entry.filename, "native_timestamp": 10000})
    result = {
        "format": "bdd-legacy-condition-inventory-v1",
        "provenance": {
            "dataset": "bdd100k", "converter": "GPT bdd_legacy_conditions v1",
            "source_kind": SOURCE_KIND,
            "source_files": [{"relative_path": path.name, "sha256": sha256}],
            "source_member_digest_sha256": source_digest.hexdigest(),
            "archive": {"package_id": None, "sha256": sha256, "md5": md5,
                        "official_md5_match": md5 == OFFICIAL_LEGACY_MD5,
                        "official_legacy_md5": OFFICIAL_LEGACY_MD5,
                        "bytes": path.stat().st_size, "zip_crc": "pass"},
            "ignore_policy": "not_applicable_no_detection_conversion",
            "policy_status": "provisional", "official_evaluator_equivalent": False,
            "group_id_status": "unknown_no_independence_inferred",
            "condition_metadata_status": "legacy_candidate_unjoined_to_detection2020",
            "dimensions_status": "unknown_nominal_bounds_reference_only",
            "summary": {"images": len(names), "splits": dict(counts),
                        "observed_fields": dict(fields), "condition_cells": dict(conditions)},
        },
    }
    if include_index:
        result["condition_index"] = index
    _json_value(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--source-kind", required=True, choices=[SOURCE_KIND])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-index", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = inspect_legacy_zip(args.archive, source_kind=args.source_kind,
                                    include_index=args.include_index)
        write_json(result, args.output, protected_inputs=[args.archive])
    except (OSError, ValueError, OverflowError, zipfile.BadZipFile) as error:
        parser.exit(2, f"BDD legacy inspection failed: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
