"""Synthetic-fixture tests for threshold_transfer.data (stdlib unittest; no real data)."""

from __future__ import annotations

import copy
import gzip
import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from threshold_transfer import data as D  # noqa: E402

KP = D.KITTI_DIAGNOSTIC_POLICY


def coco_doc():
    return {
        "images": [
            {"id": 1, "file_name": "a.jpg", "width": 100, "height": 80},
            {"id": 2, "file_name": "b.jpg", "width": 100, "height": 80},  # empty image
            {"id": "c3", "file_name": "c.jpg", "width": 100, "height": 80},
        ],
        "categories": [{"id": 1, "name": "person"}, {"id": 3, "name": "car"}],
        "annotations": [
            {"id": 10, "image_id": 1, "category_id": 1, "bbox": [1, 2, 10, 20], "iscrowd": 0, "area": 200},
            {"id": 11, "image_id": 1, "category_id": 1, "bbox": [0, 0, 50, 50], "iscrowd": 1, "area": 2500},
            {"id": "x", "image_id": "c3", "category_id": 3, "bbox": [90, 70, 20, 20], "iscrowd": 0},
        ],
    }


def kitti_doc():
    base = {"area": 1.0, "kitti_difficulty": None, "occlusion": None, "truncation": None}
    ann = lambda i, img, cat, crowd, kig, reason, **k: {  # noqa: E731
        **base, "id": i, "image_id": img, "category_id": cat, "bbox": [1, 1, 5, 9],
        "iscrowd": crowd, "kitti_ignore": kig, "ignore_reason": reason, **k}
    return {
        "images": [{"id": n, "file_name": f"{n:06d}.png", "width": 1242, "height": 375} for n in (1, 2, 3)],
        "categories": [{"id": 1, "name": "Car"}, {"id": 2, "name": "Pedestrian"}, {"id": 3, "name": "Cyclist"}],
        "annotations": [
            ann(1, 1, 2, 0, 0, None, kitti_difficulty="moderate", occlusion=1, truncation=0.1),
            *[ann(1 + c, 1, c, 1, 1, "dontcare") for c in (1, 2, 3)],
            ann(5, 2, 2, 0, 1, "neighbour:Person_sitting"),
            ann(6, 2, 1, 0, 0, None),
        ],
        "info": {"split": "val"},
    }


def legacy_cache():
    return {
        "meta": {
            "run": "toy_run", "dataset": "toy", "split": "toy-val", "num_images": 3,
            "image_ids": [1, 2, "c3"],
            "detector": {"score_thresh": 0.001, "max_raw_det": 3, "max_eval_det": 2,
                         "nms_iou": 0.7, "nms_multi_label": True},
            "vocab_key": "coco", "vocabulary": ["person", "bicycle", "car"],
        },
        "detections": [
            [1, 1.0, 2.0, 11.0, 22.0, 0.9, 0],
            [1, 5.0, 5.0, 9.0, 9.0, 0.5, 0],
            [1, 5.0, 5.0, 9.5, 9.5, 0.5, 0],   # exact tie with the previous row
            ["c3", 10.0, 10.0, 20.0, 20.0, 0.3, 2],
            [1, 0.0, 0.0, 3.0, 3.0, 0.2, 1],   # bicycle: unmapped below
        ],
    }


class CanonicalIdTests(unittest.TestCase):
    def test_int_and_string(self):
        self.assertEqual(D.canonical_id(7, "x"), "7")
        self.assertEqual(D.canonical_id("abc", "x"), "abc")
        for bad in (True, None, "", 1.0):
            with self.assertRaises(D.PreflightError):
                D.canonical_id(bad, "x")

    def test_int_string_collision_rejected(self):
        doc = coco_doc()
        doc["images"].append({"id": "1", "file_name": "d.jpg", "width": 10, "height": 10})
        with self.assertRaisesRegex(D.PreflightError, "duplicate image id"):
            D.convert_coco(doc, dataset_tag="t", split=None, ignore_policy="no_ignore_declared")


