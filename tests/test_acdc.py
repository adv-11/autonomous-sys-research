"""Synthetic-fixture tests for threshold_transfer.acdc (stdlib unittest; no ACDC data).

The fixtures imitate the inspected ACDC v1 detection schema with tiny images. Real-data
results are reported separately in docs/claude/acdc_annotation_adapter.md.
"""

from __future__ import annotations

import copy
import io
import json
import struct
import sys
import tempfile
import unittest
import zlib
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from threshold_transfer import acdc as A  # noqa: E402
from threshold_transfer.data import PreflightError  # noqa: E402
from threshold_transfer.schema import validate_documents  # noqa: E402

H, W = 8, 10
CATEGORIES = [{"id": cid, "name": name, "supercategory": sup}
              for cid, (name, sup) in A.EXPECTED_CATEGORIES.items()]


def encode_counts(counts):
    """COCO compressed-RLE encoder (pycocotools rleToString), used only for fixtures."""
    out = []
    for i, value in enumerate(counts):
        x = value - counts[i - 2] if i > 2 else value
        more = True
        while more:
            c = x & 0x1F
            x >>= 5
            more = not ((c & 0x10) == 0 and x == 0 or (c & 0x10) != 0 and x == -1)
            if more:
                c |= 0x20
            out.append(chr(c + 48))
    return "".join(out)


def rect_counts(x, y, w, h, height=H, width=W):
    mask = [0] * (height * width)  # column-major
    for col in range(x, x + w):
        for row in range(y, y + h):
            mask[col * height + row] = 1
    counts, current, run = [], 0, 0
    for value in mask:
        if value != current:
            counts.append(run)
            current, run = value, 0
        run += 1
    counts.append(run)
    return counts


def ann(aid, image_id, box, category=24, iscrowd=0):
    x, y, w, h = box
    return {"id": aid, "image_id": image_id, "category_id": category, "iscrowd": iscrowd,
            "bbox": [float(v) for v in box], "area": w * h,
            "segmentation": {"size": [H, W], "counts": encode_counts(rect_counts(x, y, w, h))}}


def image(iid, condition, seq, frame, split="train", reference=False):
    role = f"{split}_ref" if reference else split
    marker = "_ref" if reference else ""
    name = f"{condition}/{role}/{seq}/{seq}_frame_{frame:06d}_rgb{marker}_anon.png"
    record = {"id": iid, "file_name": name, "width": W, "height": H}
    if not reference:
        record["segm_file"] = name.replace("_rgb_anon.png", "_gt_labelIds.png")
    return record


def adverse_doc():
    return {
        "images": [image(0, "fog", "GOPR0475", 41), image(1, "fog", "GP010475", 7),
                   image(2, "night", "GOPR0351", 3)],  # image 2 stays empty
        "categories": copy.deepcopy(CATEGORIES),
        "annotations": [ann(0, 0, (1, 2, 3, 4)), ann(1, 0, (0, 0, 2, 2), category=25),
                        ann(2, 1, (5, 1, 4, 6), iscrowd=1)],
    }


def reference_doc():
    return {
        "images": [image(4006, "fog", "GOPR0475", 41, reference=True)],
        "categories": copy.deepcopy(CATEGORIES),
        "annotations": [ann(9000, 4006, (2, 2, 2, 2))],
    }


def convert(doc=None, **kw):
    kw.setdefault("split", "train")
    kw.setdefault("reference", False)
    kw.setdefault("ignore_policy", "no_ignore_declared")
    return A.convert_acdc(adverse_doc() if doc is None else doc, **kw)


