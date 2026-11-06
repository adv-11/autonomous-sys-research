"""Fail-closed ACDC detection-annotation inspection and canonical conversion (Claude implementation).

Scope (see ``docs/claude/acdc_annotation_adapter.md``):

* strict parsing of the official ACDC COCO-style detection JSON (``gt_detection`` and
  ``gt_detection_ref`` packages), including its compressed-RLE ``segmentation``;
* conversion to the ``threshold-transfer-v1`` canonical annotation document, preserving
  native ACDC category names (``person``, ``rider``, ...), ``iscrowd``, sequence/frame
  tokens and the adverse/normal-reference linkage as attributes;
* an annotation-only inventory: box geometry, box versus RLE-mask extent, empty images,
  crowd flags, condition counts, per-condition file consistency, cross-check against the
  panoptic package, reference-pair coverage and (optionally) invalid-mask overlap.

Policies are explicit and fail closed. Nothing here repairs boxes, aliases ``person`` to
BDD ``pedestrian``, merges ``person``/``rider``, turns invalid-mask pixels into ignore
regions, or turns a GoPro sequence token or reference pair into an independent group.
``group_id`` is always null. Only the Python standard library is used; ACDC data are
read from a local extraction outside Git and never written back into the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from .data import (PreflightError, _check_box_xywh, _checked_result, _json_value, load_json,
                   sha256_file, write_json)
from .schema import SCHEMA_VERSION, validate_documents

CONDITIONS = ("fog", "night", "rain", "snow")
SPLITS = ("train", "val")
# Observed in every ACDC v1 detection file inspected (2026-11-06). A different category
# table means a different annotation revision: refuse rather than guess.
EXPECTED_CATEGORIES = {
    24: ("person", "human"), 25: ("rider", "human"), 26: ("car", "vehicle"),
    27: ("truck", "vehicle"), 28: ("bus", "vehicle"), 31: ("train", "vehicle"),
    32: ("motorcycle", "vehicle"), 33: ("bicycle", "vehicle"),
}
ANNOTATION_KEYS = {"area", "bbox", "category_id", "id", "image_id", "iscrowd", "segmentation"}
IGNORE_POLICIES = {
    # ignore := False everywhere; native iscrowd retained for the evaluator to decide.
    "no_ignore_declared",
    # ignore := native iscrowd. A provisional research policy, not ACDC's official scoring.
    "acdc_iscrowd_v1_provisional",
}
PAIR_STATUS = ("documented_naming_convention: the ACDC README names reference files by the "
               "adverse image's {sequence}_frame_{frame} stem with a _ref marker; the "
               "correspondence is a scene/viewpoint pairing, not an independent group; "
               "this annotation parser does not verify RGB coverage or visual correspondence")
MAX_MASK_PIXELS = 16_777_216
MAX_MASK_PNG_BYTES = 64 * 1024 * 1024
GROUP_STATUS = ("unknown: ACDC sequence tokens are GoPro file/chapter names (GOPRnnnn, "
                "GP01nnnn, ...), not verified independent trips; group_id is null")
AGGREGATE_FILES = {
    ("train", False): "gt_detection_trainval/gt_detection/instancesonly_train_gt_detection.json",
    ("val", False): "gt_detection_trainval/gt_detection/instancesonly_val_gt_detection.json",
    ("train", True): "gt_detection_trainval_ref/gt_detection/instancesonly_train_gt_ref_detection.json",
    ("val", True): "gt_detection_trainval_ref/gt_detection/instancesonly_val_gt_ref_detection.json",
}
_NAME = re.compile(r"^(fog|night|rain|snow)/(train|val|test)(_ref)?/([A-Za-z0-9]+)/"
                   r"\4_frame_(\d{6})_rgb(_ref)?_anon\.png$")
_GOPRO = re.compile(r"^(?:GOPR|GP\d\d)(\d{4})$")


# ------------------------------------------------------------------ native parsing


def parse_file_name(name: Any) -> dict:
    """Parse ``{condition}/{split}[_ref]/{seq}/{seq}_frame_{frame}_rgb[_ref]_anon.png``.

    The two ``_ref`` markers must agree. The returned ``pair_key`` is the README naming
    stem shared by an adverse image and its normal-condition reference.
    """
    match = _NAME.fullmatch(name) if isinstance(name, str) else None
    if not match or bool(match.group(3)) != bool(match.group(6)):
        raise PreflightError(f"unexpected ACDC file_name {name!r}")
    condition, split, ref, sequence, frame = match.group(1, 2, 3, 4, 5)
    return {"condition": condition, "split": split, "reference": bool(ref),
            "sequence": sequence, "frame": frame,
            "pair_key": f"{condition}/{split}/{sequence}_frame_{frame}"}


def gopro_recording(sequence: str) -> str | None:
    """Return the 4-digit GoPro file number shared by chapters, or None if not GoPro-like.

    Diagnostic only: shared numbers suggest (but do not prove) one physical recording.
    """
    match = _GOPRO.match(sequence)
    return match.group(1) if match else None


def parse_segmentation(value: Any, height: int, width: int) -> list[int]:
    """Parse ACDC's ``{"size": [h, w], "counts": str}`` compressed COCO RLE into run lengths."""
    if (not isinstance(value, dict) or set(value) != {"size", "counts"}
            or not isinstance(value["size"], list) or len(value["size"]) != 2
            or any(type(v) is not int for v in value["size"])
            or value["size"] != [height, width] or not isinstance(value["counts"], str)):
        raise PreflightError("segmentation must be {'size': [h, w], 'counts': str} matching the image")
    return decode_rle_counts(value["counts"], height * width)


