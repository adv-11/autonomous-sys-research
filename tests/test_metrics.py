"""Synthetic protocol checks by GPT; these are not empirical research results."""

import copy
import math
import unittest

from threshold_transfer.metrics import (ReferenceEvaluator, binary_tp_ece,
    held_out_loss_decomposition, target_gap_decomposition)


def image(key, **kwargs):
    return {"image_id": key, "width": 100, "height": 100, **kwargs}


def gt(key, box=None, *, img="scene", category="pedestrian", **kwargs):
    return {"annotation_id": key, "image_id": img, "category": category,
            "bbox": box or [0, 0, 10, 10], "ignore": False, "iscrowd": False, **kwargs}


def pred(key, score, box=None, *, img="scene", category="pedestrian"):
    return {"candidate_id": key, "image_id": img, "category": category,
            "bbox": box or [0, 0, 10, 10], "score": score}


def documents(gts=(), preds=(), images=None):
    images = [image("scene")] if images is None else images
    return ({"schema_version": "threshold-transfer-v1", "images": images,
             "annotations": list(gts), "provenance": {"dataset": "synthetic"}},
            {"schema_version": "threshold-transfer-v1", "predictions": list(preds),
             "provenance": {"evaluated_image_ids": [i["image_id"] for i in images]}})


def evaluator(gts=(), preds=(), images=None, **kwargs):
    return ReferenceEvaluator(*documents(gts, preds, images), categories=["pedestrian"], **kwargs)


class MatchingTests(unittest.TestCase):
    def test_empty_scenes_are_in_fppi_and_object_weighted_recall(self):
        ev = evaluator([gt("g1"), gt("g2", [20, 0, 10, 10])],
                       [pred("p", .8), pred("empty-fp", .7, img="empty")],
                       [image("scene"), image("empty"), image("silent")])
        point = ev.operating_point(.7)
        self.assertEqual((point["tp"], point["fp"], point["fn"]), (1, 1, 1))
        self.assertEqual(point["recall"]["value"], .5)
        self.assertEqual(point["precision"]["value"], .5)
        self.assertEqual(point["fppi"]["value"], 1 / 3)

    def test_iou_inclusive_and_eligible_before_reusable_ignore_ioa(self):
        ev = evaluator([gt("g", [0, 0, 10, 10]),
                        gt("ignore", [0, 0, 100, 100], ignore=True)],
                       [pred("a", .9, [0, 0, 5, 10]),  # exactly .5 IoU
                        pred("b", .8, [20, 20, 2, 2]),
                        pred("c", .7, [30, 30, 2, 2])], ignore_policy="same_category_ioa")
        self.assertEqual([r["outcome"] for r in ev.rows], ["TP", "IGNORED", "IGNORED"])
        self.assertEqual(ev.operating_point()["fn"], 0)
        with self.assertRaisesRegex(ValueError, "explicit ignore"):
            evaluator([gt("i", iscrowd=True)])

    def test_category_ignore_scope_and_no_aliases(self):
        docs = documents([gt("g", category="rider"),
                          gt("i", category="other", iscrowd=True)], [pred("p", .8)])
        same = ReferenceEvaluator(*docs, categories=["pedestrian"], ignore_policy="same_category_ioa")
        any_class = ReferenceEvaluator(*docs, categories=["pedestrian"], ignore_policy="all_categories_ioa")
        self.assertEqual(same.rows[0]["outcome"], "FP")
        self.assertEqual(any_class.rows[0]["outcome"], "IGNORED")
        self.assertEqual(same.operating_point()["recall"]["status"], "UNDEFINED")
        docs[0]["annotations"] = [gt("g", category="Pedestrian")]
        self.assertEqual(ReferenceEvaluator(*docs, categories=["pedestrian"]).gt_count, 0)

    def test_score_candidate_and_annotation_id_ties_ordering_invariance(self):
        anns, preds = documents([gt("b"), gt("a")], [pred("z", .8), pred("a", .8), pred("third", .7)])
        baseline = ReferenceEvaluator(anns, preds, categories=["pedestrian"])
        self.assertEqual([(r["candidate_id"], r["annotation_id"], r["outcome"]) for r in baseline.rows],
                         [("a", "a", "TP"), ("z", "b", "TP"), ("third", None, "FP")])
        anns["annotations"].reverse()
        preds["predictions"].reverse()
        self.assertEqual(ReferenceEvaluator(anns, preds, categories=["pedestrian"]).operating_point(),
                         baseline.operating_point())

    def test_greedy_prefix_is_not_maximum_cardinality(self):
        # a overlaps g1 at .667, g2 at .538; b can match only g1.
        ev = evaluator([gt("g1"), gt("g2", [5, 0, 10, 10])],
                       [pred("a", .9, [2, 0, 10, 10]), pred("b", .8)])
        self.assertEqual([(r["outcome"], r["annotation_id"]) for r in ev.rows], [("TP", "g1"), ("FP", None)])
        self.assertEqual(ev.operating_point()["recall"]["value"], .5)

    def test_no_gt_and_no_images_have_explicit_undefined_quantities(self):
        point = evaluator(preds=[pred("p", .5)]).operating_point()
        self.assertEqual(point["recall"], {"value": None, "status": "UNDEFINED"})
        self.assertEqual(point["precision"]["value"], 0)
        self.assertEqual(point["fppi"]["value"], 1)
        empty = evaluator(images=[]).operating_point()
        for key in ("recall", "precision", "fppi", "binary_tp_ece"):
            self.assertEqual(empty[key]["status"], "UNDEFINED")

    def test_ignore_ioa_boundary_and_wrong_class_gt_is_fp(self):
        ev = evaluator([gt("i", [0, 0, 5, 10], ignore=True),
                        gt("r", [20, 0, 10, 10], category="rider")],
                       [pred("a", .8), pred("b", .7, [20, 0, 10, 10])], ignore_policy="same_category_ioa")
        self.assertEqual([r["outcome"] for r in ev.rows], ["IGNORED", "FP"])