def png_gray8(width, height, rows, filters):
    raw = bytearray()
    previous = bytes(width)
    for row, kind in zip(rows, filters):
        row = bytes(row)
        if kind == 0:
            line = row
        elif kind == 1:
            line = bytes((row[i] - (row[i - 1] if i else 0)) & 0xFF for i in range(width))
        elif kind == 2:
            line = bytes((a - b) & 0xFF for a, b in zip(row, previous))
        elif kind == 3:
            line = bytes((row[i] - ((row[i - 1] if i else 0) + previous[i]) // 2) & 0xFF for i in range(width))
        else:
            def paeth(a, b, c):
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                return a if pa <= pb and pa <= pc else b if pb <= pc else c
            line = bytes((row[i] - paeth(row[i - 1] if i else 0, previous[i],
                                         previous[i - 1] if i else 0)) & 0xFF for i in range(width))
        raw += bytes([kind]) + line
        previous = row

    def chunk(kind, body):
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b""))


class RleTests(unittest.TestCase):
    def test_round_trip_and_extent(self):
        counts = rect_counts(1, 2, 3, 4)
        self.assertEqual(A.decode_rle_counts(encode_counts(counts), H * W), counts)
        self.assertEqual(A.rle_extent(counts, H), (12, [1, 2, 3, 4]))

    def test_run_crossing_columns_spans_full_height(self):
        counts = [H - 1, 2, H * W - H - 1]  # last pixel of col 0 and first of col 1
        self.assertEqual(A.rle_extent(counts, H), (2, [0, 0, 2, H]))
        self.assertEqual(list(A.rle_columns(counts, H)), [(0, H - 1, H), (1, 0, 1)])

    def test_rejects_truncated_bad_or_wrong_size_rle(self):
        with self.assertRaises(PreflightError):
            A.decode_rle_counts(encode_counts(rect_counts(1, 1, 1, 1)), H * W + 1)
        with self.assertRaises(PreflightError):
            A.decode_rle_counts("\x7f", H * W)
        with self.assertRaises(PreflightError):
            A.decode_rle_counts("o", H * W)  # continuation bit with no next char
        with self.assertRaises(PreflightError):
            A.parse_segmentation({"size": [W, H], "counts": "0"}, H, W)
        with self.assertRaises(PreflightError):
            A.parse_segmentation("{'size': [8, 10], 'counts': '0'}", H, W)


class FileNameTests(unittest.TestCase):
    def test_parse_and_pair_key(self):
        adverse = A.parse_file_name("fog/train/GP010475/GP010475_frame_001043_rgb_anon.png")
        ref = A.parse_file_name("fog/train_ref/GP010475/GP010475_frame_001043_rgb_ref_anon.png")
        self.assertEqual(adverse["pair_key"], ref["pair_key"])
        self.assertTrue(ref["reference"])
        self.assertFalse(adverse["reference"])

    def test_rejects_inconsistent_names(self):
        for name in ("fog/train/GP010475/GP010475_frame_001043_rgb_ref_anon.png",
                     "fog/train_ref/GP010475/GP010475_frame_001043_rgb_anon.png",
                     "fog/train/GP010475/GOPR0475_frame_001043_rgb_anon.png",
                     "haze/train/A/A_frame_000001_rgb_anon.png", None):
            with self.assertRaises(PreflightError, msg=name):
                A.parse_file_name(name)

    def test_gopro_recording_is_diagnostic_only(self):
        self.assertEqual({A.gopro_recording(s) for s in ("GOPR0475", "GP010475", "GP020475")}, {"0475"})
        self.assertIsNone(A.gopro_recording("seq7"))