def decode_rle_counts(text: str, pixels: int) -> list[int]:
    """Decode COCO's compressed RLE string (pycocotools ``rleFrString``), then validate."""
    counts: list[int] = []
    position = 0
    while position < len(text):
        value, shift, more = 0, 0, True
        while more:
            if position >= len(text):
                raise PreflightError("truncated RLE")
            char = ord(text[position]) - 48
            if not 0 <= char < 64:
                raise PreflightError("invalid RLE character")
            value |= (char & 0x1F) << (5 * shift)
            more = bool(char & 0x20)
            position += 1
            shift += 1
            if not more and char & 0x10:
                value |= -1 << (5 * shift)
        if len(counts) > 2:
            value += counts[-2]
        counts.append(value)
    if any(c < 0 for c in counts) or sum(counts) != pixels:
        raise PreflightError("RLE run lengths are negative or do not cover the image")
    return counts


def rle_extent(counts: list[int], height: int) -> tuple[int, list[int] | None]:
    """Return (foreground pixel count, inclusive-pixel bbox [x, y, w, h] or None).

    COCO RLE is column-major: pixel index p is column p // height, row p % height.
    """
    area, start = 0, 0
    x0 = y0 = None
    x1 = y1 = -1
    for index, run in enumerate(counts):
        if index % 2 and run:
            end = start + run - 1
            first_col, last_col = start // height, end // height
            if first_col == last_col:
                top, bottom = start % height, end % height
            else:  # a run crossing a column boundary spans every row (as pycocotools toBbox)
                top, bottom = 0, height - 1
            x0 = first_col if x0 is None else min(x0, first_col)
            x1 = max(x1, last_col)
            y0 = top if y0 is None else min(y0, top)
            y1 = max(y1, bottom)
            area += run
        start += run
    if x0 is None:
        return 0, None
    return area, [x0, y0, x1 - x0 + 1, y1 - y0 + 1]


def rle_columns(counts: list[int], height: int):
    """Yield (column, row_start, row_end_exclusive) foreground segments."""
    start = 0
    for index, run in enumerate(counts):
        if index % 2 and run:
            position, end = start, start + run
            while position < end:
                column, row = divmod(position, height)
                stop = min(end, (column + 1) * height)
                yield column, row, row + stop - position
                position = stop
        start += run


