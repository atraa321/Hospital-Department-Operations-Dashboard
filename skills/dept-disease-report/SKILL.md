---
name: "dept-disease-report"
description: "按科室和时间段自动生成病种分析报告（Markdown+PDF）。当用户提出“给某科室在某时间段做病种分析报告”“输出.md和PDF”“复用同一分析口径批量出报告”等需求时使用。"
---

# 科室病种分析报告技能

使用本技能可基于数据库数据，按统一口径生成科室病种分析报告，输出 `.md` 与 `.pdf` 两种格式，并自动生成图表可视化（PNG）嵌入报告正文。

## 分析依据

- 报告结构与分析逻辑固定依据项目根目录的 [`病种分析步骤.md`](../../病种分析步骤.md)。
- 输出报告默认采用五步法完整结构：
  1. 定病种
  2. 拆结构
  3. 找漏洞
  4. 定标准
  5. 强闭环
- 如用户仅给出“科室+时间段”，仍按上述完整框架输出，不省略关键章节。
- 每个步骤完成后，自动追加一段“本步小结”，用于院内汇报场景下的结论表达。
- 自动生成同比/环比分析段落（关键指标变化表），用于年度趋势与近期波动判断。
- 默认生成趋势图、病种费用贡献图、DIP映射分布图等可视化图表，并在 Markdown 与 PDF 中展示。
- 全文默认使用正式、详尽的院内汇报语气，避免口语化与冗余表述。

## 输入参数

- 科室名称（例如：`神经内科`）
- 开始日期（`YYYY-MM-DD`）
- 结束日期（`YYYY-MM-DD`，含当天）

## 执行方式

在项目根目录执行：

```powershell
python skills/dept-disease-report/scripts/generate_report.py `
  --dept "神经内科" `
  --date-from 2025-01-01 `
  --date-to 2025-12-31 `
  --output-dir docs
```

可选参数：

- `--output-name`：自定义输出文件基名（不带扩展名）。
- `--db-url`：显式指定数据库连接串；不传则自动读取 `backend/.env` 的 `DATABASE_URL`。
- `--refresh-dip`：生成前先执行全量 DIP 重算（建议在导入新病案后使用）。
- `--no-charts`：关闭图表生成与报告内嵌（仅输出文字与表格）。

示例：

```powershell
python skills/dept-disease-report/scripts/generate_report.py `
  --dept "心血管内科" `
  --date-from 2025-01-01 `
  --date-to 2025-06-30 `
  --output-dir docs `
  --output-name "心血管内科_2025上半年病种分析报告" `
  --refresh-dip
```

## 输出结果

脚本会输出：

- `{output-name}.md`
- `{output-name}.pdf`
- `{output-name}_charts/`（图表目录，含 PNG 文件）

默认保存在 `docs/` 目录。

## 注意事项

- 若某科室在给定时间段无病例，脚本会提示并列出可用科室名称。
- PDF 由 Markdown 自动转换，使用系统中文字体渲染（Windows优先使用微软雅黑）。
- 如遇到 DIP 入组率异常，优先使用 `--refresh-dip` 后再生成报告。
- 图表功能依赖 `matplotlib`；若环境未安装，脚本会自动跳过图表并继续生成报告。
