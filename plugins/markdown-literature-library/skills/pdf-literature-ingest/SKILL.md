---
name: pdf-literature-ingest
description: "批量把本地 PDF 文献转换为可追溯 Markdown，生成质量报告并分流扫描件/OCR 复核；适用于 PDF 入库、PDF 转 Markdown、乱码或版面提取检查。"
---

# PDF 文献入库

把用户指定 PDF 转为独立 Markdown 目录，同时保留原件、相对路径和质量状态。开始前读取 [质量门槛](references/quality-gates.md)。

## 执行

1. 明确源目录、Markdown 输出目录和递归范围。输出不得与源目录相同，不移动、重命名或删除 PDF。
2. 优先使用可用的本地 Microsoft MarkItDown。插件的批处理入口：

   ```text
   python ../../scripts/convert_pdfs.py <PDF目录> <Markdown目录>
   ```

   如果首选转换器无法启动或退出失败，脚本默认尝试本地 `pypdf` 降级提取；可用 `--fallback none` 禁用。降级结果一律为 `needs_review`，因为文本提取不等同于版面保真。未安装 `pypdf` 时，报告会清楚标记失败原因，不会自动安装依赖或使用外部服务。

3. 检查 `conversion-report.json` 中的 `status`、`method` 和 `reason`。`failed` 和未经人工确认的 `needs_review` 文件不得进入下游；已有输出默认跳过，只有用户允许才用 `--overwrite`。
4. 抽样比较 PDF 页面与 Markdown 的题名、摘要、章节顺序、表格、公式、图注和参考文献。
5. 扫描件或复杂版面只有在用户授权后才进入本地 OCR/版面识别；OCR 结果仍需视觉核对。

## 输出

- 与 PDF 相对路径一一对应的 Markdown。
- 每个文件的转换状态、字符数和复核原因。
- 面向下游的合格文件清单；不得用“转换命令成功”代替内容质量判断。

不要启用第三方 MarkItDown 插件，不把受版权保护的文件上传到外部服务，除非用户明确授权。