def read_png_gray8(path: Path) -> tuple[int, int, bytes]:
    """Decode grayscale8 masks; reject invalid structure and bound input/inflation.

    Supported masks have at most MAX_MASK_PIXELS pixels and MAX_MASK_PNG_BYTES
    encoded bytes. These resource limits exceed the inspected 1920x1080 masks.
    """
    with Path(path).open("rb") as source:
        data = source.read(MAX_MASK_PNG_BYTES + 1)
    if len(data) > MAX_MASK_PNG_BYTES:
        raise PreflightError(f"{Path(path).name}: PNG exceeds the encoded mask size limit")
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise PreflightError(f"{Path(path).name}: not a PNG")
    position, idat, header, idat_ended, ended = 8, [], None, False, False
    while position < len(data):
        if len(data) - position < 12:
            raise PreflightError(f"{Path(path).name}: truncated PNG chunk")
        length, kind = struct.unpack_from(">I4s", data, position)
        end = position + 12 + length
        if length > 0x7fffffff or end > len(data):
            raise PreflightError(f"{Path(path).name}: invalid PNG chunk length")
        if any(not (65 <= c <= 90 or 97 <= c <= 122) for c in kind) or kind[2] & 32:
            raise PreflightError(f"{Path(path).name}: invalid PNG chunk type")
        body = data[position + 8:position + 8 + length]
        if zlib.crc32(kind + body) != struct.unpack_from(">I", data, position + 8 + length)[0]:
            raise PreflightError(f"{Path(path).name}: corrupt PNG chunk")
        if header is None and kind != b"IHDR":
            raise PreflightError(f"{Path(path).name}: IHDR must be the first PNG chunk")
        if kind == b"IHDR":
            if header is not None or length != 13:
                raise PreflightError(f"{Path(path).name}: duplicate or malformed IHDR")
            header = struct.unpack(">IIBBBBB", body)
            width, height = header[:2]
            if (header[2:] != (8, 0, 0, 0, 0) or not 0 < width <= 0x7fffffff
                    or not 0 < height <= 0x7fffffff or width * height > MAX_MASK_PIXELS):
                raise PreflightError(f"{Path(path).name}: unsupported grayscale8 dimensions or format")
        elif kind == b"IDAT":
            if idat_ended:
                raise PreflightError(f"{Path(path).name}: IDAT chunks must be consecutive")
            idat.append(body)
        elif kind == b"IEND":
            if length or not idat or end != len(data):
                raise PreflightError(f"{Path(path).name}: invalid IEND or trailing PNG data")
            ended = True
            break
        elif not kind[0] & 32:
            raise PreflightError(f"{Path(path).name}: unsupported critical PNG chunk")
        elif idat:
            idat_ended = True
        position = end
    if header is None or not ended:
        raise PreflightError(f"{Path(path).name}: PNG is missing IHDR or IEND")
    width, height = header[0], header[1]
    expected = height * (width + 1)
    try:
        decoder = zlib.decompressobj()
        raw = decoder.decompress(b"".join(idat), expected + 1)
    except zlib.error as error:
        raise PreflightError(f"{Path(path).name}: invalid PNG compressed stream") from error
    if (len(raw) != expected or not decoder.eof or decoder.unconsumed_tail or decoder.unused_data):
        raise PreflightError(f"{Path(path).name}: incomplete or oversized PNG compressed stream")
    out = bytearray(width * height)
    previous = bytearray(width)
    for row in range(height):
        kind = raw[row * (width + 1)]
        line = bytearray(raw[row * (width + 1) + 1:(row + 1) * (width + 1)])
        if kind == 1:
            for i in range(1, width):
                line[i] = (line[i] + line[i - 1]) & 0xFF
        elif kind == 2:
            line = bytearray((a + b) & 0xFF for a, b in zip(line, previous))
        elif kind == 3:
            for i in range(width):
                line[i] = (line[i] + ((line[i - 1] if i else 0) + previous[i]) // 2) & 0xFF
        elif kind == 4:
            for i in range(width):
                a = line[i - 1] if i else 0
                b, c = previous[i], (previous[i - 1] if i else 0)
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 0xFF
        elif kind != 0:
            raise PreflightError(f"{Path(path).name}: unknown PNG filter {kind}")
        out[row * width:(row + 1) * width] = line
        previous = line
    return width, height, bytes(out)


# --------------------------------------------------------------------- conversion


def _native_records(doc: Mapping[str, Any], key: str) -> list[dict]:
    if not isinstance(doc, dict) or not isinstance(doc.get(key), list):
        raise PreflightError(f"{key} must be a list of objects")
    records = doc[key]
    if any(not isinstance(record, dict) for record in records):
        raise PreflightError(f"{key} must be a list of objects")
    return records


def _categories(doc: Mapping[str, Any]) -> dict[int, str]:
    observed = {}
    for record in _native_records(doc, "categories"):
        if not isinstance(record, dict) or set(record) != {"id", "name", "supercategory"}:
            raise PreflightError("unexpected ACDC category record")
        if type(record["id"]) is not int:
            raise PreflightError("native category id must be an integer")
        if record["id"] in observed:
            raise PreflightError(f"duplicate category id {record['id']!r}")
        observed[record["id"]] = (record["name"], record["supercategory"])
    if observed != EXPECTED_CATEGORIES:
        raise PreflightError("ACDC category table differs from the inspected v1 table")
    return {cid: name for cid, (name, _) in observed.items()}


def _role(split: str, reference: bool) -> str:
    return f"{split}_ref" if reference else split


@_checked_result
def convert_acdc(doc: Mapping[str, Any], *, split: str, reference: bool, ignore_policy: str,
                 source: Mapping[str, Any] | None = None, check_masks: bool = True) -> dict:
    """Convert one ACDC aggregate detection file to a canonical-v1 annotation document.

    Fails closed on: unknown keys/categories, non-integer or duplicate native IDs,
    unexpected file names, split/reference mismatch, invalid or out-of-bounds boxes,
    malformed RLE, and (with ``check_masks``) area different from the RLE pixel count.
    """
    if split not in SPLITS or not isinstance(reference, bool):
        raise PreflightError(f"split must be one of {SPLITS} and reference a bool")
    if not isinstance(ignore_policy, str) or ignore_policy not in IGNORE_POLICIES:
        raise PreflightError(f"ignore_policy must be explicitly one of {sorted(IGNORE_POLICIES)}")
    if not isinstance(doc, dict) or not {"images", "annotations", "categories"} <= set(doc):
        raise PreflightError("ACDC detection document needs images, annotations, categories")
    _json_value(doc)
    for key in ("images", "annotations", "categories"):
        _native_records(doc, key)
    if set(doc) - {"images", "annotations", "categories", "info", "licenses"}:
        raise PreflightError(f"unexpected top-level keys {sorted(set(doc) - {'images', 'annotations', 'categories'})}")
    if source is not None:
        if not isinstance(source, dict):
            raise PreflightError("source must be an object")
        _json_value(source)
    names = _categories(doc)
    role = _role(split, reference)
    images, by_native, pair_keys = [], {}, set()
    image_keys = {"file_name", "height", "id", "width"} | (set() if reference else {"segm_file"})
    for record in doc["images"]:
        if not isinstance(record, dict) or set(record) != image_keys:
            raise PreflightError(f"unexpected ACDC image keys {sorted(record) if isinstance(record, dict) else record!r}")
        native = record["id"]
        if isinstance(native, bool) or not isinstance(native, int) or native in by_native:
            raise PreflightError(f"invalid or duplicate native image id {native!r}")
        width, height = record["width"], record["height"]
        if any(isinstance(v, bool) or not isinstance(v, int) or v <= 0 for v in (width, height)):
            raise PreflightError(f"image {native}: invalid dimensions")
        parsed = parse_file_name(record["file_name"])
        if parsed["split"] != split or parsed["reference"] != reference:
            raise PreflightError(f"image {native}: file_name split/reference disagrees with {role}")
        if not reference:
            expected = record["file_name"].replace("_rgb_anon.png", "_gt_labelIds.png")
            if record["segm_file"] != expected:
                raise PreflightError(f"image {native}: unexpected segm_file")
        if parsed["pair_key"] in pair_keys:
            raise PreflightError(f"duplicate ACDC frame {parsed['pair_key']}")
        pair_keys.add(parsed["pair_key"])
        attributes = {"condition": parsed["condition"], "reference": reference,
                      "native_image_id": native, "native_sequence": parsed["sequence"],
                      "native_frame": parsed["frame"], "acdc_pair_key": parsed["pair_key"],
                      "dimension_source": "annotation_json"}
        if not reference:
            attributes["native_segm_file"] = record["segm_file"]
        image = {"image_id": f"acdc:{role}:img{native}", "file_name": record["file_name"],
                 "width": width, "height": height, "group_id": None, "split": role,
                 "attributes": attributes}
        images.append(image)
        by_native[native] = image
    annotations, seen = [], set()
    mask = Counter()
    for record in doc["annotations"]:
        if not isinstance(record, dict) or set(record) != ANNOTATION_KEYS:
            raise PreflightError("unexpected ACDC annotation keys")
        native = record["id"]
        if isinstance(native, bool) or not isinstance(native, int) or native in seen:
            raise PreflightError(f"invalid or duplicate native annotation id {native!r}")
        seen.add(native)
        image = by_native.get(record["image_id"]) if isinstance(record["image_id"], int) else None
        if image is None or isinstance(record["image_id"], bool):
            raise PreflightError(f"annotation {native}: unknown image {record['image_id']!r}")
        if type(record["category_id"]) is not int or record["category_id"] not in names:
            raise PreflightError(f"annotation {native}: unknown category {record['category_id']!r}")
        if type(record["iscrowd"]) is not int or record["iscrowd"] not in (0, 1):
            raise PreflightError(f"annotation {native}: iscrowd must be 0/1")
        reason = _check_box_xywh(record["bbox"])
        if reason:
            raise PreflightError(f"annotation {native}: {reason}")
        x, y, w, h = record["bbox"]
        if x < 0 or y < 0 or x + w > image["width"] or y + h > image["height"]:
            raise PreflightError(f"annotation {native}: bbox outside known image bounds")
        area = record["area"]
        if isinstance(area, bool) or not isinstance(area, int) or area <= 0:
            raise PreflightError(f"annotation {native}: area must be a positive integer")
        if check_masks:
            counts = parse_segmentation(record["segmentation"], image["height"], image["width"])
            pixels, extent = rle_extent(counts, image["height"])
            if pixels != area:
                raise PreflightError(f"annotation {native}: area differs from RLE pixel count")
            mask["mask_bbox_equal" if extent == record["bbox"] else "mask_bbox_differs"] += 1
        annotations.append({
            "annotation_id": f"acdc:{role}:a{native}", "image_id": image["image_id"],
            "category": names[record["category_id"]], "bbox": [float(v) for v in record["bbox"]],
            "ignore": ignore_policy == "acdc_iscrowd_v1_provisional" and bool(record["iscrowd"]),
            "iscrowd": bool(record["iscrowd"]),
            "attributes": {"native": {"category_id": record["category_id"], "area": area}},
        })
    result = {
        "schema_version": SCHEMA_VERSION, "images": images, "annotations": annotations,
        "provenance": {
            "dataset": "acdc", "converter": "threshold_transfer.acdc.convert_acdc",
            "role": role, "source_files": [dict(source)] if source else [],
            "ignore_policy": ignore_policy, "policy_status": "provisional",
            "official_evaluator_equivalent": False,
            "categories": sorted(names.values()),
            "native_category_ids": {name: cid for cid, name in sorted(names.items())},
            "dropped_native_fields": ["segmentation"],
            "invalid_mask_policy": "not applied: invalid (uncertain) pixels are not ignore regions",
            "group_id_status": GROUP_STATUS, "pair_linkage_status": PAIR_STATUS,
            "condition_metadata_status": "parsed from official file_name condition directory",
            "bounds_policy": "strict [0,width]x[0,height] from annotation JSON dimensions; no clipping",
            "mask_check": dict(mask) if check_masks else "skipped",
            "summary": summarize(images, annotations),
        },
    }
    validate_documents(result, {"schema_version": SCHEMA_VERSION, "predictions": [], "provenance": {}})
    return result


def summarize(images: list[dict], annotations: list[dict]) -> dict:
    per_image = Counter(a["image_id"] for a in annotations)
    condition = {i["image_id"]: i["attributes"]["condition"] for i in images}
    by_condition: dict[str, Counter] = defaultdict(Counter)
    for image in images:
        by_condition[image["attributes"]["condition"]]["images"] += 1
        by_condition[image["attributes"]["condition"]]["empty_images"] += per_image[image["image_id"]] == 0
    for a in annotations:
        cell = by_condition[condition[a["image_id"]]]
        cell[a["category"]] += 1
        cell[f"{a['category']}_iscrowd"] += a["iscrowd"]
    return {
        "image_count": len(images), "annotation_count": len(annotations),
        "empty_image_count": sum(per_image[i["image_id"]] == 0 for i in images),
        "category_counts": dict(sorted(Counter(a["category"] for a in annotations).items())),
        "iscrowd_count": sum(a["iscrowd"] for a in annotations),
        "ignore_count": sum(a["ignore"] for a in annotations),
        "images_with_unknown_group": sum(i["group_id"] is None for i in images),
        "by_condition": {c: dict(sorted(v.items())) for c, v in sorted(by_condition.items())},
    }


# ------------------------------------------------------------- cross-file checks


def reference_pairing(adverse: Mapping[str, Any], reference: Mapping[str, Any]) -> dict:
    """Report adverse↔reference coverage via the documented pair key. Never sets group_id.

    A reference image without an adverse counterpart, or two references for one key, is
    an error (the README defines references only as counterparts of adverse images).
    """
    adverse_keys = Counter(i["attributes"]["acdc_pair_key"] for i in adverse["images"])
    reference_keys = Counter(i["attributes"]["acdc_pair_key"] for i in reference["images"])
    orphans = sorted(k for k in reference_keys if k not in adverse_keys)
    duplicated = sorted(k for k, n in reference_keys.items() if n > 1)
    if orphans or duplicated:
        raise PreflightError(f"reference pairing broken: {len(orphans)} orphan, {len(duplicated)} duplicate keys")
    by_condition = defaultdict(lambda: {"adverse_images": 0, "with_annotated_reference": 0})
    for key in adverse_keys:
        cell = by_condition[key.split("/", 1)[0]]
        cell["adverse_images"] += 1
        cell["with_annotated_reference"] += key in reference_keys
    return {"status": PAIR_STATUS, "adverse_images": len(adverse_keys),
            "annotated_reference_images": len(reference_keys),
            "adverse_with_annotated_reference": sum(k in reference_keys for k in adverse_keys),
            "by_condition": dict(sorted(by_condition.items()))}


def sequence_report(documents: list[Mapping[str, Any]]) -> dict:
    """Sequence tokens per (condition, split) and GoPro numbers that recur across splits."""
    tokens: dict[tuple[str, str], set] = defaultdict(set)
    frames: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for doc in documents:
        for image in doc["images"]:
            attrs = image["attributes"]
            if not attrs["reference"]:
                tokens[(attrs["condition"], image["split"])].add(attrs["native_sequence"])
                frames[(attrs["condition"], image["split"], attrs["native_sequence"])].append(
                    int(attrs["native_frame"]))
    shared = {}
    for condition in CONDITIONS:
        numbers = {s: {gopro_recording(t) for t in tokens[(condition, s)]} - {None} for s in SPLITS}
        literal = tokens[(condition, "train")] & tokens[(condition, "val")]
        gaps = [min(abs(v - t) for t in frames[(condition, "train", token)])
                for token in literal for v in frames[(condition, "val", token)]]
        shared[condition] = {
            "train_sequences": len(tokens[(condition, "train")]),
            "val_sequences": len(tokens[(condition, "val")]),
            "identical_tokens_in_train_and_val": sorted(literal),
            "gopro_numbers_in_train_and_val": sorted(numbers["train"] & numbers["val"]),
            "val_images_in_shared_tokens": len(gaps),
            "val_frame_gap_to_nearest_train_frame_same_token": (
                {"min": min(gaps), "median": sorted(gaps)[len(gaps) // 2], "max": max(gaps)} if gaps else None),
        }
    return {"status": "diagnostic: shared GoPro numbers suggest shared physical recordings "
                      "across official splits; not verified, not used as groups",
            "by_condition": shared}


def condition_file_check(aggregate: Mapping[str, Any], per_condition: Mapping[str, Any],
                         condition: str) -> dict:
    """Is a per-condition file exactly the aggregate subset for that condition?"""
    def indexed(doc, key):
        out = {}
        for record in _native_records(doc, key):
            native = record.get("id")
            if type(native) is not int or native in out:
                raise PreflightError(f"invalid or duplicate condition-file {key} id")
            if key == "images":
                parse_file_name(record.get("file_name"))
            elif type(record.get("image_id")) is not int:
                raise PreflightError("condition-file annotation image_id must be an integer")
            out[native] = record
        return out
    for doc in (aggregate, per_condition):
        _categories(doc)
    aggregate_images, aggregate_anns = indexed(aggregate, "images"), indexed(aggregate, "annotations")
    prefix = f"{condition}/"
    expected_images = {k: i for k, i in aggregate_images.items() if i["file_name"].startswith(prefix)}
    expected_ids = set(expected_images)
    expected_anns = {k: a for k, a in aggregate_anns.items() if a["image_id"] in expected_ids}
    images = indexed(per_condition, "images")
    anns = indexed(per_condition, "annotations")
    foreign = sum(not i["file_name"].startswith(prefix) for i in per_condition["images"])
    return {"condition": condition, "images": len(images), "annotations": len(anns),
            "foreign_condition_images": foreign,
            "exact_aggregate_subset": images == expected_images and anns == expected_anns}


def _iou(a, b) -> float:
    width = min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])
    height = min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1])
    inter = max(width, 0) * max(height, 0)
    return inter / (a[2] * a[3] + b[2] * b[3] - inter)