class ConvertTests(unittest.TestCase):
    def test_canonical_output_preserves_native_semantics(self):
        out = convert()
        validate_documents(out, {"schema_version": out["schema_version"], "predictions": [], "provenance": {}})
        anns = {a["annotation_id"]: a for a in out["annotations"]}
        self.assertEqual(set(anns), {"acdc:train:a0", "acdc:train:a1", "acdc:train:a2"})
        self.assertEqual(anns["acdc:train:a0"]["category"], "person")  # never "pedestrian"
        self.assertEqual(anns["acdc:train:a1"]["category"], "rider")   # never merged
        self.assertTrue(anns["acdc:train:a2"]["iscrowd"])
        self.assertFalse(any(a["ignore"] for a in anns.values()))
        self.assertEqual(anns["acdc:train:a0"]["attributes"]["native"], {"category_id": 24, "area": 12})
        self.assertEqual(out["provenance"]["summary"]["empty_image_count"], 1)
        self.assertEqual(len(out["images"]), 3)
        self.assertEqual(out["provenance"]["mask_check"], {"mask_bbox_equal": 3})
        self.assertFalse(out["provenance"]["official_evaluator_equivalent"])
        json.dumps(out, allow_nan=False)

    def test_no_group_inference_from_sequences(self):
        out = convert()
        self.assertTrue(all(i["group_id"] is None for i in out["images"]))
        attrs = out["images"][0]["attributes"]
        self.assertEqual((attrs["condition"], attrs["native_sequence"], attrs["native_frame"]),
                         ("fog", "GOPR0475", "000041"))
        self.assertEqual(attrs["acdc_pair_key"], "fog/train/GOPR0475_frame_000041")

    def test_crowd_ignore_policy_is_explicit(self):
        out = convert(ignore_policy="acdc_iscrowd_v1_provisional")
        self.assertEqual([a["ignore"] for a in out["annotations"]], [False, False, True])
        with self.assertRaises(PreflightError):
            convert(ignore_policy="coco_iscrowd_v1_provisional")
        with self.assertRaises(TypeError):
            A.convert_acdc(adverse_doc(), split="train", reference=False)

    def test_reference_namespace_differs(self):
        out = convert(reference_doc(), reference=True)
        self.assertEqual(out["images"][0]["image_id"], "acdc:train_ref:img4006")
        self.assertEqual(out["annotations"][0]["annotation_id"], "acdc:train_ref:a9000")
        self.assertEqual(out["images"][0]["split"], "train_ref")

    def _fails(self, mutate, **kw):
        doc = adverse_doc()
        mutate(doc)
        with self.assertRaises(PreflightError):
            convert(doc, **kw)

    def test_geometry_fails_closed(self):
        self._fails(lambda d: d["annotations"][0].update(bbox=[1.0, 2.0, 0.0, 4.0]))
        self._fails(lambda d: d["annotations"][0].update(bbox=[1.0, 2.0, 3.0, float("nan")]))
        self._fails(lambda d: d["annotations"][0].update(bbox=[8.0, 2.0, 3.0, 4.0]))  # past width
        self._fails(lambda d: d["annotations"][0].update(bbox=[-1.0, 2.0, 3.0, 4.0]))
        self._fails(lambda d: d["annotations"][0].update(area=13))  # disagrees with RLE

    def test_box_mask_disagreement_is_reported_not_repaired(self):
        doc = adverse_doc()
        doc["annotations"][0]["bbox"] = [1.0, 2.0, 3.0, 5.0]
        out = convert(doc)
        self.assertEqual(out["provenance"]["mask_check"], {"mask_bbox_equal": 2, "mask_bbox_differs": 1})
        self.assertEqual(out["annotations"][0]["bbox"], [1.0, 2.0, 3.0, 5.0])

    def test_schema_and_ids_fail_closed(self):
        self._fails(lambda d: d["annotations"][1].update(id=0))
        self._fails(lambda d: d["annotations"][0].update(id="0"))
        self._fails(lambda d: d["annotations"][0].update(id=True))
        self._fails(lambda d: d["annotations"][0].update(image_id=99))
        self._fails(lambda d: d["annotations"][0].update(category_id=99))
        self._fails(lambda d: d["annotations"][0].update(iscrowd=2))
        self._fails(lambda d: d["annotations"][0].update(extra=1))
        self._fails(lambda d: d["categories"].pop())
        self._fails(lambda d: d["categories"][0].update(name="pedestrian"))
        self._fails(lambda d: d["images"].append(copy.deepcopy(d["images"][0]) | {"id": 7}))  # same frame
        self._fails(lambda d: d["images"][1].update(id=0))
        self._fails(lambda d: d["images"][0].update(segm_file="other.png"))
        self._fails(lambda d: d["images"][0].update(width=0))
        self._fails(lambda d: d.update(extra=[]))
        self._fails(lambda d: None, split="val")          # file_name split disagrees
        self._fails(lambda d: None, reference=True)       # adverse file declared as ref

    def test_inputs_are_not_mutated(self):
        doc = adverse_doc()
        before = copy.deepcopy(doc)
        convert(doc)
        self.assertEqual(doc, before)


