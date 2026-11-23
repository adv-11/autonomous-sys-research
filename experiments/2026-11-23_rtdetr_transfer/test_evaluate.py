"""GPT Sol: CPU checks of the new native-candidate evaluator adapter only.

Synthetic geometry; these are not model/training results or qualifications.
"""
import unittest
import numpy as np

from evaluate import match, Population, choose_fppi, curve


class NativeAdapterTest(unittest.TestCase):
    def test_native_outside_box_and_zero_area_fp(self):
        gt = {'image': {'peds': [[0, 0, 10, 10]]}}
        predictions = {'image': (np.array([[-2, 0, 10, 10], [0, 0, 0, 10]], dtype=float),
                                  np.array([0.7, 0.9]))}
        recs, evaluator = match(['image'], gt, predictions)
        pop = Population([recs['image']])
        self.assertEqual(evaluator.select_threshold(0.8)['threshold'], 0.7)
        self.assertEqual(pop.point(0.8)['tp'], 0)
        self.assertEqual(pop.point(0.8)['fp'], 1)
        self.assertEqual(pop.point(0.7)['recall'], 1)
        self.assertEqual(pop.point(0.7)['fp'], 1)

    def test_whole_score_ties_cannot_meet_fp_budget(self):
        gt = {'image': {'peds': [[0, 0, 10, 10]]}}
        predictions = {'image': (np.array([[0, 0, 10, 10], [20, 20, 30, 30], [40, 40, 50, 50]], dtype=float),
                                  np.array([0.8, 0.8, 0.8]))}
        recs, _ = match(['image'], gt, predictions)
        pop = Population([recs['image']])
        self.assertEqual(pop.select(0.8), 0.8)
        self.assertEqual(pop.point(0.8)['fppi'], 2)
        self.assertIsNone(choose_fppi(pop))

    def test_no_pedestrian_candidates_is_explicitly_infeasible(self):
        gt = {'image': {'peds': [[0, 0, 10, 10]]}}
        recs, _ = match(['image'], gt, {'image': (np.zeros((0, 4)), np.zeros(0))})
        pop = Population([recs['image']])
        self.assertIsNone(pop.select(0.8))
        self.assertIsNone(choose_fppi(pop))
        self.assertEqual(pop.point(None)['recall'], 0)
        self.assertEqual(len(curve(pop)['fppi']), 0)


if __name__ == '__main__':
    unittest.main()
