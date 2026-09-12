#!/usr/bin/env python3
"""Batch-convert PDFs with a locally installed MarkItDown-compatible command.

The script never deletes source PDFs. It writes Markdown to a separate output
directory and produces a JSON report so sparse or failed extractions are not
silently passed to the literature library.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


def pdf_files(source: Path, recursive: bool) -> list[Path]:
    paths = source.rglob("*") if recursive else source.glob("*")
    return sorted(path for path in paths if path.is_file() and path.suffix.lower() == ".pdf")


def target_path(pdf: Path, source: Path, output: Path) -> Path:
    return (output / pdf.relative_to(source)).with_suffix(".md")


def review_reason(markdown: Path, minimum_characters: int) -> str | None:
    if not markdown.exists():
        return "转换器未生成 Markdown 文件"
    text = markdown.read_text(encoding="utf-8", errors="replace")
    visible = re.sub(r"\s+", "", text)
    if not visible:
        return "输出为空，可能是扫描件、加密文档或转换失败"
    if len(visible) < minimum_characters:
        return f"可提取文本仅 {len(visible)} 个字符，低于复核阈值 {minimum_characters}"
    if visible.count("�") >= 3:
        return "输出含有多个替换字符，疑似编码或提取异常"
    return None


def converter_command(command: str) -> list[str]:
    parts = shlex.split(command, posix=not sys.platform.startswith("win"))
    if not parts:
        raise ValueError("转换器命令不能为空")
    return parts


def convert_one(pdf: Path, destination: Path, command: list[str]) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([*command, str(pdf), "-o", str(destination)], capture_output=True, text=True, check=False)
    return {"returncode": result.returncode, "stderr": result.stderr[-800:].strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert PDF files with a local MarkItDown-compatible command.")
    parser.add_argument("source", type=Path, help="Source PDF directory")
    parser.add_argument("output", type=Path, help="Separate Markdown output directory")
    parser.add_argument("--converter", default="markitdown", help="Local conversion command; default: markitdown")
    parser.add_argument("--no-recursive", action="store_true", help="Read only the immediate source directory")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing Markdown outputs")
    parser.add_argument("--min-characters", type=int, default=80, help="Text count below which a result needs review")
    parser.add_argument("--report", type=Path, help="JSON report path; default: <output>/conversion-report.json")
    args = parser.parse_args()
    source = args.source.expanduser().resolve()
    output = args.output.expanduser().resolve()
    if not source.is_dir():
        parser.error(f"source is not a directory: {source}")
    if source == output:
        parser.error("output must be a separate directory so source PDFs remain untouched")
    if args.min_characters < 0:
        parser.error("--min-characters must be non-negative")
    command = converter_command(args.converter)
    files = pdf_files(source, recursive=not args.no_recursive)
    if not files:
        parser.error("no PDF files found in source directory")
    report: list[dict[str, Any]] = []
    for pdf in files:
        target = target_path(pdf, source, output)
        item: dict[str, Any] = {"source": pdf.relative_to(source).as_posix(), "output": target.relative_to(output).as_posix()}
        if target.exists() and not args.overwrite:
            item.update({"status": "skipped", "reason": "输出已存在；使用 --overwrite 才会覆盖"})
        else:
            result = convert_one(pdf, target, command)
            if result["returncode"]:
                item.update({"status": "failed", "reason": result["stderr"] or f"转换器退出码 {result['returncode']}"})
            else:
                reason = review_reason(target, args.min_characters)
                count = len(re.sub(r"\s+", "", target.read_text(encoding="utf-8", errors="replace"))) if target.exists() else 0
                item.update({"status": "needs_review" if reason else "converted", "characters": count})
                if reason:
                    item["reason"] = reason
        report.append(item)
    output.mkdir(parents=True, exist_ok=True)
    report_path = (args.report or output / "conversion-report.json").expanduser().resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({"source": str(source), "output": str(output), "files": report}, ensure_ascii=False, indent=2), encoding="utf-8")
    counts = {status: sum(1 for item in report if item["status"] == status) for status in ("converted", "needs_review", "skipped", "failed")}
    print(json.dumps({"report": str(report_path), **counts}, ensure_ascii=False))
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
