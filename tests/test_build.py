import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "markdown-literature-library" / "scripts" / "build_library.py"


class BuildLibraryTests(unittest.TestCase):
    def test_builds_standalone_library(self):
        examples = ROOT / "plugins" / "markdown-literature-library" / "examples"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "library.html"
            result = subprocess.run([sys.executable, str(SCRIPT), str(examples), str(output)], check=True, capture_output=True, text=True)
            report = json.loads(result.stdout)
            page = output.read_text(encoding="utf-8")
            manifest_exists = output.with_suffix(".manifest.json").exists()
        self.assertEqual(report["documents"], 2)
        self.assertEqual(report["changes"]["added"], 2)
        self.assertTrue(manifest_exists)
        self.assertIn("Shared identity and collective participation", page)
        self.assertIn('id="noteList"', page)
        self.assertIn("localStorage", page)
        self.assertIn("contextmenu", page)
        self.assertIn("exportCurrent", page)
        self.assertNotIn("https://fonts", page)

    def test_incremental_manifest_reports_unchanged(self):
        examples = ROOT / "plugins" / "markdown-literature-library" / "examples"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "library.html"
            subprocess.run([sys.executable, str(SCRIPT), str(examples), str(output)], check=True, capture_output=True, text=True)
            second = subprocess.run([sys.executable, str(SCRIPT), str(examples), str(output)], check=True, capture_output=True, text=True)
            report = json.loads(second.stdout)
        self.assertEqual(report["changes"]["unchanged"], 2)
        self.assertEqual(report["changes"]["added"], 0)


if __name__ == "__main__":
    unittest.main()