class ValidationTests(unittest.TestCase):
    def test_bad_ids_boxes_scores_flags_references_rejected_before_filtering(self):
        base = documents([gt("g")], [pred("p", .5)])
        changes = [
            (0, "images", 0, "image_id", ""),
            (0, "images", 0, "width", 0),
            (0, "annotations", 0, "ignore", 1),
            (0, "annotations", 0, "iscrowd", None),
            (0, "annotations", 0, "attributes", []),
            (0, "annotations", 0, "bbox", [0, 0, -1, 2]),
            (0, "annotations", 0, "bbox", [0, 0, 0, 2]),
            (1, "predictions", 0, "bbox", [0, 0, math.nan, 2]),
            (1, "predictions", 0, "bbox", [0, 0, math.inf, 2]),
            (1, "predictions", 0, "bbox", [0, 0, 2]),
            (1, "predictions", 0, "bbox", [99, 0, 2, 2]),
            (1, "predictions", 0, "score", -.01),
            (1, "predictions", 0, "score", 1.01),
            (1, "predictions", 0, "score", True),
            (1, "predictions", 0, "image_id", "unknown"),
            (1, "predictions", 0, "candidate_id", 1),
        ]
        for doc, collection, index, key, value in changes:
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(base)
                changed[doc][collection][index][key] = value
                with self.assertRaises(ValueError):
                    ReferenceEvaluator(*changed, categories=["not-selected"])

    def test_duplicate_collection_ids_and_incomplete_inference_population(self):
        for doc, collection in ((0, "images"), (0, "annotations"), (1, "predictions")):
            docs = documents([gt("g")], [pred("p", .5)])
            docs[doc][collection] *= 2
            with self.subTest(collection=collection), self.assertRaisesRegex(ValueError, "duplicate"):
                ReferenceEvaluator(*docs, categories=["pedestrian"])
        docs = documents(images=[image("scene"), image("empty")])
        docs[1]["provenance"]["evaluated_image_ids"] = ["scene"]
        with self.assertRaisesRegex(ValueError, "complete annotation"):
            ReferenceEvaluator(*docs, categories=["pedestrian"])

    def test_unknown_dimensions_and_explicit_outside_policy_no_repair(self):
        docs = documents([gt("g", [-1, 0, 10, 10])], [pred("p", .8, [-1, 0, 10, 10])])
        with self.assertRaises(ValueError):
            ReferenceEvaluator(*docs, categories=["pedestrian"])
        ev = ReferenceEvaluator(*docs, categories=["pedestrian"], bounds_policy="allow_outside")
        self.assertEqual(ev.operating_point()["recall"]["value"], 1)
        self.assertEqual(ev.annotations["annotations"][0]["bbox"][0], -1)
        docs[0]["images"][0]["width"] = None
        ev = ReferenceEvaluator(*docs, categories=["pedestrian"])
        self.assertTrue(any("missing dimensions" in x for x in ev.limitations))


