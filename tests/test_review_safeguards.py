"""Regression cases for concrete gaps reported by Claude's evaluator review."""

import copy
import json
import unittest

from threshold_transfer.evaluate import evaluate_transfer
from threshold_transfer.metrics import ReferenceEvaluator
from test_evaluate import example
from test_metrics import documents, gt, pred


class ReviewSafeguards(unittest.TestCase):
    def test_held_out_requires_inference_population_and_native_dataset(self):
        for collection, key, message in ((1, "evaluated_image_ids", "evaluated_image_ids"),
                                         (0, "dataset", "provenance.dataset")):
            docs, policy = example()
            del docs["target_test"][collection]["provenance"][key]
            with self.assertRaisesRegex(ValueError, message):
                evaluate_transfer(docs, policy=policy, target_recall=.5)
        docs, policy = example()
        docs["clear_test"] = copy.deepcopy(docs["source_selection"])
        for annotations, _ in docs.values():
            del annotations["provenance"]["dataset"]
        policy["roles"]["clear_test"].update(dataset_id="renamed", group_namespace="renamed")
        with self.assertRaisesRegex(ValueError, "provenance.dataset"):
            evaluate_transfer(docs, policy=policy, target_recall=.5)

    def test_held_out_rejects_missing_different_or_incomplete_pipeline(self):
        for change in ("missing", "model", "floor", "cap", "hash", "preprocessing"):
            with self.subTest(change=change):
                docs, policy = example()
                provenance = docs["target_test"][1]["provenance"]
                pipeline = provenance["inference_pipeline"]
                if change == "missing":
                    del provenance["inference_pipeline"]
                elif change == "model": pipeline["model_id"] = "other-model"
                elif change == "floor": pipeline["candidate_policy"]["score_floor"] = .85
                elif change == "cap": pipeline["candidate_policy"]["max_detections"] = 100
                elif change == "hash": pipeline["checkpoint_sha256"] = "unknown"
                else: del pipeline["preprocessing"]
                with self.assertRaises(ValueError):
                    evaluate_transfer(docs, policy=policy, target_recall=.5)

    def test_diagnostic_censoring_is_explicit_not_held_out(self):
        docs, policy = example()
        policy["population_mode"] = "diagnostic"
        for _, predictions in docs.values():
            del predictions["provenance"]["inference_pipeline"]
        docs["target_test"][1]["provenance"]["cache_policy"] = {"score_floor": .85}
        result = evaluate_transfer(docs, policy=policy, target_recall=.5)
        self.assertEqual(result["role_validation"]["status"], "DIAGNOSTIC")
        self.assertTrue(result["candidate_visibility"]["target_test"]["threshold_below_floor"])
        self.assertTrue(any("censored" in line for line in result["role_validation"]["limitations"]))
        json.dumps(result, allow_nan=False)

    def test_recorded_floor_disagreement_and_threshold_censoring(self):
        docs, policy = example()
        docs["target_test"][1]["provenance"]["cache_policy"] = {"score_floor": .85}
        with self.assertRaisesRegex(ValueError, "pipeline/cache score floor mismatch"):
            evaluate_transfer(docs, policy=policy, target_recall=.5)
        for _, predictions in docs.values():
            predictions["provenance"].pop("cache_policy", None)
            predictions["provenance"]["inference_pipeline"]["candidate_policy"]["score_floor"] = .85
        with self.assertRaisesRegex(ValueError, "below the recorded"):
            evaluate_transfer(docs, policy=policy, target_recall=.5)
        docs, policy = example()
        for field in ("max_raw_det", "max_raw_det_per_image"):
            docs["target_test"][1]["provenance"]["cache_policy"] = {field: 100}
            with self.assertRaisesRegex(ValueError, "pipeline/cache candidate cap mismatch"):
                evaluate_transfer(docs, policy=policy, target_recall=.5)

    def test_paired_views_may_share_groups_but_never_image_identity(self):
        docs, policy = example()
        policy["test_relationship"] = "paired"
        docs["target_test"] = copy.deepcopy(docs["clear_test"])
        with self.assertRaisesRegex(ValueError, "image overlap"):
            evaluate_transfer(docs, policy=policy, target_recall=.5)

    def test_compact_default_and_explicit_match_rows(self):
        docs, policy = example()
        compact = evaluate_transfer(docs, policy=policy, target_recall=.5)
        expanded = evaluate_transfer(docs, policy=policy, target_recall=.5, include_matches=True)
        self.assertFalse(compact["match_rows_included"])
        self.assertNotIn("matches", compact["selection"]["candidate_ceiling"])
        self.assertIn("matches", expanded["selection"]["candidate_ceiling"])
        self.assertEqual(compact["held_out_loss"], expanded["held_out_loss"])

    def test_exact_decimal_headroom_boundary(self):
        annotations = [gt(f"g-{i}", img=f"im-{i}") for i in range(50)]
        predictions = [pred(f"p-{i}", .8, img=f"im-{i}") for i in range(41)]
        images = [{"image_id": f"im-{i}"} for i in range(50)]
        ev = ReferenceEvaluator(*documents(annotations, predictions, images), categories=["pedestrian"])
        result = ev.select_threshold(.8)
        self.assertEqual(result["headroom"]["value"], .02)
        self.assertEqual(result["headroom_flag"], "ADEQUATE")


if __name__ == "__main__":
    unittest.main()