class CocoConversionTests(unittest.TestCase):
    def test_conversion_preserves_empty_images_and_names(self):
        out = D.convert_coco(coco_doc(), dataset_tag="t", split="val",
                             ignore_policy="coco_iscrowd_v1_provisional")
        self.assertEqual([i["image_id"] for i in out["images"]], ["1", "2", "c3"])
        self.assertEqual(out["provenance"]["summary"]["empty_image_count"], 1)
        self.assertEqual({a["category"] for a in out["annotations"]}, {"person", "car"})
        self.assertEqual([a["annotation_id"] for a in out["annotations"]], ["t:a10", "t:a11", "t:ax"])
        crowd = out["annotations"][1]
        self.assertTrue(crowd["iscrowd"] and crowd["ignore"])
        self.assertTrue(all(i["group_id"] is None and i["attributes"] == {} for i in out["images"]))
        # out-of-bounds box is reported, not clipped
        self.assertEqual(out["provenance"]["validation"]["out_of_image_bounds"], 1)
        self.assertEqual(out["annotations"][2]["bbox"], [90.0, 70.0, 20.0, 20.0])
        json.dumps(out, allow_nan=False)

    def test_no_ignore_policy_keeps_iscrowd_only(self):
        out = D.convert_coco(coco_doc(), dataset_tag="t", split=None, ignore_policy="no_ignore_declared")
        self.assertFalse(any(a["ignore"] for a in out["annotations"]))
        self.assertTrue(out["annotations"][1]["iscrowd"])

    def test_ignore_policy_required(self):
        with self.assertRaises(D.PreflightError):
            D.convert_coco(coco_doc(), dataset_tag="t", split=None, ignore_policy="guess")

    def test_duplicate_annotation_and_unknown_refs(self):
        doc = coco_doc()
        doc["annotations"].append(dict(doc["annotations"][0]))
        with self.assertRaisesRegex(D.PreflightError, "duplicate annotation"):
            D.convert_coco(doc, dataset_tag="t", split=None, ignore_policy="no_ignore_declared")
        doc = coco_doc()
        doc["annotations"][0]["image_id"] = 99
        with self.assertRaisesRegex(D.PreflightError, "unknown image"):
            D.convert_coco(doc, dataset_tag="t", split=None, ignore_policy="no_ignore_declared")
        doc = coco_doc()
        doc["annotations"][0]["category_id"] = 2
        with self.assertRaisesRegex(D.PreflightError, "unknown category"):
            D.convert_coco(doc, dataset_tag="t", split=None, ignore_policy="no_ignore_declared")

    def test_zero_and_reversed_boxes_rejected_or_reported(self):
        for bbox in ([1, 1, 0, 5], [1, 1, -3, 5], [1, 1, 5, float("nan")]):
            doc = coco_doc()
            doc["annotations"][0]["bbox"] = bbox
            with self.assertRaises(D.PreflightError):
                D.convert_coco(doc, dataset_tag="t", split=None, ignore_policy="no_ignore_declared")
            out = D.convert_coco(doc, dataset_tag="t", split=None, ignore_policy="no_ignore_declared",
                                 invalid_box_policy="exclude_and_report")
            self.assertEqual(len(out["annotations"]), 2)
            self.assertEqual(sum(out["provenance"]["validation"]["invalid_boxes"].values()), 1)

    def test_kitti_fields_refused_by_plain_coco(self):
        with self.assertRaisesRegex(D.PreflightError, "KITTI"):
            D.convert_coco(kitti_doc(), dataset_tag="k", split=None, ignore_policy="no_ignore_declared")


class KittiTests(unittest.TestCase):
    def test_default_conversion_blocked(self):
        with self.assertRaisesRegex(D.PreflightError, "blocked"):
            D.convert_kitti_derived(kitti_doc(), dataset_tag="k", split=None, policy=None)

    def test_diagnostic_subset_preserves_native_flags(self):
        out = D.convert_kitti_derived(kitti_doc(), dataset_tag="k", split="val", policy=KP)
        prov = out["provenance"]
        self.assertFalse(prov["official_kitti_equivalent"])
        self.assertEqual(prov["excluded_neighbour_image_ids"], ["2"])
        self.assertEqual([i["image_id"] for i in out["images"]], ["1", "3"])  # empty image 3 kept
        dc = [a for a in out["annotations"] if a["attributes"]["native"]["ignore_reason"] == "dontcare"]
        self.assertEqual(len(dc), 3)
        self.assertTrue(all(a["ignore"] and a["iscrowd"] for a in dc))
        self.assertEqual({a["category"] for a in dc}, {"Car", "Pedestrian", "Cyclist"})
        ped = out["annotations"][0]
        self.assertFalse(ped["ignore"])
        self.assertEqual(ped["attributes"]["native"]["kitti_difficulty"], "moderate")
        self.assertEqual(prov["native_record_kinds_before_exclusion"]["neighbour:Person_sitting"], 1)

    def test_inconsistent_native_flags_rejected(self):
        doc = kitti_doc()
        doc["annotations"][1]["iscrowd"] = 0  # dontcare without crowd
        with self.assertRaises(D.PreflightError):
            D.convert_kitti_derived(doc, dataset_tag="k", split=None, policy=KP)
        doc = kitti_doc()
        doc["annotations"][0]["ignore_reason"] = "difficulty>moderate"
        with self.assertRaisesRegex(D.PreflightError, "unsupported"):
            D.convert_kitti_derived(doc, dataset_tag="k", split=None, policy=KP)


