import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "markdown-literature-library" / "scripts" / "analyze_literature.py"


class LiteratureAnalysisTests(unittest.TestCase):
    def test_outputs_cards_relations_and_citations(self):
        examples = ROOT / "plugins" / "markdown-literature-library" / "examples"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = subprocess.run([sys.executable, str(SCRIPT), str(examples), str(output)], check=True, capture_output=True, text=True)
            report = json.loads(result.stdout)
            index = json.loads((output / "literature-index.json").read_text(encoding="utf-8"))
            cards = (output / "literature-cards.md").read_text(encoding="utf-8")
            bib = (output / "references.bib").read_text(encoding="utf-8")
            ris = (output / "references.ris").read_text(encoding="utf-8")
        self.assertEqual(report["documents"], 2)
        self.assertEqual(len(index["documents"]), 2)
        self.assertGreaterEqual(len(index["relations"]), 1)
        self.assertEqual(index["relations"][0]["evidence"], "explicit")
        self.assertIn("explicit", cards)
        self.assertIn("10.0000/fictional.2024.001", bib)
        self.assertIn("TY  - GEN", ris)


if __name__ == "__main__":
    unittest.main()
