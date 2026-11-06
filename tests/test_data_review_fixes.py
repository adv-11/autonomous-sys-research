"""Regression repros from GPT's converter review, using disposable fixtures only."""

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from threshold_transfer import data as D
from threshold_transfer.metrics import ReferenceEvaluator
from test_data import coco_doc, kitti_doc, legacy_cache


def coco(document=None, **kwargs):
    return D.convert_coco(coco_doc() if document is None else document, dataset_tag="toy",
                          split=None, ignore_policy="no_ignore_declared", **kwargs)


class DataReviewFixes(unittest.TestCase):
    def test_cli_never_overwrites_inputs_or_existing_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.json"
            source.write_text(json.dumps(coco_doc()), encoding="utf-8")
            original = source.read_bytes()
            base = ["convert-coco", "--input", str(source), "--dataset-tag", "toy",
                    "--ignore-policy", "no_ignore_declared"]
            self.assertEqual(D.main(base + ["--out", str(source)]), 2)
            alias = root / "alias.json"
            os.link(source, alias)
            self.assertEqual(D.main(base + ["--out", str(alias)]), 2)
            self.assertEqual(source.read_bytes(), original)
            self.assertEqual(alias.read_bytes(), original)
            roles = root / "roles.json"
            roles.write_text('{"1":"clear_test"}', encoding="utf-8")
            self.assertEqual(D.main(["check-roles", "--annotations", str(source), "--roles",
                                     str(roles), "--mode", "held_out", "--out", str(roles)]), 2)
            self.assertEqual(roles.read_text(encoding="utf-8"), '{"1":"clear_test"}')
            manifest, cache = root / "manifest.json", root / "cache.json"
            manifest.write_text(json.dumps(coco()), encoding="utf-8")
            cache.write_text(json.dumps(legacy_cache()), encoding="utf-8")
            manifest_bytes = manifest.read_bytes()
            self.assertEqual(D.main(["convert-legacy", "--input", str(cache), "--annotations",
                                     str(manifest), "--out", str(manifest), "--map", "person=person"]), 2)
            self.assertEqual(manifest.read_bytes(), manifest_bytes)

    def test_inventory_output_cannot_be_in_asset_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            assets = root / "assets"
            assets.mkdir()
            config = root / "config.json"
            config.write_text(json.dumps({"asset_root": str(assets)}), encoding="utf-8")
            output = assets / "must-not-exist.json"
            self.assertEqual(D.main(["inventory", "--config", str(config), "--out", str(output)]), 2)
            self.assertFalse(output.exists())
            self.assertEqual(D.main(["inventory", "--config", str(config), "--out", str(config)]), 2)

    def test_strict_json_and_cli_errors_preserve_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / "source.json", root / "out.json"
            command = ["convert-coco", "--input", str(source), "--out", str(output),
                       "--dataset-tag", "toy", "--ignore-policy", "no_ignore_declared"]
            for invalid in ('{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}',
                            '{"x":1e309}', '{', '[]', '{"images":[7]}'):
                with self.subTest(invalid=invalid):
                    source.write_text(invalid, encoding="utf-8")
                    output.write_bytes(b"existing-output")
                    self.assertEqual(D.main(command), 2)
                    self.assertEqual(output.read_bytes(), b"existing-output")
            source.unlink()
            self.assertEqual(D.main(command), 2)

    def test_atomic_serialization_and_replace_failures_leave_existing_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "out.json"
            output.write_bytes(b"sentinel")
            with self.assertRaises(D.PreflightError):
                D.write_json({"bad": float("inf")}, output)
            with patch.object(D.os, "replace", side_effect=OSError("simulated replace failure")):
                with self.assertRaises(OSError):
                    D.write_json({"valid": True}, output)
            self.assertEqual(output.read_bytes(), b"sentinel")
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_dictionary_converter_outputs_work_without_json_roundtrip(self):
        annotations = coco()
        predictions = D.convert_legacy_predictions(legacy_cache(), category_mapping={"person":"person"},
                                                   annotations=annotations)
        self.assertEqual(predictions["provenance"]["validation"]["label_index_histogram"]["0"], 3)
        ev = ReferenceEvaluator(annotations, predictions, categories=["person"],
                                ignore_policy="same_category_ioa", bounds_policy="allow_outside")
        self.assertEqual(ev.operating_point()["image_count"], 3)
        json.dumps(predictions, allow_nan=False)

    def test_category_identity_policy_rejects_aliases_and_preserves_native_ids(self):
        for bad in (True, 1.0, None):
            document = coco_doc()
            document["annotations"][0]["category_id"] = bad
            with self.assertRaises(D.PreflightError): coco(document)
            document = coco_doc()
            document["categories"][0]["id"] = bad
            with self.assertRaises(D.PreflightError): coco(document)
        document = coco_doc()
        document["categories"].append({"id":"1", "name":"other"})
        with self.assertRaises(D.PreflightError): coco(document)
        self.assertEqual(coco()["provenance"]["native_category_ids"]["person"], 1)
        with self.assertRaises(D.PreflightError): D.canonical_id("   ", "id")

    def test_final_float_geometry_validation_and_serializable_exclusions(self):
        boxes = ([1e308,0,1e308,1], [2**53,0,1,1], [0,0,1e-300,1e-300],
                 [0,0,10**400,1], [0,0,float("nan"),1])
        for box in boxes:
            document = coco_doc()
            document["annotations"][0]["bbox"] = list(box)
            with self.assertRaises(D.PreflightError): coco(document)
            excluded = coco(document, invalid_box_policy="exclude_and_report")
            self.assertEqual(sum(excluded["provenance"]["validation"]["invalid_boxes"].values()), 1)
            json.dumps(excluded, allow_nan=False)
        for corners in ([-1e308,0,1e308,1], [2**53,0,2**53+1,1], [0,0,10**400,1]):
            cache = legacy_cache()
            cache["detections"] = [[1,*corners,.5,0]]
            with self.assertRaises(D.PreflightError):
                D.convert_legacy_predictions(cache, category_mapping={"person":"person"})
            result = D.convert_legacy_predictions(cache, category_mapping={"person":"person"},
                                                   invalid_row_policy="exclude_and_report")
            self.assertEqual(result["predictions"], [])
            json.dumps(result, allow_nan=False)
        document = coco_doc()
        document["annotations"][0]["area"] = float("inf")
        with self.assertRaises(D.PreflightError): coco(document)

    def test_role_checker_cannot_hide_duplicates_or_assert_independence(self):
        manifest = {"images":[{"image_id":"1","group_id":"shared"},
                              {"image_id":"2","group_id":"shared"},
                              {"image_id":"1","group_id":"other"}]}
        with self.assertRaises(D.PreflightError):
            D.check_roles(manifest, {"1":"source_selection","2":"clear_test"}, mode="held_out")
        for group in ("", "   ", 1):
            with self.assertRaises(D.PreflightError):
                D.check_roles({"images":[{"image_id":"1","group_id":group}]},
                              {"1":"clear_test"}, mode="held_out")
        self.assertEqual(D.check_roles({"images":[]}, {}, mode="held_out")["status"], "FAIL")
        clean = D.check_roles({"images":[{"image_id":"1","group_id":"g"}]},
                              {"1":"clear_test"}, mode="held_out")
        self.assertEqual(clean["status"], "PASS")
        self.assertTrue(clean["declared_groups_consistent"])
        self.assertFalse(clean["independent_split_declared"])

    def test_invalid_neighbour_box_does_not_change_policy_population(self):
        document = kitti_doc()
        neighbour = next(a for a in document["annotations"] if a["ignore_reason"] == "neighbour:Person_sitting")
        neighbour["bbox"] = [1,1,0,9]
        result = D.convert_kitti_derived(document, dataset_tag="toy", split=None,
                                         policy=D.KITTI_DIAGNOSTIC_POLICY, invalid_box_policy="exclude_and_report")
        self.assertNotIn("2", [i["image_id"] for i in result["images"]])
        self.assertEqual(result["provenance"]["excluded_neighbour_image_count"], 1)


if __name__ == "__main__": unittest.main()