class LegacyPredictionTests(unittest.TestCase):
    def manifest(self):
        return D.convert_coco(coco_doc(), dataset_tag="t", split=None, ignore_policy="no_ignore_declared")

    def test_conversion_ids_order_and_provenance(self):
        out = D.convert_legacy_predictions(legacy_cache(), category_mapping={"person": "person", "car": "car"},
                                           annotations=self.manifest())
        ids = [p["candidate_id"] for p in out["predictions"]]
        self.assertEqual(ids, ["toy_run:0", "toy_run:1", "toy_run:2", "toy_run:3"])
        prov = out["provenance"]
        self.assertEqual(prov["evaluated_image_ids"], ["1", "2", "c3"])  # empty image 2 retained
        self.assertEqual(prov["validation"]["empty_output_image_count"], 1)
        self.assertEqual(prov["dropped_unmapped_rows"], {"bicycle": 1})
        self.assertEqual(prov["cache_policy"]["score_floor"], 0.001)
        self.assertEqual(prov["cache_policy"]["score_decimals"], 5)
        self.assertEqual(prov["cache_policy"]["max_eval_det_not_applied"], 2)
        self.assertEqual(prov["validation"]["images_at_cap"], 0)
        self.assertEqual(prov["max_tie_group_size"], 2)
        self.assertEqual(out["predictions"][0]["bbox"], [1.0, 2.0, 10.0, 20.0])
        # tie order: (score desc, candidate id asc) reproduces original row order
        ordered = sorted(out["predictions"], key=lambda p: (-p["score"], p["candidate_id"]))
        self.assertEqual([p["candidate_id"] for p in ordered], ids)
        json.dumps(out, allow_nan=False)

    def test_candidate_id_padding_keeps_lexicographic_row_order(self):
        cache = legacy_cache()
        cache["detections"] = [[1, 0.0, 0.0, 1.0, 1.0, 0.5, 0] for _ in range(12)]
        out = D.convert_legacy_predictions(cache, category_mapping={"person": "person"})
        ids = [p["candidate_id"] for p in out["predictions"]]
        self.assertEqual(ids[0], "toy_run:00")
        self.assertEqual(sorted(ids), ids)

    def test_mapping_required_and_checked(self):
        with self.assertRaises(D.PreflightError):
            D.convert_legacy_predictions(legacy_cache(), category_mapping={})
        with self.assertRaisesRegex(D.PreflightError, "not in cache vocabulary"):
            D.convert_legacy_predictions(legacy_cache(), category_mapping={"pedestrian": "person"})
        # person -> Pedestrian is not a category of this manifest: refused, not aliased
        with self.assertRaisesRegex(D.PreflightError, "absent from annotation"):
            D.convert_legacy_predictions(legacy_cache(), category_mapping={"person": "Pedestrian"},
                                         annotations=self.manifest())

    def test_malformed_rows(self):
        bad_rows = {
            "row_not_length_7": [1, 0, 0, 1, 1, 0.5],
            "image_id_not_in_meta": [9, 0, 0, 1, 1, 0.5, 0],
            "coordinate_nonfinite_or_nonnumeric": [1, "0", 0, 1, 1, 0.5, 0],
            "score_nonfinite_or_outside_0_1": [1, 0, 0, 1, 1, 1.5, 0],
            "vocabulary_index_invalid": [1, 0, 0, 1, 1, 0.5, 3],
            "box_zero_or_reversed": [1, 5, 0, 5, 1, 0.5, 0],
        }
        for reason, row in bad_rows.items():
            cache = legacy_cache()
            cache["detections"].append(row)
            with self.assertRaisesRegex(D.PreflightError, reason):
                D.convert_legacy_predictions(cache, category_mapping={"person": "person"})
            out = D.convert_legacy_predictions(cache, category_mapping={"person": "person"},
                                               invalid_row_policy="exclude_and_report")
            self.assertEqual(out["provenance"]["validation"]["invalid_rows"], {reason: 1})
            self.assertEqual(len(out["provenance"]["evaluated_image_ids"]), 3)

    def test_duplicate_vocabulary_placeholder(self):
        # torchvision-style list: placeholder names repeat; mapping them is ambiguous.
        cache = legacy_cache()
        cache["meta"]["vocabulary"] = ["__background__", "person", "N/A", "N/A"]
        cache["detections"] = [[1, 0.0, 0.0, 1.0, 1.0, 0.5, 1], [1, 0.0, 0.0, 1.0, 1.0, 0.4, 3]]
        out = D.convert_legacy_predictions(cache, category_mapping={"person": "person"})
        self.assertEqual(out["provenance"]["dropped_unmapped_rows"], {"N/A": 1})
        self.assertEqual(out["provenance"]["validation"]["duplicate_vocabulary_names"], {"N/A": [2, 3]})
        self.assertEqual(out["predictions"][0]["category"], "person")  # index 1, not COCO id guess
        with self.assertRaisesRegex(D.PreflightError, "ambiguous"):
            D.convert_legacy_predictions(cache, category_mapping={"N/A": "person"})

    def test_reversed_box_with_neg_vocab_bool(self):
        cache = legacy_cache()
        cache["detections"].append([1, 0, 0, 1, 1, 0.5, True])
        with self.assertRaisesRegex(D.PreflightError, "vocabulary_index_invalid"):
            D.convert_legacy_predictions(cache, category_mapping={"person": "person"})

    def test_meta_problems(self):
        cache = legacy_cache()
        cache["meta"]["image_ids"].append("1")
        with self.assertRaisesRegex(D.PreflightError, "duplicate image ids"):
            D.convert_legacy_predictions(cache, category_mapping={"person": "person"})
        cache = legacy_cache()
        cache["meta"]["num_images"] = 4
        with self.assertRaises(D.PreflightError):
            D.convert_legacy_predictions(cache, category_mapping={"person": "person"})
        cache = legacy_cache()
        cache["extra"] = 1
        with self.assertRaises(D.PreflightError):
            D.convert_legacy_predictions(cache, category_mapping={"person": "person"})

    def test_policy_gap_reporting(self):
        cache = legacy_cache()
        cache["detections"] += [[1, 0.0, 0.0, 1.0, 1.0, 0.0005, 0], [1, 0.0, 0.0, 1.123, 1.0, 0.1234567, 0]]
        scan = D.scan_legacy_rows(cache)
        self.assertEqual(scan["rows_below_score_floor"], 1)
        self.assertEqual(scan["rows_exceeding_coordinate_rounding"], 1)
        self.assertEqual(scan["rows_exceeding_score_rounding"], 1)
        self.assertEqual(scan["images_over_cap"], 1)  # image 1 now has 6 rows > cap 3

    def test_manifest_equality_and_restriction(self):
        manifest = self.manifest()
        sub = copy.deepcopy(manifest)
        sub["images"] = [i for i in sub["images"] if i["image_id"] != "c3"]
        sub["annotations"] = [a for a in sub["annotations"] if a["image_id"] != "c3"]
        with self.assertRaisesRegex(D.PreflightError, "differs from manifest"):
            D.convert_legacy_predictions(legacy_cache(), category_mapping={"person": "person"}, annotations=sub)
        out = D.convert_legacy_predictions(legacy_cache(), category_mapping={"person": "person"},
                                           annotations=sub, restrict_to_manifest=True)
        self.assertEqual(out["provenance"]["evaluated_image_ids"], ["1", "2"])
        self.assertEqual(out["provenance"]["population_restriction"]["excluded_image_count"], 1)
        bigger = copy.deepcopy(manifest)
        bigger["images"].append({**manifest["images"][0], "image_id": "zz"})
        with self.assertRaisesRegex(D.PreflightError, "never evaluated"):
            D.convert_legacy_predictions(legacy_cache(), category_mapping={"person": "person"},
                                         annotations=bigger, restrict_to_manifest=True)