def panoptic_crosscheck(converted: Mapping[str, Any], panoptic: Mapping[str, Any], *,
                        near_iou: float = 0.9, small_area: int = 100) -> dict:
    """Compare detection instances with panoptic thing segments of the same frames.

    Per frame and (category, iscrowd): exact (bbox, area) matches first, then greedy
    bbox-IoU >= ``near_iou`` matches. Descriptive only; detection boxes stay the source.
    """
    stem = {}
    for image in _native_records(panoptic, "images"):
        native = image.get("id")
        if type(native) not in (int, str) or native in stem:
            raise PreflightError("invalid or duplicate panoptic image id")
        stem[native] = parse_file_name(image.get("file_name"))["pair_key"]
    if len(set(stem.values())) != len(stem):
        raise PreflightError("panoptic frames are not unique")
    pan, det = defaultdict(list), defaultdict(list)
    crowd = Counter()
    for record in _native_records(panoptic, "annotations"):
        native = record.get("image_id")
        if type(native) not in (int, str) or native not in stem:
            raise PreflightError("unknown panoptic image id")
        for s in _native_records(record, "segments_info"):
            category = s.get("category_id")
            if type(category) is not int:
                raise PreflightError("panoptic category_id must be an integer")
            if category in EXPECTED_CATEGORIES:
                if type(s.get("iscrowd")) is not int or s["iscrowd"] not in (0, 1):
                    raise PreflightError("panoptic iscrowd must be 0/1")
                if _check_box_xywh(s.get("bbox")) or type(s.get("area")) is not int or s["area"] <= 0:
                    raise PreflightError("invalid panoptic bbox or area")
                pan[(stem[record["image_id"]], s["category_id"], bool(s["iscrowd"]))].append(
                    (tuple(map(float, s["bbox"])), s["area"]))
                crowd[EXPECTED_CATEGORIES[s["category_id"]][0]] += bool(s["iscrowd"])
    pair = {i["image_id"]: i["attributes"]["acdc_pair_key"] for i in converted["images"]}
    for a in converted["annotations"]:
        native = a["attributes"]["native"]
        det[(pair[a["image_id"]], native["category_id"], a["iscrowd"])].append((tuple(a["bbox"]), native["area"]))
    counts = Counter()
    for key in set(pan) | set(det):
        p, d = Counter(pan[key]), Counter(det[key])
        exact = p & d
        counts["exact"] += sum(exact.values())
        p, d = list((p - exact).elements()), list((d - exact).elements())
        for box, _ in d:
            best = max(range(len(p)), key=lambda j: _iou(box, p[j][0]), default=None)
            if best is not None and _iou(box, p[best][0]) >= near_iou:
                counts["near"] += 1
                p.pop(best)
            else:
                counts["detection_unmatched"] += 1
        counts["panoptic_unmatched"] += len(p)
        counts["panoptic_unmatched_area_lt_small"] += sum(area < small_area for _, area in p)
    return {"detection_instances": sum(map(len, det.values())),
            "panoptic_thing_segments": sum(map(len, pan.values())),
            "exact_bbox_area_matches": counts["exact"],
            f"near_matches_bbox_iou_ge_{near_iou}": counts["near"],
            "detection_unmatched": counts["detection_unmatched"],
            "panoptic_unmatched": counts["panoptic_unmatched"],
            f"panoptic_unmatched_area_lt_{small_area}px": counts["panoptic_unmatched_area_lt_small"],
            "panoptic_iscrowd_by_category": dict(sorted(crowd.items()))}


