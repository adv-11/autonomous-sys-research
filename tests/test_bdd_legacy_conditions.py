"""GPT synthetic tests of the inspected legacy schema, not publisher validation."""

import copy
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from threshold_transfer.bdd_legacy_conditions import inspect_legacy_zip, SOURCE_KIND
from threshold_transfer.data import PreflightError


def document(name="a"):
    return {"name": name, "attributes": {"weather": "clear", "timeofday": "daytime"},
            "frames": [{"timestamp": 10000, "objects": [
                {"id": 1, "category": "person", "attributes": {"occluded": True},
                 "box2d": {"x1": 1, "y1": 2, "x2": 4, "y2": 8}},
                {"id": 2, "category": "lane/single white", "attributes": {}, "poly2d": []}]}]}


class LegacyConditionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "candidate.zip"

    def make_zip(self, docs=None, raw=None, member="100k/train/a.json"):
        with zipfile.ZipFile(self.path, "w", compression=zipfile.ZIP_STORED) as z:
            if raw is not None:
                entry = zipfile.ZipInfo()
                entry.filename = member  # Avoid Windows ZipInfo path normalization in this attack fixture.
                z.writestr(entry, raw)
            else:
                for name, doc in (docs or [(member, document())]):
                    z.writestr(name, json.dumps(doc))
        return self.path

    def inspect(self, **kwargs):
        return inspect_legacy_zip(self.path, source_kind=SOURCE_KIND, **kwargs)

    def test_preserves_empty_unknown_conditions_and_never_emits_gt(self):
        empty = document("empty")
        empty["attributes"] = {"weather": "native-unknown-value"}
        empty["frames"][0]["objects"] = []
        self.make_zip([("100k/train/a.json", document()), ("100k/val/empty.json", empty)])
        result = self.inspect(include_index=True)
        p = result["provenance"]
        self.assertNotIn("schema_version", result)
        self.assertNotIn("annotations", result)
        self.assertNotIn("images", result)
        self.assertFalse(p["archive"]["official_md5_match"])
        self.assertFalse(p["official_evaluator_equivalent"])
        self.assertEqual(p["summary"]["images"], 2)
        self.assertEqual(p["summary"]["splits"]["train"]["box_category:person"], 1)
        self.assertNotIn("box_category:pedestrian", p["summary"]["splits"]["train"])
        self.assertEqual(p["summary"]["splits"]["val"]["zero_box_images"], 1)
        self.assertEqual(p["summary"]["splits"]["val"]["missing_condition:timeofday"], 1)
        self.assertEqual(result["condition_index"][1]["attributes"], empty["attributes"])
        self.assertTrue(all(r["group_id"] is None for r in result["condition_index"]))

    def test_source_kind_required_and_2020_claim_rejected(self):
        self.make_zip()
        with self.assertRaises(TypeError):
            inspect_legacy_zip(self.path)
        with self.assertRaises(PreflightError):
            inspect_legacy_zip(self.path, source_kind="detection2020")

    def test_geometry_inventory_does_not_repair_or_drop(self):
        doc = document()
        doc["frames"][0]["objects"][0]["box2d"].update(x2=1, y1=-1)
        self.make_zip(docs=[("100k/train/a.json", doc)])
        c = self.inspect()["provenance"]["summary"]["splits"]["train"]
        self.assertEqual((c["boxes"], c["nonpositive_boxes"], c["outside_nominal_1280x720"]), (1, 1, 1))

    def test_duplicate_names_ids_and_revised_schema_fail(self):
        variants = []
        d = document(); d["frames"][0]["objects"][1]["id"] = "1"; variants.append(d)
        d = document(); d["name"] = "wrong"; variants.append(d)
        d = document(); d["frames"].append(copy.deepcopy(d["frames"][0])); variants.append(d)
        d = document(); d["frames"][0]["timestamp"] = True; variants.append(d)
        d = document(); d["frames"][0]["objects"][0]["box2d"]["x1"] = True; variants.append(d)
        variants.append({"name": "a.jpg", "attributes": {}, "labels": []})
        for d in variants:
            with self.subTest(d=d):
                self.make_zip(docs=[("100k/train/a.json", d)])
                with self.assertRaises(PreflightError): self.inspect()
        self.make_zip([("100k/train/a.json", document()), ("100k/val/a.json", document())])
        with self.assertRaisesRegex(PreflightError, "duplicate name"): self.inspect()

    def test_unsafe_unexpected_duplicate_and_symlink_members_fail(self):
        for name in ["../a.json", "/100k/train/a.json", "C:/a.json", "100k\\train\\a.json", "100k/other/a.json", "a.jpg"]:
            with self.subTest(name=name):
                self.make_zip(raw=json.dumps(document()), member=name)
                with self.assertRaises(PreflightError): self.inspect()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self.make_zip([("100k/train/a.json", document()), ("100k/train/a.json", document())])
        with self.assertRaisesRegex(PreflightError, "duplicate or unsafe"): self.inspect()
        with zipfile.ZipFile(self.path, "w") as z:
            entry = zipfile.ZipInfo("100k/train/a.json")
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
            z.writestr(entry, "target")
        with self.assertRaisesRegex(PreflightError, "unsafe"): self.inspect()

    def test_duplicate_json_keys_nonfinite_and_crc_failure(self):
        for raw in ['{"name":"a","name":"b"}', json.dumps(document()).replace('"x1": 1', '"x1": NaN'),
                    json.dumps(document()).replace('"x1": 1', '"x1": 1e9999')]:
            self.make_zip(raw=raw)
            with self.assertRaises(PreflightError): self.inspect()
        self.make_zip()
        b = bytearray(self.path.read_bytes())
        offset = b.find(b'{"name"')
        b[offset] = ord('[')
        self.path.write_bytes(b)
        with self.assertRaises(zipfile.BadZipFile): self.inspect()

    def test_member_digest_stable_for_reordered_archive(self):
        docs = [("100k/train/a.json", document()), ("100k/val/b.json", document("b"))]
        self.make_zip(docs)
        first = self.inspect()["provenance"]
        self.make_zip(list(reversed(docs)))
        second = self.inspect()["provenance"]
        self.assertEqual(first["source_member_digest_sha256"], second["source_member_digest_sha256"])
        self.assertNotEqual(first["archive"]["sha256"], second["archive"]["sha256"])

    def test_cli_and_input_protection(self):
        self.make_zip()
        code = Path(__file__).resolve().parents[1] / "src"
        launch = [sys.executable, "-c", "import sys;sys.path.insert(0,sys.argv.pop(1));from threshold_transfer.bdd_legacy_conditions import main;main()", str(code), str(self.path), "--source-kind", SOURCE_KIND, "--output"]
        output = Path(self.temp.name) / "index.json"
        result = subprocess.run(launch + [str(output), "--include-index"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(output.read_text())["condition_index"]), 1)
        original = self.path.read_bytes()
        result = subprocess.run(launch + [str(self.path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.path.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
