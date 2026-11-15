"""Claude Opus: split/label-conversion checks for experiments/2026-11-15_bdd_clearday_transfer.

Synthetic legacy-style objects only; these guard logic that could invalidate the
result (class mapping, YOLO geometry, selection holdout, stratum assignment).
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "bdd_common", ROOT / "experiments/2026-11-15_bdd_clearday_transfer/common.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def obj(cat, x1=10, y1=20, x2=50, y2=120):
    return {"category": cat, "box2d": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}}


class ConversionTests(unittest.TestCase):
    def test_pedestrian_and_rider_stay_separate_and_lane_dropped(self):
        boxes, drops = C.convert_objects([obj("person"), obj("rider"), obj("motor"), obj("bike"),
                                          {"category": "lane/crosswalk", "poly2d": []},
                                          {"category": "area/drivable", "poly2d": []}])
        self.assertEqual([b[0] for b in boxes], [0, 1, 6, 7])
        self.assertEqual(C.CLASSES[0], "pedestrian")
        self.assertEqual(drops["dropped_category"], 2)

    def test_all_ten_legacy_categories_map(self):
        self.assertEqual(sorted(C.LEGACY_TO_CLASS.values()), sorted(C.CLASSES))

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            C.convert_objects([obj("dog")])

    def test_nonpositive_dropped_and_out_of_bounds_rejected(self):
        boxes, drops = C.convert_objects([obj("car", 10, 10, 10, 30)])
        self.assertEqual((boxes, drops["nonpositive"]), ([], 1))
        with self.assertRaises(ValueError):
            C.convert_objects([obj("car", -1, 0, 10, 10)])

    def test_yolo_geometry_round_trips(self):
        line = C.yolo_lines([(0, 100.0, 200.0, 300.0, 600.0)]).split()
        c, xc, yc, w, h = int(line[0]), *map(float, line[1:])
        self.assertEqual(c, 0)
        self.assertAlmostEqual((xc - w / 2) * 1280, 100.0, places=3)
        self.assertAlmostEqual((yc + h / 2) * 720, 600.0, places=3)
        self.assertEqual(C.yolo_lines([]), "")


class SplitTests(unittest.TestCase):
    def test_selection_is_deterministic_and_about_fifteen_percent(self):
        names = [f"{i:08x}-{i * 7919 % 99991:08x}" for i in range(20000)]
        roles = [C.source_role(n) for n in names]
        self.assertEqual(roles, [C.source_role(n) for n in names])
        frac = roles.count("selection") / len(roles)
        self.assertTrue(0.14 < frac < 0.16, frac)

    def test_source_requires_clear_and_daytime(self):
        self.assertTrue(C.is_source({"weather": "clear", "timeofday": "daytime"}))
        for a in ({"weather": "clear", "timeofday": "night"},
                  {"weather": "overcast", "timeofday": "daytime"}, {"weather": "clear"}):
            self.assertFalse(C.is_source(a))

    def test_primary_strata(self):
        cases = {("clear", "daytime"): "clear_day", ("rainy", "night"): "night",
                 ("snowy", "dawn/dusk"): "dawn_dusk", ("foggy", "daytime"): "foggy",
                 ("overcast", "daytime"): "cloudy_day", ("partly cloudy", "daytime"): "cloudy_day",
                 ("rainy", "daytime"): "rainy_day", ("snowy", "daytime"): "snowy_day",
                 ("undefined", "daytime"): "undefined", ("clear", "undefined"): "undefined"}
        for (w, t), want in cases.items():
            self.assertEqual(C.primary_stratum({"weather": w, "timeofday": t}), want, (w, t))
        self.assertEqual(C.secondary_strata({"weather": "rainy", "timeofday": "night"}),
                         ["night_rain_snow", "rainy_all"])

    def test_height_bins(self):
        self.assertEqual(C.height_bin(0), "0-16")
        self.assertEqual(C.height_bin(31.9), "16-32")
        self.assertEqual(C.height_bin(128), ">=128")


if __name__ == "__main__":
    unittest.main()