class SelectionAndDiagnosticsTests(unittest.TestCase):
    def test_whole_ties_highest_observed_score_infeasible_and_undefined(self):
        ev = evaluator([gt("a"), gt("b", [20, 0, 10, 10])],
                       [pred("one", .8), pred("fp", .8, [50, 0, 10, 10]), pred("two", .4, [20, 0, 10, 10])])
        selected = ev.select_threshold(.5)
        self.assertEqual(selected["threshold"], .8)
        self.assertEqual(selected["boundary_tie_count"], 2)
        self.assertEqual(selected["operating_point"]["fp"], 1)
        self.assertEqual(selected["next_lower_score"], .4)
        self.assertEqual(ev.select_threshold(1)["threshold"], .4)
        self.assertEqual(evaluator([gt("a")]).select_threshold(.9)["status"], "INFEASIBLE")
        self.assertIsNone(evaluator([gt("a")]).select_threshold(.9)["threshold"])
        self.assertEqual(evaluator().select_threshold(.9)["status"], "UNDEFINED")
        self.assertEqual(evaluator([gt("a")], [pred("p", 0)]).select_threshold(1)["threshold"], 0)

    def test_strict_monotone_mapping_preserves_source_and_target_sets(self):
        source = documents([gt("a"), gt("b", [20, 0, 10, 10])],
                           [pred("one", .8), pred("fp", .8, [50, 0, 10, 10]), pred("two", .4, [20, 0, 10, 10])])
        target = documents([gt("g")], [pred("unseen-score", .62), pred("tie", .8, [50, 0, 10, 10])])
        original_sets = None
        for transform in (lambda s: s, lambda s: s ** 2, lambda s: .1 + .8 * s):
            src, tgt = copy.deepcopy(source), copy.deepcopy(target)
            for docs in (src, tgt):
                for p in docs[1]["predictions"]:
                    p["score"] = transform(p["score"])
            selected = ReferenceEvaluator(*src, categories=["pedestrian"]).select_threshold(.5)
            self.assertEqual(selected["threshold"], transform(.8))
            result = ReferenceEvaluator(*tgt, categories=["pedestrian"]).operating_point(selected["threshold"])
            sets = ([r["candidate_id"] for r in selected["operating_point"]["matches"]],
                    [r["candidate_id"] for r in result["matches"]], result["fppi"], result["recall"])
            if original_sets is None:
                original_sets = sets
            self.assertEqual(sets, original_sets)

    def test_midpoint_counterexample_on_unseen_target_score(self):
        ev = evaluator([gt("a")], [pred("target", .62)])
        transformed = evaluator([gt("a")], [pred("target", .62 ** 2)])
        raw_midpoint = (.8 + .4) / 2
        transformed_midpoint = (.8 ** 2 + .4 ** 2) / 2
        self.assertEqual(ev.operating_point(raw_midpoint)["tp"], 1)
        self.assertEqual(transformed.operating_point(transformed_midpoint)["tp"], 0)

    def test_target_decompositions_positive_signed_and_overachievement(self):
        for rho, r, m in ((.9, .5, .8), (.9, .8, 1), (.8, .9, 1), (.9, .95, .95)):
            with self.subTest(rho=rho, r=r, m=m):
                d = {k: v["value"] for k, v in target_gap_decomposition(rho, r, m).items()}
                self.assertAlmostEqual(d["shortfall"], d["ceiling_shortfall"] + d["removable_shortfall"])
                self.assertAlmostEqual(d["signed_gap"], d["ceiling_shortfall"] + d["signed_threshold_component"])
                self.assertGreaterEqual(d["shortfall"], 0)
        self.assertLess(target_gap_decomposition(.8, .9, 1)["signed_threshold_component"]["value"], 0)
        self.assertTrue(all(v["status"] == "UNDEFINED" for v in target_gap_decomposition(.9, None, None).values()))

    def test_held_out_loss_identity_including_negative_components(self):
        for values in ((.8, .5, .9, .8), (.5, .8, .9, .8), (.8, .5, .8, 1)):
            d = {k: v["value"] for k, v in held_out_loss_decomposition(*values).items()}
            self.assertAlmostEqual(d["held_out_loss"], d["ceiling_difference"] + d["threshold_miss_difference"])
        with self.assertRaises(ValueError):
            held_out_loss_decomposition(.9, .5, .8, 1)

    def test_binary_tp_ece_endpoints_empty_bins_and_ignores(self):
        rows = [{"score": 0, "outcome": "TP"}, {"score": 1, "outcome": "FP"},
                {"score": .5, "outcome": "TP"}, {"score": .7, "outcome": "IGNORED"}]
        result = binary_tp_ece(rows, 4)
        self.assertAlmostEqual(result["value"], 2.5 / 3)
        self.assertEqual([b["count"] for b in result["bins"]], [1, 0, 1, 1])
        self.assertIsNone(result["bins"][1]["mean_score"])
        self.assertEqual(binary_tp_ece(rows[-1:])["status"], "UNDEFINED")


if __name__ == "__main__":
    unittest.main()
