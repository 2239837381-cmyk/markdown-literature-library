#!/usr/bin/env python3
"""Create evidence-labelled paper cards, relations, BibTeX and RIS."""

from __future__ import annotations

import argparse
import itertools
import json
import re
from pathlib import Path
from typing import Any

from build_library import TOPICS, build_documents, read_text, split_front_matter

FIELD_HEADINGS = {
    "research_question": ("research question", "objective", "aim", "研究问题", "研究目的", "问题意识"),
    "theory": ("theory", "framework", "理论", "分析框架", "理论框架"),
    "methods": ("method", "data", "sample", "方法", "数据", "样本", "研究设计"),
    "findings": ("finding", "result", "conclusion", "发现", "结果", "结论"),
    "limitations": ("limitation", "future research", "局限", "不足", "未来研究"),
}


def sections(markdown: str) -> dict[str, str]:
    result: dict[str, list[str]] = {"__preamble__": []}
    current = "__preamble__"
    for line in markdown.splitlines():
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", line)
        if heading:
            current = re.sub(r"[*`_]", "", heading.group(1)).strip().lower()
            result.setdefault(current, [])
        else:
            result[current].append(line)
    return {key: re.sub(r"\s+", " ", "\n".join(value)).strip() for key, value in result.items()}


def section_field(parts: dict[str, str], aliases: tuple[str, ...]) -> tuple[str, str]:
    for heading, text in parts.items():
        if any(alias in heading for alias in aliases) and text:
            return text[:1200], "explicit"
    return "", "not_found"


def metadata_for(path: Path) -> dict[str, str]:
    metadata, _ = split_front_matter(read_text(path))
    return metadata


def find_doi(text: str, metadata: dict[str, str]) -> str:
    if metadata.get("doi"):
        return metadata["doi"].removeprefix("https://doi.org/").strip()
    match = re.search(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", text, re.IGNORECASE)
    return match.group(0).rstrip(".,;)") if match else ""


def split_tags(value: str) -> list[str]:
    return sorted({part.strip().lower() for part in re.split(r"[,，;；|]", value or "") if part.strip()})


def card_for(document: dict[str, Any], source: Path) -> dict[str, Any]:
    path = source / document["filename"]
    metadata = metadata_for(path)
    parts = sections(document["markdown"])
    fields: dict[str, str] = {}
    evidence: dict[str, str] = {}
    for field, aliases in FIELD_HEADINGS.items():
        fields[field], evidence[field] = section_field(parts, aliases)
    authors = metadata.get("authors") or metadata.get("author") or ""
    doi = find_doi(document["markdown"], metadata)
    return {
        "id": document["id"], "title": document["title"], "authors": authors,
        "year": document["year"], "doi": doi, "tags": split_tags(document["tags"]),
        "topics": document["topics"], "excerpt": document["excerpt"], "source": document["filename"],
        **fields,
        "evidence": {
            "title": "explicit", "authors": "explicit" if authors else "not_found",
            "year": "explicit" if document["year"] else "not_found",
            "doi": "explicit" if doi else "not_found", **evidence,
        },
    }


def relations(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for left, right in itertools.combinations(cards, 2):
        shared_tags = sorted(set(left["tags"]) & set(right["tags"]))
        shared_topics = sorted(set(left["topics"]) & set(right["topics"]))
        if shared_tags:
            result.append({"source": left["id"], "target": right["id"], "type": "shared-metadata", "evidence": "explicit", "basis": shared_tags})
        elif len(shared_topics) >= 2:
            result.append({"source": left["id"], "target": right["id"], "type": "topic-cooccurrence", "evidence": "inferred", "basis": shared_topics})
    return result


def citation_key(card: dict[str, Any]) -> str:
    author = re.sub(r"[^A-Za-z0-9]", "", card["authors"].split(",")[0]) or "document"
    year = card["year"] or "nd"
    return f"{author}{year}{card['id'][-4:]}"


def bibtex(cards: list[dict[str, Any]]) -> str:
    entries = []
    for card in cards:
        fields = [("title", card["title"]), ("author", card["authors"]), ("year", card["year"]), ("doi", card["doi"]), ("note", f"Source: {card['source']}")]
        body = ",\n".join(f"  {name} = {{{str(value).replace('{', '').replace('}', '')}}}" for name, value in fields if value)
        entries.append(f"@misc{{{citation_key(card)},\n{body}\n}}")
    return "\n\n".join(entries) + "\n"


def ris(cards: list[dict[str, Any]]) -> str:
    records = []
    for card in cards:
        lines = ["TY  - GEN", f"TI  - {card['title']}"]
        if card["authors"]:
            lines.extend(f"AU  - {name.strip()}" for name in re.split(r"[;；]", card["authors"]) if name.strip())
        if card["year"]:
            lines.append(f"PY  - {card['year']}")
        if card["doi"]:
            lines.append(f"DO  - {card['doi']}")
        lines.extend([f"N1  - Source: {card['source']}", "ER  -"])
        records.append("\n".join(lines))
    return "\n\n".join(records) + "\n"


def cards_markdown(cards: list[dict[str, Any]]) -> str:
    labels = [("research_question", "研究问题"), ("theory", "理论框架"), ("methods", "方法"), ("findings", "主要发现"), ("limitations", "局限")]
    blocks = ["# 文献卡片", ""]
    for card in cards:
        blocks.extend([f"## {card['title']}", "", f"- 来源：`{card['source']}`", f"- 作者：{card['authors'] or '未找到'}", f"- 年份：{card['year'] or '未找到'}", f"- DOI：{card['doi'] or '未找到'}", f"- 主题：{', '.join(card['topics'])}", ""])
        for field, label in labels:
            blocks.extend([f"### {label} [{card['evidence'][field]}]", "", card[field] or "未找到明确内容。", ""])
    return "\n".join(blocks)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze verified Markdown literature.")
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--no-recursive", action="store_true")
    args = parser.parse_args()
    source, output = args.source.expanduser().resolve(), args.output.expanduser().resolve()
    if not source.is_dir():
        parser.error(f"source is not a directory: {source}")
    documents = build_documents(source, recursive=not args.no_recursive)
    if not documents:
        parser.error("no Markdown files found")
    output.mkdir(parents=True, exist_ok=True)
    cards = [card_for(document, source) for document in documents]
    graph = {"schema_version": 1, "documents": cards, "topics": {key: {"label": value["label"], "color": value["color"]} for key, value in TOPICS.items()}, "relations": relations(cards)}
    (output / "literature-index.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "literature-cards.md").write_text(cards_markdown(cards), encoding="utf-8")
    (output / "references.bib").write_text(bibtex(cards), encoding="utf-8")
    (output / "references.ris").write_text(ris(cards), encoding="utf-8")
    print(json.dumps({"documents": len(cards), "relations": len(graph["relations"]), "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