def invalid_overlap_native(doc: Mapping[str, Any], gt_root: Path, *,
                           categories=("person", "rider"), limit: int | None = None) -> dict:
    """Per-instance fraction of mask pixels marked invalid in ACDC ``invIds`` (adverse only).

    Descriptive only: invalid marks uncertain semantic content and is never turned into
    ignore. Reads the native RLE, so it takes the native (unconverted) document.
    """
    names = _categories(doc)
    wanted = {cid for cid, name in names.items() if name in categories}
    by_image = defaultdict(list)
    for a in doc["annotations"]:
        if a["category_id"] in wanted:
            by_image[a["image_id"]].append(a)
    images = sorted(doc["images"], key=lambda i: i["id"])
    if limit is not None:
        images = images[:limit]
    bins = ("0", "(0,0.1]", "(0.1,0.5]", "(0.5,1]")
    hist = defaultdict(lambda: dict.fromkeys(bins, 0))
    image_fraction = defaultdict(list)
    source_files = []
    for image in images:
        path = Path(gt_root) / image["segm_file"].replace("_gt_labelIds.png", "_gt_invIds.png")
        width, height, pixels = read_png_gray8(path)
        source_files.append({"relative_path": path.relative_to(gt_root).as_posix(),
                             "sha256": sha256_file(path)})
        if (width, height) != (image["width"], image["height"]) or set(pixels) - {0, 1}:
            raise PreflightError(f"{path.name}: unexpected invIds dimensions or values")
        condition = parse_file_name(image["file_name"])["condition"]
        image_fraction[condition].append(pixels.count(1) / len(pixels))
        for a in by_image[image["id"]]:
            counts = parse_segmentation(a["segmentation"], height, width)
            total = invalid = 0
            for column, top, bottom in rle_columns(counts, height):
                total += bottom - top
                invalid += sum(pixels[row * width + column] for row in range(top, bottom))
            fraction = invalid / total
            key = bins[0] if fraction == 0 else bins[1] if fraction <= 0.1 else bins[2] if fraction <= 0.5 else bins[3]
            hist[f"{condition}:{names[a['category_id']]}"][key] += 1
    manifest_bytes = json.dumps(sorted(source_files, key=lambda x: x["relative_path"]),
                                sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"images_read": len(images),
            "source_manifest": {"files": len(source_files),
                                "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
                                "recipe": "UTF-8 JSON of relative_path/sha256 objects sorted by relative_path; "
                                          "sort_keys=True, separators=(',', ':'); paths relative to gt root"},
            "mean_invalid_pixel_fraction_by_condition": {
                c: round(sum(v) / len(v), 6) for c, v in sorted(image_fraction.items())},
            "images_with_any_invalid_by_condition": {
                c: sum(f > 0 for f in v) for c, v in sorted(image_fraction.items())},
            "instance_invalid_fraction_histogram": dict(sorted(hist.items())),
            "bin_boundaries_status": "descriptive inspection bins, not frozen protocol strata"}


