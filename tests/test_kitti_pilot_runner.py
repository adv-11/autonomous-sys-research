"""CPU integration tests for scripts/pilot/kitti_pilot.py (Claude; synthetic captures, no GPU).

These exercise the summarize path and the GPU preflight refusal. The GPU capture functions
themselves have not been executed (GPU occupied by an unrelated user job on 2026-11-09).
"""

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("kitti_pilot", ROOT / "scripts/pilot/kitti_pilot.py")
K = importlib.util.module_from_spec(spec)
spec.loader.exec_module(K)

PILOT = {"sensitivity_floors": [1e-4, 1e-2], "sensitivity_caps": [1, 3], "person_class": "person"}


def row(i, score, cls="person", box=(0, 0, 10, 10), unclipped=None):
    r = {"id": i, "score": score, "cls": cls, "box": list(box)}
    if unclipped is not None:
        r["box_unclipped"] = list(unclipped)
    return r


def capture(status="PASS", identical=1):
    img = {"file": "x.png", "width": 100, "height": 50,
           "rows": [row("a1:c2", 0.9, "car"), row("a2:c0", 0.8, box=(0, 0, 10, 10), unclipped=(-4, 0, 10, 10)),
                    row("a3:c0", 0.005, box=(95, 0, 100, 10)), row("a4:c2", 0.005, "car")],
           "person_pool": [{"id": "a2:c0", "score": 0.8}, {"id": "a3:c0", "score": 0.005},
                           {"id": "a9:c0", "score": 0.004}],
           "stages": {"post_nms_cap": {"bound": None, "omitted_count": 0}, "floor": {"bound": 1e-4}}}
    return {"pipeline": "yolo11s", "status": status, "comparator": ">", "images": [img],
            "checks": [{"policy": {}, "images": 1, "identical_identities": identical, "within_tolerance": identical,
                        "max_abs_score_diff": 0.0, "max_abs_box_diff": 0.0}]}


class SummarizeTests(unittest.TestCase):
    def test_grid_counts_on_synthetic_capture(self):
        # Arithmetic of the retained prototype only; never native runtime approval.
        _, out = K._summarize_capture_prototype(capture(), PILOT)
        self.assertTrue(out["derivation_supported"])
        c1 = out["grid"]["floor=0.0001,cap=1"]
        self.assertEqual(c1["mean_kept"], 1)
        self.assertEqual(c1["mean_person_all_class_first"], 0)  # the car takes the only slot
        self.assertEqual(c1["mean_person_class_first_pipeline"], 1)
        self.assertEqual(c1["person_removed_by_cap_vs_capture"], 2)
        self.assertEqual(c1["images_cap_binding"], 1)
        c3 = out["grid"]["floor=0.0001,cap=3"]
        self.assertEqual(c3["images_tie_at_cap"], 1)  # 0.005 vs 0.005 at the cut
        self.assertEqual(c3["native_boxes_outside_image_before_native_clip"], 1)
        hi = out["grid"]["floor=0.01,cap=3"]
        self.assertEqual(hi["mean_kept"], 2)
        self.assertEqual(hi["images_cap_binding"], 0)

    def test_grid_withheld_without_exact_native_check(self):
        _, out = K.summarize_capture(capture(identical=0), PILOT)
        self.assertFalse(out["derivation_supported"])
        self.assertTrue(out["grid"].startswith("UNSUPPORTED"))
        _, failed = K.summarize_capture(capture(status="FAIL"), PILOT)
        self.assertTrue(failed["grid"].startswith("UNSUPPORTED"))


class GeometryAndPreflightTests(unittest.TestCase):
    def test_unletterbox_inverts_kitti_letterbox_without_clipping(self):
        h0, w0 = 375, 1242
        shape = (224, 640)  # auto=True minimal stride-32 padding of 193 x 640
        gain = 640 / 1242
        new_h = round(h0 * gain)
        py = round((shape[0] - new_h) / 2 - 0.1)
        box = (-10.0, -5.0, 1250.0, 380.0)  # extends outside the original image
        lb = [(box[0] * 640 / w0, box[1] * new_h / h0 + py, box[2] * 640 / w0, box[3] * new_h / h0 + py)]
        (back,) = K._unletterbox(lb, shape, (h0, w0))
        for a, b in zip(back, box):
            self.assertAlmostEqual(a, b, places=6)

    TABLE = (
        "| Processes: GPU GI CI PID Type Process name GPU Memory |\n"
        r"|    0   N/A  N/A            4101    C+G   C:\synthetic\desktop.exe             N/A      |" "\n"
        r"|    0   N/A  N/A            4202      C   C:\synthetic\worker.exe              N/A      |" "\n")

    def test_combined_compute_is_not_assumed_desktop_only(self):
        self.assertEqual(K.compute_processes(self.TABLE),
                         [r"4101 C:\synthetic\desktop.exe", r"4202 C:\synthetic\worker.exe"])

    def test_preflight_refuses_when_another_compute_process_exists(self):
        with mock.patch.object(K.subprocess, "run", return_value=mock.Mock(stdout=self.TABLE)):
            with self.assertRaises(SystemExit) as ctx:
                K.gpu_preflight(7.5)
        self.assertIn("BLOCKED", str(ctx.exception))
        for text in ('', 'unrecognized output', self.TABLE.splitlines()[0],
                     self.TABLE.splitlines()[0] + '\n' + self.TABLE.splitlines()[1]):
            with self.subTest(text=text), mock.patch.object(K.subprocess, "run", return_value=mock.Mock(stdout=text)):
                with self.assertRaises(SystemExit):
                    K.gpu_preflight(7.5)
        idle = self.TABLE.splitlines()[0] + '\n| No running processes found |'
        with mock.patch.object(K.subprocess, "run", return_value=mock.Mock(stdout=idle)):
            self.assertEqual(K.gpu_preflight(7.5)["other_compute_processes"], 0)

if __name__ == "__main__":
    unittest.main()
