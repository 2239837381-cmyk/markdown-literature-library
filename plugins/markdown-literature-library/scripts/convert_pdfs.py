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
    return [part.strip('"') for part in parts]


def convert_one(pdf: Path, destination: Path, command: list[str]) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run([*command, str(pdf), "-o", str(destination)], capture_output=True, text=True, check=False)
    except OSError as error:
        return {"returncode": 1, "stderr": f"无法启动首选转换器：{error}"}
    return {"returncode": result.returncode, "stderr": result.stderr[-800:].strip()}


def pypdf_fallback(pdf: Path, destination: Path) -> dict[str, str]:
    """Extract selectable text locally when the preferred converter cannot run.

    This is intentionally a recovery path, not an equivalent layout-preserving
    conversion. Callers must keep the result in ``needs_review`` status.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return {"status": "failed", "reason": "首选转换器失败，且本地未安装可选依赖 pypdf；无法执行降级提取"}
    try:
        text = "\n\n".join(page.extract_text() or "" for page in PdfReader(pdf).pages).strip()
    except Exception as error:  # pypdf exposes several document-specific exception types
        return {"status": "failed", "reason": f"pypdf 无法读取 PDF：{error}"}
    if not text:
        return {"status": "failed", "reason": "pypdf 未提取到可见文本；文件可能是扫描件、加密文档或损坏文档"}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(f"# {pdf.stem}\n\n> 提取方式：本地 pypdf 降级提取；请对照 PDF 复核版面与段落顺序。\n\n{text}\n", encoding="utf-8")
    return {"status": "needs_review", "reason": "首选转换器失败，已用本地 pypdf 降级提取；须经人工抽样核验后才能进入下游"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert PDF files with a local MarkItDown-compatible command.")
    parser.add_argument("source", type=Path, help="Source PDF directory")
    parser.add_argument("output", type=Path, help="Separate Markdown output directory")
    parser.add_argument("--converter", default="markitdown", help="Local conversion command; default: markitdown")
    parser.add_argument("--no-recursive", action="store_true", help="Read only the immediate source directory")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing Markdown outputs")
    parser.add_argument("--fallback", choices=("pypdf", "none"), default="pypdf", help="Fallback when the preferred converter fails; default: pypdf")
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
                primary_reason = result["stderr"] or f"转换器退出码 {result['returncode']}"
                if args.fallback == "pypdf":
                    fallback = pypdf_fallback(pdf, target)
                    item.update({"method": "pypdf-fallback", **fallback})
                    if fallback["status"] == "needs_review":
                        item["characters"] = len(re.sub(r"\s+", "", target.read_text(encoding="utf-8", errors="replace")))
                        item["reason"] = f"{fallback['reason']} 首选转换器原因：{primary_reason}"
                    else:
                        item["reason"] = f"首选转换器原因：{primary_reason}；{fallback['reason']}"
                else:
                    item.update({"status": "failed", "reason": primary_reason})
            else:
                reason = review_reason(target, args.min_characters)
                count = len(re.sub(r"\s+", "", target.read_text(encoding="utf-8", errors="replace"))) if target.exists() else 0
                item.update({"status": "needs_review" if reason else "converted", "characters": count, "method": "preferred-converter"})
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
