import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "markdown-literature-library" / "scripts" / "convert_pdfs.py"
SPEC = importlib.util.spec_from_file_location("convert_pdfs", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PdfConversionTests(unittest.TestCase):
    def test_preserves_relative_name_and_flags_sparse_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            output = root / "output"
            pdf = source / "nested" / "paper.pdf"
            pdf.parent.mkdir(parents=True)
            pdf.write_bytes(b"%PDF fictional fixture")
            target = MODULE.target_path(pdf, source, output)
            self.assertEqual(target.relative_to(output).as_posix(), "nested/paper.md")
            target.parent.mkdir(parents=True)
            target.write_text("too short", encoding="utf-8")
            self.assertIn("低于复核阈值", MODULE.review_reason(target, 80))
            target.write_text("可提取文本 " * 30, encoding="utf-8")
            self.assertIsNone(MODULE.review_reason(target, 80))


if __name__ == "__main__":
    unittest.main()
