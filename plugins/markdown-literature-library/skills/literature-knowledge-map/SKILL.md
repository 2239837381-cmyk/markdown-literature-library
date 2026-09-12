---
name: literature-knowledge-map
description: "从已核验 Markdown 文献提取结构化文献卡、主题关系、证据等级与 BibTeX/RIS；适用于综述梳理、研究脉络、理论关系、方法比较和引文整理。"
---

# 文献知识图谱

只接受已核验 Markdown。若输入来自 PDF 且没有质量报告，先使用 `pdf-literature-ingest`。

## 执行

1. 运行结构化分析器：

   ```text
   python ../../scripts/analyze_literature.py <Markdown目录> <分析输出目录>
   ```

2. 按 [文献卡与证据模式](references/evidence-schema.md)检查文献卡。缺失字段保持空白或 `not_found`，不能根据常识补写。
3. 关系必须携带证据等级与依据：元数据中明确共享的标签为 `explicit`；正文关键词或主题共现为 `inferred`；信息不足为 `needs_review`。
4. 复核高中心性关系和所有 `needs_review` 项，再把 `literature-index.json` 交给阅读库使用。

## 输出

- `literature-index.json`：文献卡、主题、关系、证据等级和来源定位。
- `literature-cards.md`：便于人工阅读的卡片集合。
- `references.bib` 与 `references.ris`：仅使用文献中已有的作者、题名、年份和 DOI；不完整记录应保留而不虚构。

外部检索、DOI 校验和引用指标不属于默认流程，只有用户明确要求时才能增加。
