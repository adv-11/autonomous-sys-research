"""Synthetic tests for threshold_transfer.candidate_pilot (Claude; no detector, no GPU).

The nesting tests re-implement the pinned selectors in plain Python (Ultralytics 8.4.197
``Detect.get_topk_index`` two-stage top-k and class-aware greedy hard NMS; RT-DETRv2 flattened
top-k) and check, on random inputs with distinct scores, that lower floor/cap settings are
filtered prefixes of a permissive capture. Counterexamples show where derivation is invalid.
"""

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from threshold_transfer import candidate_pilot as P


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def ultralytics_o2m(anchors, floor, cap, iou_thr=0.7):
    """Single-label anchors -> strict floor -> class-aware greedy hard NMS -> [:cap]."""
    cands = []
    for a, (box, scores) in enumerate(anchors):
        c = max(range(len(scores)), key=lambda k: (scores[k], -k))
        if scores[c] > floor:
            cands.append({"id": f"a{a}:c{c}", "score": scores[c], "cls": c, "box": box})
    cands.sort(key=lambda r: -r["score"])
    kept = []
    for r in cands:
        if all(k["cls"] != r["cls"] or iou(k["box"], r["box"]) <= iou_thr for k in kept):
            kept.append(r)
    return kept[:cap]


def ultralytics_o2o(scores, floor, cap):
    """Two-stage head top-k with hidden k = max(cap, 300) (capped by anchors), then floor and cap."""
    k = min(max(cap, 300), len(scores))
    top_anchors = sorted(range(len(scores)), key=lambda a: -max(scores[a]))[:k]
    pairs = sorted(((scores[a][c], a, c) for a in top_anchors for c in range(len(scores[a]))), reverse=True)[:k]
    rows = [{"id": f"a{a}:c{c}", "score": s} for s, a, c in pairs]
    return [r for r in rows if r["score"] > floor][:cap]


def rtdetr(scores, cap, floor):
    flat = sorted(((s, q, c) for q, row in enumerate(scores) for c, s in enumerate(row)), reverse=True)[:cap]
    return [{"id": f"q{q}:c{c}", "score": s} for s, q, c in flat if s >= floor]


def random_anchors(rng, n, nc=3):
    out = []
    for _ in range(n):
        x, y = rng.uniform(0, 100), rng.uniform(0, 100)
        w, h = rng.uniform(5, 30), rng.uniform(5, 30)
        out.append(((x, y, x + w, y + h), [rng.random() for _ in range(nc)]))
    return out


GRID = [(f, c) for f in (1e-4, 1e-3, 1e-2, 0.3) for c in (1, 5, 20, 100)]


class NestingTests(unittest.TestCase):
    def test_o2m_floor_and_cap_are_filtered_prefixes_of_capture(self):
        rng = random.Random(0)
        for _ in range(30):
            anchors = random_anchors(rng, 120)
            capture = ultralytics_o2m(anchors, 1e-4, 3000)
            for f, c in GRID:
                self.assertEqual([r["id"] for r in P.derive(capture, floor=f, cap=c, comparator=">")],
                                 [r["id"] for r in ultralytics_o2m(anchors, f, c)])

    def test_o2o_two_stage_topk_equals_global_topk_prefix(self):
        rng = random.Random(1)
        for _ in range(20):
            scores = [[rng.random() for _ in range(4)] for _ in range(700)]
            capture = ultralytics_o2o(scores, 1e-4, 3000)
            self.assertEqual(len(capture), 700)  # hidden k is capped by the anchor count
            for f, c in GRID + [(1e-4, 400)]:
                self.assertEqual([r["id"] for r in P.derive(capture, floor=f, cap=c, comparator=">")],
                                 [r["id"] for r in ultralytics_o2o(scores, f, c)])

    def test_rtdetr_topk_prefix_with_inclusive_export_floor(self):
        rng = random.Random(2)
        scores = [[rng.random() for _ in range(5)] for _ in range(60)]
        capture = rtdetr(scores, 3000, 1e-4)
        for f, c in GRID:
            self.assertEqual([r["id"] for r in P.derive(capture, floor=f, cap=c, comparator=">=")],
                             [r["id"] for r in rtdetr(scores, c, f)])

    def test_changed_nms_iou_is_not_derivable(self):
        anchors = [((0, 0, 10, 10), [0.9]), ((1, 0, 11, 10), [0.8])]  # IoU 9/11 ~ 0.82
        capture = ultralytics_o2m(anchors, 1e-4, 3000, iou_thr=0.7)
        self.assertEqual(len(capture), 1)
        self.assertEqual(len(ultralytics_o2m(anchors, 1e-4, 3000, iou_thr=0.9)), 2)

    def test_nms_suppression_hides_high_score_behind_higher_one(self):
        # A post-NMS kth score cannot bound pre-NMS omitted scores: 0.85 is gone behind 0.9.
        anchors = [((0, 0, 10, 10), [0.9]), ((0, 0, 10, 10.5), [0.85]), ((50, 50, 60, 60), [0.2])]
        kept = ultralytics_o2m(anchors, 1e-4, 3000)
        self.assertEqual([r["score"] for r in kept], [0.9, 0.2])


