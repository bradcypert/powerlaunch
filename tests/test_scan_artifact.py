"""Evidence validation must fail before extracting a mismatched/unexpected file."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fetch_scan_artifact import extract_verified


class ArtifactEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="artifact-evidence-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.archive = self.root / "artifact.zip"
        self.executable = b"fixture bytes, never executed"
        self.expected = hashlib.sha256(self.executable).hexdigest()

    def fixture(self, extra=None):
        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("powerlaunch.exe", self.executable)
            archive.writestr("build-info.json", '{"commit":"source-fixture"}')
            if extra:
                entry = zipfile.ZipInfo()
                # Preserve malformed raw ZIP spelling even on Windows, where
                # constructing ZipInfo(name) would normalize the test fixture.
                entry.filename = entry.orig_filename = extra
                archive.writestr(entry, b"unexpected")
        return {"id": 12, "name": "powerlaunch-windows-x64", "expired": False,
            "workflow_run": {"id": 34, "head_sha": "source-fixture"},
            "digest": "sha256:" + hashlib.sha256(self.archive.read_bytes()).hexdigest()}

    def extract(self, metadata, run=34, expected=None):
        return extract_verified(self.archive, metadata, run, expected or self.expected,
            self.root / "package", self.root / "reports/inventory.json")

    def test_verified_inventory_matches_extracted_content(self):
        evidence = self.extract(self.fixture())
        self.assertEqual((self.root / "package/powerlaunch.exe").read_bytes(), self.executable)
        inventory = json.loads((self.root / "reports/inventory.json").read_text())
        self.assertEqual(inventory, evidence)
        self.assertEqual(inventory["source_commit"], "source-fixture")
        self.assertEqual(next(f for f in inventory["files"] if f["path"] == "powerlaunch.exe")["sha256"], self.expected)

    def test_wrong_run_hash_or_archive_is_never_extracted(self):
        metadata = self.fixture()
        for run, expected in [(99, self.expected), (34, "0" * 64)]:
            with self.subTest(run=run, expected=expected):
                with self.assertRaises(ValueError):
                    self.extract(metadata, run, expected)
                self.assertFalse((self.root / "package").exists())
        self.archive.write_bytes(self.archive.read_bytes() + b"changed")
        with self.assertRaises(ValueError):
            self.extract(metadata)
        self.assertFalse((self.root / "package").exists())

    def test_windows_reader_normalization_does_not_hide_raw_path(self):
        with mock.patch("zipfile.os.sep", "\\"):
            with self.assertRaises(ValueError):
                self.extract(self.fixture("folder\\outside"))
        self.assertFalse((self.root / "package").exists())

    def test_traversal_and_windows_name_collisions_are_rejected(self):
        for name in ["../outside", "C:/outside", "folder\\outside", "Powerlaunch.exe"]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.extract(self.fixture(name))
                self.assertFalse((self.root / "package").exists())


if __name__ == "__main__":
    unittest.main()