class CrossFileTests(unittest.TestCase):
    def test_reference_pairing_coverage_and_errors(self):
        report = A.reference_pairing(convert(), convert(reference_doc(), reference=True))
        self.assertEqual(report["adverse_with_annotated_reference"], 1)
        self.assertEqual(report["by_condition"]["night"], {"adverse_images": 1, "with_annotated_reference": 0})
        orphan = reference_doc()
        orphan["images"][0] = image(4006, "snow", "X1", 1, reference=True)
        with self.assertRaises(PreflightError):
            A.reference_pairing(convert(), convert(orphan, reference=True))

    def test_condition_file_copy_defect_is_detected(self):
        doc = adverse_doc()
        fog = {"images": doc["images"][:2], "annotations": doc["annotations"], "categories": CATEGORIES}
        self.assertTrue(A.condition_file_check(doc, fog, "fog")["exact_aggregate_subset"])
        copied = A.condition_file_check(doc, doc, "fog")  # aggregate shipped as a condition file
        self.assertFalse(copied["exact_aggregate_subset"])
        self.assertEqual(copied["foreign_condition_images"], 1)

    def test_sequence_report_flags_shared_recordings(self):
        val = {"images": [image(10, "fog", "GP020475", 5, split="val")], "categories": CATEGORIES,
               "annotations": []}
        report = A.sequence_report([convert(), convert(val, split="val")])
        self.assertEqual(report["by_condition"]["fog"]["gopro_numbers_in_train_and_val"], ["0475"])
        self.assertEqual(report["by_condition"]["fog"]["identical_tokens_in_train_and_val"], [])

    def test_panoptic_crosscheck(self):
        out = convert()
        panoptic = {"images": [{"id": "GOPR0475_frame_000041", "file_name": adverse_doc()["images"][0]["file_name"]}],
                    "annotations": [{"image_id": "GOPR0475_frame_000041", "segments_info": [
                        {"category_id": 24, "bbox": [1, 2, 3, 4], "area": 12, "iscrowd": 0},
                        {"category_id": 25, "bbox": [0, 0, 2, 3], "area": 5, "iscrowd": 0},
                        {"category_id": 24, "bbox": [7, 7, 1, 1], "area": 1, "iscrowd": 0},
                        {"category_id": 7, "bbox": [0, 0, 10, 8], "area": 80, "iscrowd": 0}]}]}
        report = A.panoptic_crosscheck(out, panoptic, near_iou=0.6)
        self.assertEqual(report["exact_bbox_area_matches"], 1)
        self.assertEqual(report["near_matches_bbox_iou_ge_0.6"], 1)
        self.assertEqual(report["detection_unmatched"], 1)  # the crowd box on another frame
        self.assertEqual(report["panoptic_unmatched"], 1)


