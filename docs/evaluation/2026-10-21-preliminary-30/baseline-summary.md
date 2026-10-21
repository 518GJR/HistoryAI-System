# 2026-10-21 修复前 30 题评估摘要

## 结论

- 记录数量：30。
- 映射范围：E01—E30 对应历史 ID 36—65，ID 连续，无缺失或范围内重复。
- 初评汇总：26 题通过、3 题部分通过、1 题失败。
- 本轮30题初评通过率：86.7%（26/30，四舍五入到1位小数）。该比例仅描述本轮样本，不能称为系统整体准确率。
- 部分通过：E10（历史 ID 45）、E25（历史 ID 60）、E26（历史 ID 61）。
- 失败：E20（历史 ID 55）。
- 评分来源：ChatGPT辅助浏览器初评，待教材PDF及第二人复核。

## 题目文本核对

- E04（历史 ID 39）原题为“旧石器时代和新石器时代主要使用的石器有什么区别？”，实际输入为“石器时代和新石器时代主要使用的石器有什么区别？”。实际输入少“旧”字，归档同时保留两者。
- E15原题带句末句号，历史实际输入未带句末句号，语义一致；归档同时保留两者。
- 其余28题原题与历史实际问句一致。
- 完整原题、参考答案必答要点、参考来源页码和评分口径已补入[`questions-and-rubric.md`](questions-and-rubric.md)。参考来源不等于系统实际采用证据。

## sources 与证据去重

- 顶层历史记录实际字段：`id`、`question`、`answer`、`sources`、`created_at`。
- `sources` 候选实际字段：`title`、`dynasty`、`score`、`knowledge_id`、`book_id`、`book_title`、`unit_id`、`unit_title`、`lesson_id`、`lesson_number`、`lesson_title`、`section_title`、`material_types`、`textbook_pages`、`pdf_pages`、`qualifiers`、`evidence_type`、`certainty`、`source_refs`、`used_evidence`。
- `source_refs` 实际字段：`source_id`、`material_type`、`textbook_pages`、`pdf_pages`、`excerpt`、`locator`。
- `used_evidence` 实际字段并集：`evidence_id`、`text`、`knowledge_id`、`knowledge_ids`、`source_ids`、`source_title`、`source_titles`、`textbook_pages`、`pdf_pages`。
- 30 题共保存 36 条候选内 `used_evidence`。按题内的 `evidence_id + knowledge_id + source_ids + text` 去重后为 30 条，减少 6 条重复。
- E20、E30 的 `sources` 为 `[]`；不补写证据。

| 题号 | 历史ID | 原始 used_evidence 数 | 去重后 | 重复数 | 重复 evidence_id |
| --- | ---: | ---: | ---: | ---: | --- |
| E03 | 38 | 3 | 1 | 2 | E1 |
| E05 | 40 | 2 | 1 | 1 | E1 |
| E07 | 42 | 3 | 2 | 1 | E2 |
| E10 | 45 | 2 | 1 | 1 | E1 |
| E12 | 47 | 2 | 1 | 1 | E1 |

完整候选来源与原始重复仍保留在原始 JSON 中；`baseline-results.csv` 只对汇总证据去重。

## 生成路径与待复核项

- 历史记录和 `sources` 中没有独立的生成路径字段。
- 生成路径统一标记“待截图核对”，不凭回答样式、来源字段或证据字段推断。
- 截图材料、PDF 复核、第二人复核均待补或待完成。

## 完整性检查

- `baseline-results.csv`：30 条数据行。
- `baseline-results.csv`仅补齐原题、文本核对、必答要点和评分来源等描述性元数据；原始回答、初评结果和实际证据保持修复前内容。
- `retest-results.csv`：仅表头，无复测结果。
- 65条原始历史导出仅在本地`tmp/evaluation-export-20261021-230010/history-raw.json`保留，不纳入GitHub提交。
- 原始 JSON SHA-256：`2ad06d42a6d8d506ca4ecc837a1ebab7aaf89b6124e01c9f05949703abfe5b9c`。归档生成及元数据补齐过程均未修改原始 JSON。
- 仓库内的逐题问题、评分规则、原始回答、初评状态、去重证据和来源追溯字段足以供老师查阅修复前基线；如需核查候选间原始重复，再使用上述本地导出按哈希确认。