# --------------------------------------------------------------------- inventory


def _source(root: Path, relative: str) -> dict:
    return {"relative_path": relative, "relative_to": "documented ACDC extraction root",
            "sha256": sha256_file(Path(root) / relative)}


@_checked_result
def inventory(root: Path, *, invalid_limit: int | None = 0) -> dict:
    """Annotation-only inventory of a local ACDC extraction (no images, no inference).

    ``invalid_limit``: 0 skips invalid-mask reading, None reads every adverse image.
    """
    root = Path(root)
    converted, natives, sources = {}, {}, {}
    for (split, reference), relative in AGGREGATE_FILES.items():
        natives[(split, reference)] = load_json(root / relative)
        sources[(split, reference)] = _source(root, relative)
        converted[(split, reference)] = convert_acdc(
            natives[(split, reference)], split=split, reference=reference,
            ignore_policy="no_ignore_declared", source=sources[(split, reference)])
    condition_files = []
    for split in SPLITS:
        for condition in CONDITIONS:
            relative = (f"gt_detection_trainval/gt_detection/{condition}/"
                        f"instancesonly_{condition}_{split}_gt_detection.json")
            entry = condition_file_check(natives[(split, False)], load_json(root / relative), condition)
            entry.update(split=split, sha256=sha256_file(root / relative))
            condition_files.append(entry)
    panoptic, panoptic_sources = {}, {}
    for split in SPLITS:
        for reference, relative in ((False, f"gt_panoptic_trainval/gt_panoptic/{split}_gt_panoptic.json"),
                                    (True, f"gt_panoptic_trainval_ref/gt_panoptic/{split}_gt_ref_panoptic.json")):
            if (root / relative).exists():
                panoptic_sources[_role(split, reference)] = _source(root, relative)
                panoptic[_role(split, reference)] = panoptic_crosscheck(
                    converted[(split, reference)], load_json(root / relative))
    report = {
        "dataset": "acdc", "scope": "annotation-only; no images, inference or evaluation",
        "files": {_role(*k): {**v, "summary": converted[k]["provenance"]["summary"],
                              "mask_check": converted[k]["provenance"]["mask_check"]}
                  for k, v in sources.items()},
        "condition_files": condition_files,
        "panoptic_crosscheck": panoptic,
        "panoptic_sources": panoptic_sources,
        "reference_pairing": {s: reference_pairing(converted[(s, False)], converted[(s, True)]) for s in SPLITS},
        "sequences": sequence_report([converted[(s, False)] for s in SPLITS]),
        "group_id_status": GROUP_STATUS,
    }
    if invalid_limit != 0:
        report["invalid_mask"] = {s: invalid_overlap_native(
            natives[(s, False)], root / "gt_trainval" / "gt", limit=invalid_limit) for s in SPLITS}
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m threshold_transfer.acdc", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    inv = sub.add_parser("inventory", help="annotation-only inventory summary (no boxes)")
    inv.add_argument("--root", type=Path, required=True)
    inv.add_argument("--invalid-images", type=int, default=0,
                     help="adverse images per split for invalid-mask overlap; -1 = all, 0 = skip")
    inv.add_argument("--out", type=Path, required=True)
    conv = sub.add_parser("convert", help="canonical-v1 annotations (data-derived; keep outside Git)")
    conv.add_argument("--root", type=Path, required=True)
    conv.add_argument("--split", choices=SPLITS, required=True)
    conv.add_argument("--reference", action="store_true")
    conv.add_argument("--ignore-policy", choices=sorted(IGNORE_POLICIES), required=True)
    conv.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    repo = Path(__file__).resolve().parents[2]
    try:
        if args.command == "inventory":
            limit = None if args.invalid_images < 0 else args.invalid_images
            result = inventory(args.root, invalid_limit=limit)
            write_json(result, args.out, protected_roots=[args.root])
        else:
            relative = AGGREGATE_FILES[(args.split, args.reference)]
            result = convert_acdc(load_json(args.root / relative), split=args.split,
                                  reference=args.reference, ignore_policy=args.ignore_policy,
                                  source=_source(args.root, relative))
            # Canonical boxes are a modified dataset artifact under ETH's licence.
            write_json(result, args.out, protected_roots=[args.root, repo])
    except (PreflightError, OSError) as error:
        print(f"acdc: {error}", file=sys.stderr)
        return 2
    print(f"acdc: wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
