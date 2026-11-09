"""Synthetic checks for Claude's smoke selection/export logic (no GPU, no real data).

These test implementation behavior only; they are not empirical results.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from threshold_transfer import smoke  # noqa: E402
from threshold_transfer.metrics import ReferenceEvaluator  # noqa: E402


def coco_doc():
    """Tiny native COCO document: person=1, car=3 (plus 78 fillers for the 80-class check)."""
    cats = [{"id": 1, "name": "person"}, {"id": 3, "name": "car"}]
    cats += [{"id": 100 + i, "name": f"c{i}"} for i in range(78)]
    images = [{"id": i, "file_name": f"{i:012d}.jpg", "width": 100, "height": 50} for i in range(1, 13)]
    anns, k = [], 0

    def add(image_id, cat, bbox, crowd=0, area=None):
        nonlocal k
        k += 1
        anns.append({"id": k, "image_id": image_id, "category_id": cat, "bbox": bbox,
                     "iscrowd": crowd, "area": area if area is not None else bbox[2] * bbox[3]})

    for _ in range(5):
        add(1, 1, [0, 0, 40, 40])          # image 1: 5 large persons (most crowded)
    for _ in range(3):
        add(2, 1, [0, 0, 40, 40])          # image 2: 3 persons
    add(3, 1, [0, 0, 40, 40], crowd=1)     # image 3: crowd region only
    add(4, 1, [0, 0, 10, 10])              # image 4: one small person (area 100)
    add(5, 3, [0, 0, 10, 10])              # image 5: car only
    add(6, 1, [0, 0, 40, 40])              # image 6: 1 large person
    # images 7..12: no annotations
    return {"images": images, "annotations": anns, "categories": cats}


QUOTAS = (("crowded_count", 2), ("iscrowd_person", 1), ("small_person", 1),
          ("empty", 2), ("no_person_nonempty", 1), ("general", 1))


class SelectionTests(unittest.TestCase):
    def test_strata_follow_the_documented_rule(self):
        rows = smoke.select_eval_images(coco_doc(), seed="s", quotas=QUOTAS)
        by = {}
        for r in rows:
            by.setdefault(r["stratum"], []).append(r["image_id"])
        self.assertEqual(by["crowded_count"], [1, 2])  # descending person count
        self.assertEqual(by["iscrowd_person"], [3])
        self.assertEqual(by["small_person"], [4])
        self.assertEqual(by["no_person_nonempty"], [5])
        self.assertTrue(set(by["empty"]) <= set(range(7, 13)))
        self.assertEqual(len({r["image_id"] for r in rows}), 8)  # no image claimed twice

    def test_selection_is_deterministic_and_seed_dependent(self):
        a = smoke.select_eval_images(coco_doc(), seed="s", quotas=QUOTAS)
        b = smoke.select_eval_images(coco_doc(), seed="s", quotas=QUOTAS)
        self.assertEqual(a, b)
        orders = {tuple(r["image_id"] for r in smoke.select_eval_images(coco_doc(), seed=s, quotas=QUOTAS)
                        if r["stratum"] == "empty") for s in ("a", "b", "c", "d", "e")}
        self.assertGreater(len(orders), 1)

    def test_unfillable_quota_raises_instead_of_shrinking(self):
        with self.assertRaises(ValueError):
            smoke.select_eval_images(coco_doc(), seed="s", quotas=(("iscrowd_person", 2),))

    def test_small_uses_native_area_and_excludes_crowd(self):
        doc = coco_doc()
        doc["annotations"].append({"id": 99, "image_id": 7, "category_id": 1, "bbox": [0, 0, 5, 5],
                                   "iscrowd": 1, "area": 25})
        stats = smoke.image_statistics(doc)
        self.assertEqual(stats[7]["n_small_person"], 0)
        self.assertEqual(stats[7]["n_crowd_person"], 1)
        self.assertEqual(stats[4]["n_small_person"], 1)

    def test_train_pool_contains_eval_images_first(self):
        pool = smoke.select_train_images(coco_doc(), [1, 7], seed="t", total=5)
        self.assertEqual(pool[:2], [1, 7])
        self.assertEqual(len(set(pool)), 5)
        with self.assertRaises(ValueError):
            smoke.select_train_images(coco_doc(), [1, 1], seed="t", total=5)

    def test_role_split_is_disjoint_and_complete(self):
        rows = smoke.select_eval_images(coco_doc(), seed="s", quotas=QUOTAS)
        roles = smoke.split_roles(rows)
        ids = [i for v in roles.values() for i in v]
        self.assertEqual(sorted(ids), sorted(r["image_id"] for r in rows))
        self.assertEqual(len(ids), len(set(ids)))


class YoloLabelTests(unittest.TestCase):
    def test_normalized_clipped_and_crowd_skipped(self):
        ids = smoke.coco80_category_ids(coco_doc())
        anns = [{"id": 1, "category_id": 3, "bbox": [90, 10, 20, 20], "iscrowd": 0},
                {"id": 2, "category_id": 1, "bbox": [0, 0, 10, 10], "iscrowd": 1}]
        lines, skipped = smoke.yolo_label_lines(anns, width=100, height=50, category_ids=ids)
        self.assertEqual(skipped, 1)
        # Clipped to x in [90,100]: centre 95/100, width 10/100; y centre 20/50, height 20/50.
        self.assertEqual(lines, ["1 0.950000 0.400000 0.100000 0.400000"])

    def test_box_entirely_outside_is_rejected(self):
        ids = smoke.coco80_category_ids(coco_doc())
        with self.assertRaises(ValueError):
            smoke.yolo_label_lines([{"id": 1, "category_id": 1, "bbox": [120, 0, 5, 5], "iscrowd": 0}],
                                   width=100, height=50, category_ids=ids)

    def test_requires_80_categories(self):
        doc = coco_doc()
        doc["categories"] = doc["categories"][:10]
        with self.assertRaises(ValueError):
            smoke.coco80_category_ids(doc)


def annotations():
    return {"schema_version": "threshold-transfer-v1",
            "images": [{"image_id": "a", "width": 100, "height": 100},
                       {"image_id": "empty", "width": 100, "height": 100}],
            "annotations": [{"annotation_id": "g1", "image_id": "a", "category": "person",
                             "bbox": [0, 0, 10, 10], "ignore": False, "iscrowd": False}],
            "provenance": {"dataset": "synthetic"}}


class ExportTests(unittest.TestCase):
    def export(self, rows, **kw):
        args = dict(model_key="m", evaluated_image_ids=["a", "empty"],
                    image_sizes={"a": (100, 100), "empty": (100, 100)}, score_floor=0.1, max_detections=2)
        args.update(kw)
        return smoke.export_candidates(rows, **args)

    def test_floor_cap_order_and_empty_images(self):
        rows = {"a": [(0, 0, 10, 10, 0.5, "person"), (50, 50, 60, 60, 0.9, "car"),
                      (0, 0, 10, 10, 0.05, "person"), (5, 5, 15, 15, 0.5, "person")],
                "empty": []}
        doc, summary = self.export(rows)
        preds = doc["predictions"]
        self.assertEqual([p["score"] for p in preds], [0.9, 0.5])
        self.assertEqual(preds[1]["bbox"], [0.0, 0.0, 10.0, 10.0])  # tie broken by native rank
        self.assertEqual(preds[0]["bbox"], [50.0, 50.0, 10.0, 10.0])  # xyxy -> xywh
        a = summary["per_image"]["a"]
        self.assertEqual((a["below_floor"], a["removed_by_cap"], a["kept"], a["kept_person"]), (1, 1, 2, 1))
        self.assertTrue(a["cap_binding"])
        self.assertEqual(summary["per_image"]["empty"]["kept"], 0)
        self.assertEqual(doc["provenance"]["evaluated_image_ids"], ["a", "empty"])
        self.assertEqual(summary["images_zero_kept"], 1)
        smoke.validate_pair(annotations(), doc)

    def test_floor_is_inclusive_and_not_rounded(self):
        doc, _ = self.export({"a": [(0, 0, 10.123456789, 10, 0.1, "person")], "empty": []})
        self.assertEqual(doc["predictions"][0]["bbox"][2], 10.123456789)
        self.assertEqual(doc["predictions"][0]["score"], 0.1)

    def test_missing_image_rows_fail_closed(self):
        with self.assertRaises(ValueError):
            self.export({"a": []})
        with self.assertRaises(ValueError):
            self.export({"a": [], "empty": [], "other": []})

    def test_degenerate_policy(self):
        rows = {"a": [(10, 10, 10, 20, 0.5, "person")], "empty": []}
        with self.assertRaises(ValueError):
            self.export(rows)
        _, summary = self.export(rows, degenerate_policy="drop_and_count")
        self.assertEqual(summary["degenerate_dropped"], 1)

    def test_nonfinite_and_out_of_range_scores_rejected(self):
        with self.assertRaises(ValueError):
            self.export({"a": [(0, 0, 1, 1, float("nan"), "person")], "empty": []})
        with self.assertRaises(ValueError):
            self.export({"a": [(0, 0, 1, 1, 1.5, "person")], "empty": []})

    def test_outside_boxes_counted_not_clipped_and_evaluable(self):
        doc, summary = self.export({"a": [(-5, 0, 10, 10, 0.9, "person")], "empty": []})
        self.assertEqual(summary["outside_image_bounds"], 1)
        self.assertEqual(doc["predictions"][0]["bbox"], [-5.0, 0.0, 15.0, 10.0])
        ev = ReferenceEvaluator(annotations(), doc, categories=["person"], bounds_policy="allow_outside")
        point = ev.operating_point()
        self.assertEqual((point["tp"], point["image_count"]), (1, 2))  # IoU 100/150 >= 0.5

    def test_restrict_predictions_keeps_role_coverage(self):
        doc, _ = self.export({"a": [(0, 0, 10, 10, 0.9, "person")], "empty": [(0, 0, 5, 5, 0.3, "car")]})
        part = smoke.restrict_predictions(doc, ["empty"])
        self.assertEqual(part["provenance"]["evaluated_image_ids"], ["empty"])
        self.assertEqual([p["image_id"] for p in part["predictions"]], ["empty"])
        with self.assertRaises(ValueError):
            smoke.restrict_predictions(doc, ["missing"])


class CensoringTests(unittest.TestCase):
    def test_cap_censoring_counts_removed_person_candidates(self):
        rows = {"a": [(0, 0, 10, 10, 0.9 - i / 100, "person" if i % 2 else "car") for i in range(5)], "empty": []}
        args = dict(model_key="m", evaluated_image_ids=["a", "empty"],
                    image_sizes={"a": (100, 100), "empty": (100, 100)}, score_floor=0.0)
        _, small = smoke.export_candidates(rows, max_detections=2, **args)
        _, large = smoke.export_candidates(rows, max_detections=10, **args)
        result = smoke.cap_censoring(small, large)
        self.assertEqual(result["candidates_removed_by_primary_cap"], 3)
        self.assertEqual(result["person_candidates_removed_by_primary_cap"], 1)  # ranks 3 (person) of 2..4
        self.assertEqual(result["images_with_cap_removal"], 1)
        self.assertTrue(result["exact"])
        _, tight = smoke.export_candidates(rows, max_detections=3, **args)
        self.assertFalse(smoke.cap_censoring(small, tight)["exact"])  # sensitivity cap also binds
        with self.assertRaises(ValueError):
            smoke.cap_censoring(large, small)


class CanonicalSubsetTests(unittest.TestCase):
    def test_subset_preserves_group_and_empty_images(self):
        doc = annotations()
        doc["images"][1]["group_id"] = None
        sub = smoke.canonical_subset(doc, ["empty"], note="t")
        self.assertEqual(sub["images"], [doc["images"][1]])
        self.assertEqual(sub["annotations"], [])
        self.assertEqual(sub["provenance"]["subset"]["image_count"], 1)
        with self.assertRaises(ValueError):
            smoke.canonical_subset(doc, ["nope"], note="t")


if __name__ == "__main__":
    unittest.main()
