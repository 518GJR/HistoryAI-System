# Fallback 实际证据追溯修复记录

## 范围

本目录记录 `13f7c81` 之后的 fallback 证据追溯修复和资料充分性最小设计。原始向量检索与 API 失败报告仍保留在 `docs/evaluation/2026-10-22-vector-retrieval/`，本轮没有覆盖或改写。

## 已实现：fallback 证据追溯

- 模板回答保持原有文字和排序。
- 记录模板实际渲染的教材字段，只有完整 `excerpt` 确实出现在这些字段中时，才进入 `used_evidence`。
- 问题复述、系统确定性说明、内部 `certainty` 以及未逐字进入回答的候选不计为教材证据。
- 同源同文按 `(source_id, excerpt)` 去重，合并知识点 ID 和标题，保留教材页码与 PDF 页序。
- 模型证据选择路径的选择逻辑不变，与 fallback 共用同一证据快照格式。
- 无检索结果时的资料不足回答仍返回 `used_evidence=[]`。

当前 vector fallback 会把所有 Top K 原文渲染进模板，因此这些原文都可能被如实记录为实际证据。这是对现有模板行为的追溯，不是对候选相关性的认可。

## 仍未修复

范围外问题仍可以得到 vector 最近邻，并被现有模板组装成无关回答。本轮没有实现资料充分性门控，没有增加临时相似度阈值或题目特判。该缺陷继续以原始 API 报告为准。

资料充分性方案见 [support-assessment-design.md](support-assessment-design.md)；它是设计，不是已实现能力。

## 验证边界

- AI、ASR、TTS 显式 disabled。
- TestClient 使用测试内存 SQLite，不连接原验收库。
- 测试夹具默认阻断外部 HTTP。
- 首次受限环境运行在 TestClient 建立 AnyIO 事件循环时阻塞于 Windows `socketpair()`；线程栈证明尚未进入检索、Embedding 或回答代码。允许本机回环 socket 后同一测试集正常完成。
- 专项测试：`27 passed in 1.44s`，退出码 0。
- 完整后端离线回归：`67 passed in 1.89s`，退出码 0。
- 本轮没有运行真实 AI/ASR/TTS，没有重复前端构建，也没有开展正式效果实验。
