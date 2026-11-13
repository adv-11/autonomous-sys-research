"""Conclusion-relevant synthetic checks only; no restricted NightOwls records."""

import copy
import unittest

from threshold_transfer.data import PreflightError, check_roles
from threshold_transfer.metrics import ReferenceEvaluator
from threshold_transfer.nightowls import (
    EXPECTED_CATEGORIES, PRIMARY_PROFILE, SECONDARY_PROFILE, convert_nightowls,
)
from threshold_transfer.schema import SCHEMA_VERSION


def image(iid, *, daytime="night", recording=7.0):
    return {"id": iid, "file_name": f"synthetic-{iid}.png", "width": 300, "height": 100,
            "daytime": daytime, "recordings_id": recording, "timestamp": iid}


def ann(aid, *, iid=1, category=1, box=None, occluded=False, ignore=0):
    box = [0, 0, 20, 50] if box is None else box
    return {"id": aid, "image_id": iid, "category_id": category, "bbox": box,
            "area": box[2] * box[3], "occluded": occluded, "ignore": ignore,
            "difficult": True, "truncated": True, "pose_id": 999, "tracking_id": 3}


def native(images=None, annotations=None):
    return {"images": [image(1)] if images is None else images,
            "annotations": [] if annotations is None else annotations,
            "categories": [{"id": cid, "name": name} for cid, name in EXPECTED_CATEGORIES.items()],
            "poses": [{"id": 0, "name": "synthetic"}]}


def evaluator(converted, predictions=None):
    return ReferenceEvaluator(
        converted, {"schema_version": SCHEMA_VERSION, "predictions": predictions or [],
                    "provenance": {"candidate_policy": "synthetic only"}},
        **converted["provenance"]["evaluator_policy"])


