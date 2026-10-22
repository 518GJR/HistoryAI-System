# 第一版本地教材向量检索验证

## 验证边界

- 日期：2026-10-22
- 数据：七年级上册第 1—3 课现有教材 JSON
- 模型：`BAAI/bge-small-zh-v1.5`
- 修订：`7999e1d3359715c523056ef9478215996d62a620`
- 许可证：MIT
- 运行：Windows、Python 3.12.2、PyTorch 2.9.1+cpu、本地 CPU
- AI / ASR / TTS：显式 disabled
- 验证脚本只调用检索层，不调用问答模型、不写问答历史

## 索引实测

- 原始来源数：35
- 去重索引片段数：35
- 向量维度：512
- 最大文档 token 数：281
- 模型上限：512；未切分、未截断
- 教材数据 SHA-256：`c7b206d12fe315664389a1516f8c822b62d90c32229836f9f5f2417d81b1eeb5`
- 35 条来源的 `source_id`、原文、材料类型、lesson/section、教材页码、PDF 页序与知识点关联逐条一致
- 向量全部有限、非零并已 L2 归一化；单位范数最大误差 `1.1920928955078125e-07`

## 结果摘要

- 事实题“北京人用火有什么作用”：keyword 和 vector 第 1 名均为 `H7A-P006-B`。
- 换问法“掌握火给北京人的生存带来了哪些好处”：vector 第 1 名为 `H7A-P006-B`；keyword 的同一来源为第 2 名。
- 仰韶文化事实题：两种模式第 1 名均覆盖 `H7A-P012-A`。
- 北京人/山顶洞人工具比较：双方来源 `H7A-P006-A`、`H7A-P007-A` 均进入两种模式 Top 3。
- 河姆渡/半坡比较：双方来源 `H7A-P011-A`、`H7A-P012-B` 均进入两种模式 Top 3。
- 范围外秦始皇题：keyword 无结果；vector 仍返回史前教材近邻，证明最近邻不能直接作为存在回答依据。
- 首次 vector 查询含模型加载约 16.3 秒；同进程后续查询约 19.7—21.0 毫秒。本结果只描述该次本机运行，不作为通用性能承诺。

逐题原始排名、分数、来源、页码、实际模式和耗时保存在 [real-retrieval-results.json](real-retrieval-results.json)。

## 实际运行 API 集成验证

使用独立 SQLite `tmp/vector_api_integration_20261022_01.db`、真实本地 Embedding、离线模型缓存以及显式 disabled 的 AI/ASR/TTS，在不带 `--reload` 的 Uvicorn `127.0.0.1:8000` 上完成两次实际 HTTP 问答。原验收库 `tmp/acceptance_a_offline.db` 未被该进程引用；验证后其 SHA-256 仍为 `b4e0ba871173cd6ca89ce26bd853a5d19cf7ef876736967e8cc5c84b67a6e070`。独立测试库新增 2 条验证历史，不属于原验收数据。

- 两题顶层 `retrieval_mode` 均为 `vector`，所有候选来源均标记 `retrieval_mode=vector`、`retrieval_unit=source_excerpt`。
- 北京人用火题的首位来源为 `H7A-P006-B`，教材第 6 页、PDF 页序 11，原文片段贯通。
- disabled AI 下 `answer_mode=fallback`，顶层及来源内 `used_evidence` 均为空。因此本次只能证明候选原文、来源和页码贯通，不能宣称“实际采用证据”已产生。
- 范围外秦始皇题未正确拒答：系统把养蚕丝织、禹治水和仰韶文化近邻组装成无关史前答案。该结果已原样保留，列为后续通用资料充分性/拒答机制待修复项；本轮未删除近邻、未设置单题阈值，也未添加题目特判。

完整 API 响应、检查项和耗时另存于 [api-integration-results.json](api-integration-results.json)，没有覆盖原真实检索报告。

本阶段最终离线回归为 `64 passed in 2.18s`，pytest 退出码 0。该退出码只说明自动测试套件通过；API 报告中的 `used_evidence_present=false` 和 `out_of_scope_answer_refuses=false` 是被成功记录的现象，不是对应功能通过。详细路径分析见 [api-integration-analysis.md](api-integration-analysis.md)。

## 结论口径

本轮可以声明“代码实现完成”和“真实向量建库检索验证完成”。本轮只有小规模开发与 API 集成验证，不能声明“正式对照实验完成”。keyword 的 Top K 单位是知识点，vector 的 Top K 单位是去重来源片段，两者相同 K 不等于相同证据预算；正式实验前必须统一或等价化证据预算并冻结口径。余弦相似度不是答案正确概率，本轮没有校准资料充分性阈值。
