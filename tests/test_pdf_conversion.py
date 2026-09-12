import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "markdown-literature-library" / "scripts" / "convert_pdfs.py"
SPEC = importlib.util.spec_from_file_location("convert_pdfs", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PdfConversionTests(unittest.TestCase):
    def test_converter_command_strips_windows_path_quotes(self):
        command = 'python "C:\\Users\\Example User\\tools\\convert.py"'
        self.assertEqual(MODULE.converter_command(command), ["python", "C:\\Users\\Example User\\tools\\convert.py"])

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

    def test_pypdf_fallback_writes_markdown_and_requires_review(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "paper.pdf"
            target = root / "output" / "paper.md"
            source.write_bytes(b"%PDF fictional fixture")
            fake_module = ModuleType("pypdf")
            fake_module.PdfReader = lambda _: SimpleNamespace(pages=[SimpleNamespace(extract_text=lambda: "Extracted PDF text")])
            with patch.dict(sys.modules, {"pypdf": fake_module}):
                result = MODULE.pypdf_fallback(source, target)
            self.assertEqual(result["status"], "needs_review")
            self.assertIn("降级提取", target.read_text(encoding="utf-8"))
            self.assertIn("Extracted PDF text", target.read_text(encoding="utf-8"))

    def test_missing_converter_returns_a_reportable_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = MODULE.convert_one(root / "paper.pdf", root / "output" / "paper.md", ["definitely-not-a-local-converter"])
            self.assertNotEqual(result["returncode"], 0)
            self.assertIn("无法启动首选转换器", result["stderr"])


if __name__ == "__main__":
    unittest.main()
