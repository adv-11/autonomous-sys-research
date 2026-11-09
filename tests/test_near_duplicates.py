"""Synthetic tests for threshold_transfer.near_duplicates (Claude; no ACDC data)."""

import json
import math
import random
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from threshold_transfer import near_duplicates as nd


def brute_dct(x):
    n = x.shape[0]
    out = np.zeros_like(x, dtype=float)
    for u in range(n):
        for v in range(n):
            cu = math.sqrt(1 / n) if u == 0 else math.sqrt(2 / n)
            cv = math.sqrt(1 / n) if v == 0 else math.sqrt(2 / n)
            s = sum(x[i, j] * math.cos(math.pi * (2 * i + 1) * u / (2 * n)) * math.cos(math.pi * (2 * j + 1) * v / (2 * n))
                    for i in range(n) for j in range(n))
            out[u, v] = cu * cv * s
    return out


def rec(path, comp, cond, phash, dhash=0):
    return {"path": path, "component": comp, "condition": cond, "phash": phash, "dhash": dhash}


class HashTests(unittest.TestCase):
    def test_dct_matrix_orthonormal_and_matches_definition(self):
        d = nd._dct_matrix(8)
        self.assertTrue(np.allclose(d @ d.T, np.eye(8)))
        x = np.random.default_rng(0).random((8, 8))
        self.assertTrue(np.allclose(d @ x @ d.T, brute_dct(x)))

    def test_phash_invariant_to_positive_contrast_scaling(self):
        x = np.random.default_rng(1).random((32, 32)) * 255
        self.assertEqual(nd.phash_bits(x), nd.phash_bits(0.5 * x))
        self.assertEqual(bin(nd.phash_bits(x)).count("1"), 32)  # median split, no ties

    def test_phash_rejects_wrong_shape(self):
        with self.assertRaises(ValueError):
            nd.phash_bits(np.zeros((16, 16)))

    def test_dhash_bit_order(self):
        g = np.zeros((8, 9))
        g[0, 1] = 1.0  # first row: pixel 1 brighter than pixel 0 -> MSB set; pixel 2 darker than 1
        self.assertEqual(nd.dhash_bits(g), 1 << 63)

    def test_pairwise_hamming_matches_brute_force(self):
        rng = random.Random(2)
        hashes = [rng.getrandbits(64) for _ in range(40)] + [0, 1, 3]
        got = nd.pairwise_hamming(hashes, 30)
        want = [(i, j, nd.hamming(hashes[i], hashes[j])) for i in range(len(hashes))
                for j in range(i + 1, len(hashes)) if nd.hamming(hashes[i], hashes[j]) <= 30]
        self.assertEqual(got, want)

    def test_distance_histogram_partitions_all_pairs(self):
        rng = random.Random(3)
        hashes = [rng.getrandbits(64) for _ in range(20)]
        labels = [(f"c{i % 4}", "fog" if i % 4 < 2 else "snow") for i in range(20)]
        hist = nd.distance_histogram(hashes, labels)
        self.assertEqual(sum(sum(v) for v in hist.values()), 20 * 19 // 2)
        within = sum(1 for i in range(20) for j in range(i + 1, 20) if labels[i][0] == labels[j][0])
        cross_cond = sum(1 for i in range(20) for j in range(i + 1, 20)
                         if labels[i][0] != labels[j][0] and labels[i][1] != labels[j][1])
        self.assertEqual(sum(hist["within_component"]), within)
        self.assertEqual(sum(hist["cross_condition"]), cross_cond)


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.records = [rec("a1", "A", "fog", 0b0), rec("a2", "A", "snow", 0b1),  # A spans two conditions
                        rec("b1", "B", "snow", 0b11), rec("c1", "C", "fog", 0b111),
                        rec("c2", "C", "fog", 0b1), rec("d1", "D", "night", 0xFFFF)]

    def test_categories_treat_multi_condition_component_as_within(self):
        cats = {(p["a"], p["b"]): p["category"] for p in nd.flagged_pairs(self.records, 4)}
        self.assertEqual(cats[("a1", "a2")], "within_component")
        self.assertEqual(cats[("a1", "c2")], "cross_component_same_condition")
        self.assertEqual(cats[("a2", "c2")], "cross_condition")
        self.assertEqual(cats[("a2", "b1")], "cross_component_same_condition")
        self.assertEqual(cats[("b1", "c1")], "cross_condition")

    def test_queue_one_closest_representative_per_component_pair_cross_condition_first(self):
        pairs = nd.flagged_pairs(self.records, 4)
        queue, remaining = nd.review_queue(pairs, 2)
        keys = [p["components"] for p in queue + remaining]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertNotIn(("A", "A"), keys)
        self.assertEqual(queue[0]["category"], "cross_condition")
        ac = next(p for p in queue + remaining if p["components"] == ("A", "C"))
        self.assertEqual(ac["phash_distance"], 0)  # a2 vs c2 are identical hashes
        self.assertEqual(ac["image_pairs_in_component_pair"], 4)
        self.assertEqual(len(queue), 2)

    def test_summarize_flags_accepts_json_round_trip(self):
        pairs = json.loads(json.dumps(nd.flagged_pairs(self.records, 4)))
        out = nd.summarize_flags(pairs, [0, 4])
        self.assertEqual(out["4"]["distinct_cross_component_pairs"],
                         len({tuple(p["components"]) for p in pairs if p["category"] != "within_component"}))


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.comp = {"x1": "X", "x2": "X", "y1": "Y", "z1": "Z", "w1": "W"}
        self.cond = {"x1": "night", "x2": "snow", "y1": "night", "z1": "rain", "w1": "rain"}

    def test_sensitivity_counts_without_mutating_input(self):
        before = dict(self.comp)
        out = nd.component_sensitivity(self.comp, self.cond, ["x1", "y1", "z1"], [("X", "Y"), ("Y", "X")])
        self.assertEqual(self.comp, before)
        self.assertEqual(out["components"], 3)
        self.assertEqual(out["merges_applied"], 1)
        self.assertEqual(out["labelled_adverse_components_by_condition"]["night"], 1)

    def test_closure_ids_content_addressed_and_order_independent(self):
        a = nd.closure_ids(self.comp, [("X", "Y")], "p")
        b = nd.closure_ids(dict(reversed(list(self.comp.items()))), [("Y", "X")], "p")
        self.assertEqual(a, b)
        self.assertEqual(a["x1"], a["y1"])
        self.assertNotEqual(a["z1"], a["w1"])
        self.assertTrue(a["x1"].startswith("p:"))

    def test_exclusion_removes_whole_linked_closure(self):
        # X is descriptive-only; a confirmed link X-Y removes Y's labelled image as well.
        ids = nd.closure_ids(self.comp, [("X", "Y")], "p")
        out = nd.closure_support(ids, self.cond, ["x1", "y1", "z1", "w1"], ["x1"])
        self.assertEqual(out["labelled_adverse_images_excluded"], 2)
        self.assertEqual(out["by_condition"]["night"]["eligible_labelled_adverse_images"], 0)
        self.assertEqual(out["by_condition"]["rain"]["eligible_closures_with_labelled_adverse"], 2)
        base = nd.closure_support(nd.closure_ids(self.comp, [], "p"), self.cond, ["x1", "y1", "z1", "w1"], ["x1"])
        self.assertEqual(base["by_condition"]["night"]["eligible_labelled_adverse_images"], 1)


if __name__ == "__main__":
    unittest.main()