class PngAndInvalidTests(unittest.TestCase):
    def test_png_filters_decode(self):
        rows = [[(r * 7 + c * 13) % 256 for c in range(W)] for r in range(5)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.png"
            path.write_bytes(png_gray8(W, 5, rows, [0, 1, 2, 3, 4]))
            self.assertEqual(A.read_png_gray8(path), (W, 5, bytes(sum(rows, []))))
            data = bytearray(path.read_bytes())
            data[40] ^= 1
            path.write_bytes(bytes(data))
            with self.assertRaises(PreflightError):
                A.read_png_gray8(path)

    def test_invalid_overlap_is_descriptive_not_ignore(self):
        doc = adverse_doc()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for record in doc["images"]:
                rows = [[1 if c >= 2 else 0 for c in range(W)] if record["id"] == 0 else [0] * W for _ in range(H)]
                path = root / record["segm_file"].replace("_gt_labelIds.png", "_gt_invIds.png")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(png_gray8(W, H, rows, [2] * H))
            report = A.invalid_overlap_native(doc, root)
        hist = report["instance_invalid_fraction_histogram"]
        # image 0 columns >= 2 invalid: person box x=1..3 -> 8/12 invalid; image 1 crowd box valid
        self.assertEqual(hist["fog:person"], {"0": 1, "(0,0.1]": 0, "(0.1,0.5]": 0, "(0.5,1]": 1})
        self.assertEqual(hist["fog:rider"]["0"], 1)
        self.assertEqual(report["images_with_any_invalid_by_condition"], {"fog": 1, "night": 0})
        self.assertFalse(any(a["ignore"] for a in convert()["annotations"]))


class CliTests(unittest.TestCase):
    def _root(self, tmp):
        root = Path(tmp) / "acdc"
        docs = {("train", False): adverse_doc(), ("train", True): reference_doc()}
        val = {"images": [image(500, "fog", "GP020475", 5, split="val")], "categories": CATEGORIES, "annotations": []}
        val_ref = {"images": [], "categories": CATEGORIES, "annotations": []}
        docs[("val", False)], docs[("val", True)] = val, val_ref
        for key, relative in A.AGGREGATE_FILES.items():
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text(json.dumps(docs[key]), encoding="utf-8")
        for split, doc in (("train", docs[("train", False)]), ("val", val)):
            for condition in A.CONDITIONS:
                part = {"images": [i for i in doc["images"] if i["file_name"].startswith(condition + "/")],
                        "categories": CATEGORIES}
                ids = {i["id"] for i in part["images"]}
                part["annotations"] = [a for a in doc["annotations"] if a["image_id"] in ids]
                path = root / f"gt_detection_trainval/gt_detection/{condition}/instancesonly_{condition}_{split}_gt_detection.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(part), encoding="utf-8")
        return root

    def _run(self, argv):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            try:
                return A.main(argv)
            except SystemExit as exit_:
                return exit_.code

    def test_inventory_and_convert(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._root(tmp)
            out = Path(tmp) / "inv.json"
            self.assertEqual(self._run(["inventory", "--root", str(root), "--out", str(out)]), 0)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["files"]["train"]["summary"]["image_count"], 3)
            self.assertTrue(all(c["exact_aggregate_subset"] for c in report["condition_files"]))
            self.assertEqual(report["reference_pairing"]["train"]["adverse_with_annotated_reference"], 1)
            self.assertNotIn('"bbox":', out.read_text(encoding="utf-8"))  # summary carries no boxes
            conv = Path(tmp) / "train.json"
            self.assertEqual(self._run(["convert", "--root", str(root), "--split", "train",
                                        "--ignore-policy", "no_ignore_declared", "--out", str(conv)]), 0)
            self.assertEqual(len(json.loads(conv.read_text(encoding="utf-8"))["annotations"]), 3)
            # missing policy is an argparse error; output inside the data root is refused
            self.assertEqual(self._run(["convert", "--root", str(root), "--split", "train", "--out", str(conv)]), 2)
            self.assertEqual(self._run(["convert", "--root", str(root), "--split", "train", "--ignore-policy",
                                        "no_ignore_declared", "--out", str(root / "x.json")]), 2)
            repo_out = Path(A.__file__).resolve().parents[2] / "acdc_should_not_exist.json"
            self.assertEqual(self._run(["convert", "--root", str(root), "--split", "train", "--ignore-policy",
                                        "no_ignore_declared", "--out", str(repo_out)]), 2)
            self.assertFalse(repo_out.exists())


if __name__ == "__main__":
    unittest.main()