class RoleCheckTests(unittest.TestCase):
    def manifest(self, groups):
        return {"images": [{"image_id": k, "group_id": g} for k, g in groups.items()]}

    def test_unknown_groups_fail_closed_for_held_out(self):
        m = self.manifest({"1": None, "2": None})
        r = D.check_roles(m, {"1": "source_selection", "2": "clear_test"}, mode="held_out")
        self.assertEqual(r["status"], "FAIL")
        self.assertFalse(r["independent_split_declared"])
        r = D.check_roles(m, {"1": "source_selection", "2": "clear_test"}, mode="diagnostic")
        self.assertEqual(r["status"], "DIAGNOSTIC_ONLY")
        self.assertFalse(r["independent_split_declared"])

    def test_group_leakage_fails_in_both_modes(self):
        m = self.manifest({"1": "g1", "2": "g1", "3": "g2"})
        roles = {"1": "source_selection", "2": "target_test", "3": "clear_test"}
        for mode in ("held_out", "diagnostic"):
            self.assertEqual(D.check_roles(m, roles, mode=mode)["status"], "FAIL")

    def test_clean_grouped_split_passes(self):
        m = self.manifest({"1": "g1", "2": "g1", "3": "g2"})
        r = D.check_roles(m, {"1": "source_selection", "2": "source_selection", "3": "clear_test"},
                          mode="held_out")
        self.assertEqual(r["status"], "PASS")

    def test_unknown_role_or_image(self):
        m = self.manifest({"1": "g1"})
        self.assertEqual(D.check_roles(m, {"1": "train"}, mode="held_out")["status"], "FAIL")
        self.assertEqual(D.check_roles(m, {"9": "clear_test"}, mode="held_out")["status"], "FAIL")


