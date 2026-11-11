"""Package regression tests: contents remain explicit and free of local secrets."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))
from package_source import FOLDER, source_files, make_zip
from verify_source_zip import verify


class SourcePackageTests(unittest.TestCase):
    def test_source_allowlist_excludes_secrets_and_binaries(self):
        paths = [p.as_posix() for p in source_files()]
        self.assertIn("app.py", paths)
        self.assertIn("dashboard.py", paths)
        self.assertIn("RUN-JARVIS.py", paths)
        self.assertIn("START-JARVIS.cmd", paths)
        self.assertFalse(any(p.endswith((".exe", ".env", ".pyc", ".zip")) for p in paths))
        self.assertFalse(any(p.startswith((".git/", ".venv/", "build/", "dist/")) for p in paths))

    def test_bundle_manifest_and_integrity(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "Jarvis-Source-Windows.zip"
            make_zip(destination)
            self.assertTrue(destination.is_file())
            self.assertGreater(verify(destination), 10)
            with ZipFile(destination) as archive:
                self.assertIn(f"{FOLDER}/README-START-HERE.txt", archive.namelist())
                self.assertIn(f"{FOLDER}/START-JARVIS.cmd", archive.namelist())
                self.assertNotIn(f"{FOLDER}/Jarvis.exe", archive.namelist())


if __name__ == "__main__":
    unittest.main()
