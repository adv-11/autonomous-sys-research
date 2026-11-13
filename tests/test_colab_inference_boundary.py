"""CPU checks for the publication safeguards; never import GPU libraries."""
import builtins
import copy
import importlib.util
import os
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import patch

EXPERIMENTS = Path(__file__).resolve().parents[1] / "experiments"


def load(name):
    spec = importlib.util.spec_from_file_location(name, EXPERIMENTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ColabInferenceBoundaryTests(unittest.TestCase):
    def test_all_inference_entries_refuse_before_gpu_import(self):
        original_import = builtins.__import__

        def cpu_import(name, *args, **kwargs):
            if name.split(".")[0] in {"torch", "ultralytics", "cv2"}:
                self.fail("GPU dependency imported before Colab refusal: " + name)
            return original_import(name, *args, **kwargs)

        entries = [
            ("2026-11-10_transfer_pilot", ("unused", "yolo11s")),
            ("2026-11-11_information_control", ("unused",)),
            ("2026-11-11_dual_head_transfer", ("unused",)),
            ("2026-11-13_head_policy_mechanism", ("unused",)),
        ]
        with patch.dict(os.environ, {}, clear=True), patch("builtins.__import__", side_effect=cpu_import):
            for name, args in entries:
                with self.subTest(entry=name):
                    module = load(name)
                    with self.assertRaisesRegex(RuntimeError, "Colab-only inference"):
                        module.infer(*args)
            path = EXPERIMENTS / "2026-11-10_resolution_probe.py"
            with patch.object(sys, "argv", [str(path), "infer", "unused"]):
                with self.assertRaisesRegex(RuntimeError, "Colab-only inference"):
                    runpy.run_path(str(path), run_name="__main__")

    def test_incomplete_runtime_markers_fail_closed(self):
        module = load("2026-11-10_transfer_pilot")
        for content, release in [(False, "tag"), (True, "")]:
            with self.subTest(content=content, release=release):
                with patch.object(module.sys, "platform", "linux"), patch.object(module.Path, "is_dir", return_value=content):
                    with patch.dict(os.environ, {"COLAB_RELEASE_TAG": release}, clear=True):
                        with self.assertRaisesRegex(RuntimeError, "Colab-only inference"):
                            module.require_colab()

    def test_public_status_replaces_identity_events_with_counts(self):
        module = load("2026-11-11_information_control")
        status = {"status": "COMPLETE", "coverage": {"H1280": 700},
                  "effective_runtime": {"args": {"conf": .0001, "source": "private-image-id"}}, "events": [
            {"arm": "H1280", "kind": "cap3000", "image_id": "private-A"},
            {"arm": "U1280", "kind": "cap3000", "image_id": "private-B"},
            {"arm": "L640", "message": "private filename time-limit event"},
        ]}
        before = copy.deepcopy(status)
        result = module.public_runtime_status(status)
        self.assertEqual(result["cap3000_events_by_arm"], {"H1280": 1, "L640": 0, "U1280": 1})
        self.assertEqual(result["native_time_limit_events"], 1)
        self.assertEqual(result["coverage"], status["coverage"])
        self.assertNotIn("events", result)
        self.assertNotIn("private", repr(result))
        self.assertEqual(status, before)


if __name__ == "__main__":
    unittest.main()