class PolicyTests(unittest.TestCase):
    rows = [{"id": "a", "score": 0.9, "box": (0, 0, 1, 1)}, {"id": "b", "score": 0.5, "box": (0, 0, 1, 1)},
            {"id": "c", "score": 0.5, "box": (0, 0, 1, 1)}, {"id": "d", "score": 0.01, "box": (0, 0, 1, 1)}]

    def test_strict_vs_inclusive_floor_at_equality(self):
        self.assertEqual([r["id"] for r in P.derive(self.rows, floor=0.01, cap=10, comparator=">")], ["a", "b", "c"])
        self.assertEqual(len(P.derive(self.rows, floor=0.01, cap=10, comparator=">=")), 4)

    def test_derive_rejects_unsorted_or_duplicate_ids(self):
        with self.assertRaises(ValueError):
            P.derive(list(reversed(self.rows)), floor=0, cap=2, comparator=">")
        with self.assertRaises(ValueError):
            P.derive(self.rows + [dict(self.rows[-1], score=0.0)], floor=0, cap=2, comparator=">")

    def test_boundary_reports_tie_at_cut(self):
        b = P.boundary(self.rows, floor=1e-4, cap=2, comparator=">")
        self.assertTrue(b["cap_binding"])
        self.assertTrue(b["tie_at_cap_boundary"])
        self.assertEqual(b["first_omitted_score"], 0.5)
        self.assertFalse(P.boundary(self.rows, floor=1e-4, cap=3, comparator=">")["tie_at_cap_boundary"])
        self.assertEqual(P.boundary(self.rows, floor=1e-4, cap=3, comparator=">")["duplicate_scores_kept"], 1)

    def test_class_first_differs_from_all_class_global_cap(self):
        # GPT counterexample: car .9, person .8, k = 1.
        capture = [{"id": "a0:car", "score": 0.9, "cls": "car"}, {"id": "a1:person", "score": 0.8, "cls": "person"}]
        all_class = [r for r in P.derive(capture, floor=1e-4, cap=1, comparator=">") if r["cls"] == "person"]
        person_first = P.class_first([capture[1]], floor=1e-4, cap=1, comparator=">")
        self.assertEqual(all_class, [])
        self.assertEqual([r["id"] for r in person_first], ["a1:person"])

    def test_geometry_counts_clip_and_collapse(self):
        g = P.geometry([(-5, 0, 10, 10), (0, 0, 10, 10), (120, 5, 130, 9), (0, 0, 100, 50)], 100, 50)
        self.assertEqual(g, {"changed_by_clip": 2, "collapsed_after_clip": 1})

    def test_compare_reports_identity_and_numeric_differences(self):
        native = [dict(r, score=r["score"] + 1e-7) for r in self.rows[:2]]
        out = P.compare(self.rows[:2], native, score_tol=1e-6)
        self.assertTrue(out["identical_identities"] and out["within_tolerance"])
        self.assertFalse(P.compare(self.rows[:2], [self.rows[1], self.rows[0]])["identical_identities"])

    def test_select_images_order_independent_and_seeded(self):
        names = [f"{i:06d}.png" for i in range(200)]
        a = P.select_images(names, seed="s", count=32)
        self.assertEqual(a, P.select_images(list(reversed(names)), seed="s", count=32))
        self.assertNotEqual(a, P.select_images(names, seed="t", count=32))
        self.assertEqual(len(set(a)), 32)


class CompletenessTests(unittest.TestCase):
    def test_complete_when_every_stage_bound_is_below_threshold(self):
        stages = [{"name": "head_topk", "bound": 0.004, "exact": True}, {"name": "floor", "bound": 1e-4}]
        self.assertEqual(P.stage_status(0.01, stages)["status"], "COMPLETE_RELATIVE_TO_POOL")

    def test_threshold_equal_to_strict_floor_is_unknown(self):
        # conf > f drops items exactly f, which s >= t = f would include.
        self.assertEqual(P.stage_status(1e-3, [{"name": "floor", "bound": 1e-3, "inclusive": True}])["status"],
                         "UNKNOWN")
        self.assertEqual(P.stage_status(1e-3, [{"name": "floor", "bound": 1e-3, "inclusive": False}])["status"],
                         "COMPLETE_RELATIVE_TO_POOL")

    def test_exact_omitted_score_at_threshold_is_incomplete(self):
        self.assertEqual(P.stage_status(0.3, [{"name": "cap", "bound": 0.31, "exact": True}])["status"], "INCOMPLETE")

    def test_unknown_stage_or_unattained_bound_is_unknown(self):
        self.assertEqual(P.stage_status(0.5, [{"name": "timeout", "bound": None}])["status"], "UNKNOWN")
        self.assertEqual(P.stage_status(0.5, [{"name": "post_nms_kth", "bound": 0.6, "exact": False}])["status"],
                         "UNKNOWN")
        self.assertEqual(P.stage_status(0.5, [{"name": "cap", "bound": None, "omitted_count": 0}])["status"],
                         "COMPLETE_RELATIVE_TO_POOL")


if __name__ == "__main__":
    unittest.main()
