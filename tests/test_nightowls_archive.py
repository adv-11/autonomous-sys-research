"""Synthetic ZIP integrity checks; no dataset members or network requests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location(
    "verify_nightowls_archive", Path(__file__).resolve().parents[1] /
    "scripts/data/verify_nightowls_archive.py")
VERIFY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFY)


class ArchiveVerificationTests(unittest.TestCase):
    def test_full_members_counts_and_bad_reference(self):
        with tempfile.TemporaryDirectory() as d:
            archive, report = Path(d) / "synthetic.zip", Path(d) / "counts.json"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("synthetic/", b"")
                z.writestr("synthetic/fake.png", b"not an actual image")
                z.writestr("synthetic/fake.json", b"{}")
            first = VERIFY.verify(archive, report, archive.stat().st_size)
            self.assertTrue(first["passed"])
            self.assertEqual(first["crc_members_checked"], 3)
            self.assertEqual(first["image_count"], 1)
            self.assertEqual(first["annotation_file_count"], 1)
            self.assertNotIn("fake", report.read_text())
            self.assertFalse(VERIFY.verify(archive, report, 0, "wrong")["passed"])

    def test_crc_failure_does_not_skip_later_members(self):
        with tempfile.TemporaryDirectory() as d:
            archive, report = Path(d) / "synthetic.zip", Path(d) / "counts.json"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_STORED) as z:
                z.writestr("one.png", b"unique payload")
                z.writestr("two.png", b"still checked")
            archive.write_bytes(archive.read_bytes().replace(b"unique payload", b"broken payload", 1))
            result = VERIFY.verify(archive, report, archive.stat().st_size)
            self.assertFalse(result["passed"])
            self.assertEqual(result["crc_failed_members"], 1)
            self.assertEqual(result["crc_members_checked"], 1)


if __name__ == "__main__":
    unittest.main()
