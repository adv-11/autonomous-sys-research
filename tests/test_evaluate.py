"""Hand-counted synthetic end-to-end and role-leakage checks by GPT."""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from threshold_transfer.evaluate import ROLES, evaluate_transfer
from threshold_transfer.schema import load_json
from test_metrics import documents, gt, image, pred


def example():
    docs = {}
    # One threshold-selection TP at .8; a second GT is recovered at .4.
    docs["source_selection"] = documents(
        [gt("s1", img="s"), gt("s2", [20, 0, 10, 10], img="s")],
        [pred("s-a", .8, img="s"), pred("s-b", .4, [20, 0, 10, 10], img="s")],
        [image("s", group_id="source-trip")])
    # Independent clear-test recall=1 and ceiling=1, with one empty-scene FP.
    docs["clear_test"] = documents([gt("c1", img="c")],
        [pred("c-a", .9, img="c"), pred("c-fp", .85, img="ce")],
        [image("c", group_id="clear-trip"), image("ce", group_id="clear-trip")])
    # Target recall=.25 and ceiling=.75; one FP on an empty image.
    docs["target_test"] = documents(
        [gt(f"t{i}", [i * 20, 0, 10, 10], img="t") for i in range(4)],
        [pred("t-a", .8, img="t"), pred("t-b", .7, [20, 0, 10, 10], img="t"),
         pred("t-c", .1, [40, 0, 10, 10], img="t"), pred("t-fp", .9, img="te")],
        [image("t", group_id="target-trip"), image("te", group_id="target-trip")])
    policy = {"categories": ["pedestrian"], "ignore_policy": "reject", "bounds_policy": "strict_known",
              "population_mode": "held_out", "test_relationship": "disjoint",
              "roles": {role: {"dataset_id": "synthetic", "group_namespace": "synthetic-trips",
                         "population": f"synthetic {role}", "group_provenance": "synthetic independent trip construction"}
                        for role in ROLES}}
    return docs, policy


class TransferTests(unittest.TestCase):
    def test_hand_counted_transfer_and_both_decompositions(self):
        docs, policy = example()
        result = evaluate_transfer(docs, policy=policy, target_recall=.5)
        self.assertEqual(result["selection"]["threshold"], .8)
        pop = result["populations"]
        self.assertEqual(pop["clear_test"]["operating_point"]["recall"]["value"], 1)
        target = pop["target_test"]
        self.assertEqual(target["operating_point"]["recall"]["value"], .25)
        self.assertEqual(target["candidate_ceiling"]["recall"]["value"], .75)
        self.assertEqual(target["operating_point"]["precision"]["value"], .5)
        self.assertEqual(target["operating_point"]["fppi"]["value"], .5)
        self.assertEqual(target["target_gaps"]["shortfall"]["value"], .25)
        self.assertEqual(target["target_gaps"]["threshold_removable_misses"]["value"], .5)
        self.assertEqual({k: v["value"] for k, v in result["held_out_loss"].items()},
                         {"held_out_loss": .75, "ceiling_difference": .25, "threshold_miss_difference": .5})
        self.assertEqual(result["g0_status"], "PENDING")
        # Changing held-out labels cannot alter source selection.
        changed = copy.deepcopy(docs)
        changed["target_test"][0]["annotations"] = []
        self.assertEqual(evaluate_transfer(changed, policy=policy, target_recall=.5)["selection"], result["selection"])

    def test_selection_failure_propagates_and_keeps_test_ceiling(self):
        docs, policy = example()
        docs["source_selection"][1]["predictions"] = []
        for expected in ("INFEASIBLE", "UNDEFINED"):
            result = evaluate_transfer(docs, policy=policy, target_recall=.9)
            self.assertEqual(result["selection"]["status"], expected)
            self.assertIsNone(result["populations"]["target_test"]["operating_point"])
            self.assertEqual(result["populations"]["target_test"]["candidate_ceiling"]["recall"]["value"], .75)
            self.assertEqual(result["held_out_loss"]["held_out_loss"]["status"], "UNDEFINED")
            json.dumps(result, allow_nan=False)
            docs["source_selection"][0]["annotations"] = []

    def test_reject_selection_image_and_group_overlap_even_diagnostic(self):
        docs, policy = example()
        for mode in ("held_out", "diagnostic"):
            policy["population_mode"] = mode
            # Same group, different images is still leakage.
            docs["clear_test"][0]["images"][0]["group_id"] = "source-trip"
            with self.assertRaisesRegex(ValueError, "group overlap"):
                evaluate_transfer(docs, policy=policy, target_recall=.5)
            docs["clear_test"][0]["images"][0]["group_id"] = "clear-trip"
            altered = copy.deepcopy(docs)
            altered["clear_test"] = altered["source_selection"]
            with self.assertRaisesRegex(ValueError, "image overlap"):
                evaluate_transfer(altered, policy=policy, target_recall=.5)

    def test_missing_group_provenance_never_claims_independence(self):
        docs, policy = example()
        docs["clear_test"][0]["images"][0]["group_id"] = None
        with self.assertRaisesRegex(ValueError, "complete group IDs"):
            evaluate_transfer(docs, policy=policy, target_recall=.5)
        policy["population_mode"] = "diagnostic"
        result = evaluate_transfer(docs, policy=policy, target_recall=.5)
        self.assertEqual(result["role_validation"]["status"], "DIAGNOSTIC")
        self.assertTrue(any("independence unverified" in s for s in result["role_validation"]["limitations"]))
        docs, policy = example()
        policy["roles"]["source_selection"]["group_provenance"] = None
        with self.assertRaises(ValueError):
            evaluate_transfer(docs, policy=policy, target_recall=.5)

    def test_paired_test_groups_allowed_only_when_explicit_and_never_selection(self):
        docs, policy = example()
        docs["target_test"][0]["images"][0]["group_id"] = "clear-trip"
        with self.assertRaisesRegex(ValueError, "group overlap"):
            evaluate_transfer(docs, policy=policy, target_recall=.5)
        policy["test_relationship"] = "paired"
        self.assertEqual(evaluate_transfer(docs, policy=policy, target_recall=.5)["selection"]["threshold"], .8)
        docs["target_test"][0]["images"][0]["group_id"] = "source-trip"
        with self.assertRaisesRegex(ValueError, "group overlap"):
            evaluate_transfer(docs, policy=policy, target_recall=.5)

    def test_explicit_population_filters_and_dataset_identity(self):
        docs, policy = example()
        policy["roles"]["source_selection"]["attribute_filter"] = {"weather": "clear", "timeofday": "daytime"}
        with self.assertRaisesRegex(ValueError, "attribute_filter"):
            evaluate_transfer(docs, policy=policy, target_recall=.5)
        docs["source_selection"][0]["images"][0]["attributes"] = {"weather": "clear", "timeofday": "daytime"}
        evaluate_transfer(docs, policy=policy, target_recall=.5)
        policy["roles"]["target_test"]["dataset_id"] = "different"
        with self.assertRaisesRegex(ValueError, "provenance.dataset"):
            evaluate_transfer(docs, policy=policy, target_recall=.5)

    def test_order_invariance_of_all_numeric_results(self):
        docs, policy = example()
        baseline = evaluate_transfer(docs, policy=policy, target_recall=.5)
        for anns, preds in docs.values():
            anns["images"].reverse()
            anns["annotations"].reverse()
            preds["predictions"].reverse()
        self.assertEqual(evaluate_transfer(docs, policy=policy, target_recall=.5), baseline)


