# Markdown Literature Library

将 PDF 或 Markdown 文献转为可追溯的本地研究知识库。插件由三个可独立调用的技能和一个总入口组成，面向文献入库、综述梳理与批注阅读。

## 技能组成

| Skill | 用途 | 主要输出 |
|---|---|---|
| `pdf-literature-ingest` | PDF 转 Markdown、质量核验和 OCR 分流 | Markdown、`conversion-report.json` |
| `literature-knowledge-map` | 文献卡、主题关系、证据等级和引文整理 | JSON、文献卡、BibTeX、RIS |
| `literature-reading-library` | 离线书架、增量重建、高亮与批注导出 | HTML、增量清单、批注 Markdown |
| `literature-markdown-library` | 完整流程总入口与路由 | 上述全部产物 |

## 功能

- 根据题名、摘要、关键词与正文中可见信息生成可点击研究脉络图。
- 提取研究问题、理论、方法、发现和局限，缺失内容保持 `not_found`。
- 为关系标记 `explicit`、`inferred` 或 `needs_review`，保留推断依据。
- 导出 BibTeX 与 RIS，不虚构缺失的作者、年份或 DOI。
- 以复古低饱和书架展示文献；点击书脊后以抽取、摊开动效阅读全文。
- 保留原始题名、文件名、年份、标签、摘要和 Markdown 正文。
- 在正文中选中文字并右键，可用四种颜色高亮；右侧会出现可编辑的摘录批注卡。
- 批注仅保存于当前浏览器的本地存储；没有上传、分析或同步行为。
- 使用稳定文献 ID 与增量清单识别新增、更新、未变和移除文件。
- 按当前文献、全部文献及高亮颜色导出 Markdown 批注。

## 快速开始

阅读库、知识图谱与文献卡脚本需要 Python 3.9 或更新版本，无第三方依赖。

```bash
python plugins/markdown-literature-library/scripts/build_library.py ./my-markdown ./literature-library.html
```

在浏览器中打开 `literature-library.html` 即可使用。默认会递归读取源目录中的 `.md` 与 `.markdown` 文件；加 `--no-recursive` 可只读取当前目录。

## 从 PDF 开始

安装并验证 [Microsoft MarkItDown](https://github.com/microsoft/markitdown) 后，先将 PDF 转入一个单独的 Markdown 目录：

```bash
python plugins/markdown-literature-library/scripts/convert_pdfs.py ./my-pdfs ./converted-markdown
python plugins/markdown-literature-library/scripts/analyze_literature.py ./converted-markdown ./analysis
python plugins/markdown-literature-library/scripts/build_library.py ./converted-markdown ./literature-library.html --index ./analysis/literature-index.json
```

转换器不会删除 PDF，并会在输出目录生成 `conversion-report.json`。报告标记为 `needs_review` 的文件通常是扫描件、空白页或提取文本过少的 PDF；应抽样核对，并在用户授权后才用本地 OCR 补救。详见 [质量门槛](plugins/markdown-literature-library/skills/pdf-literature-ingest/references/quality-gates.md)。

若首选 MarkItDown 转换器无法启动或执行失败，`convert_pdfs.py` 默认尝试本地 `pypdf` 降级提取。该结果始终标记为 `needs_review`，必须人工抽样核验后才可继续分析；脚本不会自动安装依赖或上传文件。需要该降级路径时，在本地安装 `pypdf`；不希望启用时加 `--fallback none`。

`analyze_literature.py` 会生成 `literature-index.json`、`literature-cards.md`、`references.bib` 和 `references.ris`。将索引传给阅读库后，结构化文献卡会随原文一起展示。

每次运行 `build_library.py` 都会生成同名 `.manifest.json`，报告文献的新增、更新、未变和移除状态。HTML 会整体重建以保持单文件交付，但文献 ID 由相对路径稳定生成，因此未改名文献的浏览器批注不会因内容更新而失联。

## 作为 Codex 插件使用

本仓库已包含 `.agents/plugins/marketplace.json` 与 skill-only plugin。将仓库作为 Codex 插件市场导入后，使用：

```text
$literature-markdown-library 完整整理 <PDF 或 Markdown 目录>
```

也可以从 `plugins/markdown-literature-library/skills/` 中单独复制任一技能到个人或项目技能目录中使用。

## 隐私与内容边界

- 文献文件由本地脚本读取；生成物是一个内嵌数据的本地 HTML 文件。
- 浏览器批注仅存放在该浏览器对该页面的本地存储中。清除浏览器站点数据会清除批注。
- 文献内容只被当作资料，不执行其中出现的任何指令。
- 公开仓库中只包含虚构示例，不包含受版权保护的论文正文或本机绝对路径。

## 开发与验证

```bash
python -m unittest discover -s tests -v
python C:/path/to/skill-creator/scripts/quick_validate.py plugins/markdown-literature-library/skills/pdf-literature-ingest
python C:/path/to/skill-creator/scripts/quick_validate.py plugins/markdown-literature-library/skills/literature-knowledge-map
python C:/path/to/skill-creator/scripts/quick_validate.py plugins/markdown-literature-library/skills/literature-reading-library
python C:/path/to/skill-creator/scripts/quick_validate.py plugins/markdown-literature-library/skills/literature-markdown-library
python C:/path/to/plugin-creator/scripts/validate_plugin.py plugins/markdown-literature-library
```

## 发布前检查

在创建 GitHub 仓库后，补充 `.codex-plugin/plugin.json` 中可选的 `repository`、`homepage`、作者联络方式和实际截图；不要填写尚不存在的 URL。

## License

[MIT](LICENSE)