class NightOwlsTests(unittest.TestCase):
    def test_keep_empty_night_exclude_dusk_without_gt_selection(self):
        doc = native([image(1), image(2), image(3, daytime="dusk")],
                     [ann(1), ann(2, iid=3)])
        for profile in (PRIMARY_PROFILE, SECONDARY_PROFILE):
            converted = convert_nightowls(doc, profile=profile)
            self.assertEqual(len(converted["images"]), 2)
            self.assertEqual(len(converted["annotations"]), 1)
            self.assertEqual(converted["provenance"]["summary"]["empty_image_count"], 1)
            self.assertEqual(len(evaluator(converted).annotations["images"]), 2)
        empty = convert_nightowls(native([image(1), image(2)]), profile=PRIMARY_PROFILE)
        self.assertEqual(len(empty["images"]), 2)
        self.assertEqual(empty["annotations"], [])

    def test_null_group_not_a_sequence_or_held_out_bypass(self):
        converted = convert_nightowls(
            native([image(1), image(2, recording=7), image(3, recording=None)]),
            profile=PRIMARY_PROFILE)
        groups = [i["group_id"] for i in converted["images"]]
        self.assertEqual(groups, ["nightowls:recording:7", "nightowls:recording:7", None])
        self.assertEqual(converted["provenance"]["summary"]["known_group_count"], 1)
        roles = {i["image_id"]: "target_test" for i in converted["images"]}
        self.assertEqual(check_roles(converted, roles, mode="held_out")["status"], "FAIL")
        self.assertEqual(check_roles(converted, roles, mode="diagnostic")["status"], "DIAGNOSTIC_ONLY")

    def test_native_height_occlusion_and_flags(self):
        records = [ann(1, box=[0, 0, 20, 49]), ann(2), ann(3, occluded=True),
                   ann(4, occluded=None), ann(5, ignore=1), ann(6, box=[-3, 90, 20, 50])]
        for profile in (PRIMARY_PROFILE, SECONDARY_PROFILE):
            converted = convert_nightowls(native(annotations=records), profile=profile)
            self.assertEqual([a["ignore"] for a in converted["annotations"]],
                             [True, False, True, False, True, False])
            self.assertEqual(converted["annotations"][-1]["bbox"], [-3, 90, 20, 50])
            self.assertEqual(converted["annotations"][1]["attributes"]["native"]["pose_id"], 999)
            self.assertEqual(evaluator(converted).gt_count, 3)

    def test_profile_scope_eligible_first_and_short_detection_absorption(self):
        records = [ann(1), ann(2, category=2, box=[0, 0, 40, 100]),
                   ann(3, category=3, box=[60, 0, 20, 60]),
                   ann(4, category=4, ignore=1, box=[90, 0, 20, 60]),
                   ann(5, box=[150, 0, 20, 49])]
        boxes = [[0, 0, 20, 50], [30, 0, 10, 20], [30, 0, 10, 20],
                 [60, 0, 10, 20], [100, 0, 20, 20], [150, 0, 10, 20]]
        predictions = [{"candidate_id": f"p{i}", "image_id": "nightowls:validation:img1",
                        "category": "human", "bbox": box, "score": 0.9 - i * 0.1}
                       for i, box in enumerate(boxes)]
        primary = convert_nightowls(native(annotations=records), profile=PRIMARY_PROFILE)
        secondary = convert_nightowls(native(annotations=records), profile=SECONDARY_PROFILE)
        self.assertEqual([r["outcome"] for r in evaluator(primary, predictions).rows],
                         ["TP", "IGNORED", "IGNORED", "IGNORED", "IGNORED", "IGNORED"])
        self.assertEqual([r["outcome"] for r in evaluator(secondary, predictions).rows],
                         ["TP", "FP", "FP", "FP", "FP", "IGNORED"])
        self.assertEqual(evaluator(primary).gt_count, evaluator(secondary).gt_count)
        self.assertEqual(len(secondary["annotations"]), 2)
        self.assertTrue(all(a["category"] == "human" for a in primary["annotations"]))
        self.assertEqual([a["attributes"]["native"]["category_id"] for a in primary["annotations"]],
                         [1, 2, 3, 4, 1])

    def test_pure_conversion_and_canonical_dict(self):
        doc = native(annotations=[ann(1)])
        source = {"path": "synthetic-only.json", "metadata": ["synthetic"]}
        before, source_before = copy.deepcopy(doc), copy.deepcopy(source)
        converted = convert_nightowls(doc, profile=PRIMARY_PROFILE, source=source)
        self.assertIsInstance(converted, dict)
        self.assertEqual(doc, before)
        self.assertEqual(source, source_before)
        converted["images"][0]["attributes"]["native"]["timestamp"] = -1
        converted["annotations"][0]["bbox"][0] = -1
        converted["annotations"][0]["attributes"]["native"]["occluded"] = True
        converted["provenance"]["source_files"][0]["metadata"].append("changed")
        self.assertEqual(doc, before)
        self.assertEqual(source, source_before)

    def test_refuse_ids_categories_and_geometry_even_when_omitted(self):
        base = native([image(1), image(2, daytime="dusk")], [ann(1, iid=2, category=2)])
        variants = []
        for collection in ("images", "annotations", "categories"):
            doc = copy.deepcopy(base)
            doc[collection].append(copy.deepcopy(doc[collection][0]))
            variants.append(doc)
        for field, value in (("image_id", 99), ("category_id", 99), ("id", True),
                             ("bbox", [0, 0, 0, 50]), ("bbox", [0, 0, 20, float("nan")]),
                             ("occluded", 1)):
            doc = copy.deepcopy(base)
            doc["annotations"][0][field] = value
            variants.append(doc)
        doc = copy.deepcopy(base)
        doc["images"][0]["recordings_id"] = 1.5
        variants.append(doc)
        for index, doc in enumerate(variants):
            with self.subTest(case=index), self.assertRaises(PreflightError):
                convert_nightowls(doc, profile=SECONDARY_PROFILE)


if __name__ == "__main__":
    unittest.main()