class FileAndCliTests(unittest.TestCase):
    def test_image_dimensions_png_and_jpeg(self):
        with tempfile.TemporaryDirectory() as td:
            png = Path(td) / "x.png"
            ihdr = struct.pack(">IIBBBBB", 37, 11, 8, 2, 0, 0, 0)
            png.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + ihdr
                            + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr)))
            self.assertEqual(D.image_dimensions(png), (37, 11))
            jpg = Path(td) / "x.jpg"
            app0 = b"\xff\xe0" + struct.pack(">H", 4) + b"\x00\x00"
            sof = b"\xff\xc0" + struct.pack(">HBHHB", 8, 8, 19, 23, 1)
            jpg.write_bytes(b"\xff\xd8" + app0 + sof + b"\xff\xd9")
            self.assertEqual(D.image_dimensions(jpg), (23, 19))

    def test_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "gt.json").write_text(json.dumps(coco_doc()))
            with gzip.open(td / "cache.json.gz", "wt") as f:
                json.dump(legacy_cache(), f)
            rc = D.main(["convert-coco", "--input", str(td / "gt.json"), "--out", str(td / "ann.json"),
                         "--dataset-tag", "t", "--ignore-policy", "coco_iscrowd_v1_provisional"])
            self.assertEqual(rc, 0)
            rc = D.main(["convert-legacy", "--input", str(td / "cache.json.gz"), "--out", str(td / "pred.json"),
                         "--map", "person=person", "--annotations", str(td / "ann.json")])
            self.assertEqual(rc, 0)
            pred = json.loads((td / "pred.json").read_text())
            self.assertEqual(pred["provenance"]["source"]["file_name"], "cache.json.gz")
            self.assertEqual(len(pred["provenance"]["source"]["sha256"]), 64)
            (td / "roles.json").write_text(json.dumps({"1": "source_selection", "2": "clear_test"}))
            rc = D.main(["check-roles", "--annotations", str(td / "ann.json"), "--roles",
                         str(td / "roles.json"), "--mode", "held_out", "--out", str(td / "r.json")])
            self.assertEqual(rc, 3)
            rc = D.main(["convert-legacy", "--input", str(td / "cache.json.gz"), "--out", str(td / "p2.json"),
                         "--map", "nope=person"])
            self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