class CliTests(unittest.TestCase):
    def test_real_module_cli_strict_output_provenance_and_rejection(self):
        docs, policy = example()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            command = [sys.executable, "-m", "threshold_transfer.evaluate", "--target-recall", ".5"]
            for role, pair in docs.items():
                for name, document in zip(("annotations", "predictions"), pair):
                    path = root / f"{role}-{name}.json"
                    path.write_text(json.dumps(document), encoding="utf-8")
                    command.extend([f"--{role.replace('_', '-')}-{name}", str(path)])
            policy_path = root / "policy.json"
            policy_path.write_text(json.dumps(policy), encoding="utf-8")
            command.extend(["--policy", str(policy_path)])
            process = subprocess.run(command, capture_output=True, text=True, env=os.environ.copy())
            self.assertEqual(process.returncode, 0, process.stderr)
            result = json.loads(process.stdout, parse_constant=lambda x: self.fail(f"nonfinite JSON {x}"))
            self.assertEqual(result["selection"]["threshold"], .8)
            self.assertEqual(result["input_provenance"]["target_test"]["predictions"], docs["target_test"][1]["provenance"])
            self.assertEqual(len(result["input_files"]["clear_test"]["annotations"]["sha256"]), 64)
            # Never overwrite the policy or another input with results.
            process = subprocess.run(command + ["--output", str(policy_path)], capture_output=True, text=True)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(json.loads(process.stderr)["status"], "ERROR")
            self.assertEqual(json.loads(policy_path.read_text()), policy)
            policy_path.write_text('{"categories": [], "categories": []}', encoding="utf-8")
            process = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(process.returncode, 2)
            self.assertIn("duplicate JSON key", json.loads(process.stderr)["error"])

    def test_strict_loader_rejects_nonfinite_json_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            for value in ('{"x": NaN}', '{"x": Infinity}', '{"x": 1e999}', '{"x":1,"x":2}'):
                path.write_text(value, encoding="utf-8")
                with self.subTest(value=value), self.assertRaises(ValueError):
                    load_json(path)


if __name__ == "__main__":
    unittest.main()
