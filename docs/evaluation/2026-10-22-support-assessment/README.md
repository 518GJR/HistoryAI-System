# 资料支持判断实现与冻结后新题验证

## 状态与边界

- 基线提交：`2357af3d3812a0c5e9bdce3440bf4007443d9ba2`；分支：`feat/textbook-vector-retrieval`；本轮改动未提交。
- 规则版本：`interpretable-v1`；校准标记：`development-set-v1`。
- 教材数据 SHA-256：`c7b206d12fe315664389a1516f8c822b62d90c32229836f9f5f2417d81b1eeb5`。
- 默认检索模式仍为 `keyword`。没有改 Prompt、没有扩教材、没有改界面、没有按新题结果继续修改规则。
- 原始向量失败报告 `../2026-10-22-vector-retrieval/api-integration-results.json` 保持不变。

## 已实现

检索后、回答前新增结构化资料支持判断，记录必需/已覆盖/未覆盖要点、支持来源和知识点。候选来源完整保留；只有同时覆盖所问对象、通用维度和已识别主题且有教材原文的来源才进入回答。回答后再按 `used_evidence` 复核全部必需要点；失败时返回 `answer_mode=insufficient_support` 且 `used_evidence=[]`。比较题要求双方实际证据覆盖，确定性问题保留教材限定词。向量余弦分数不作为充分性阈值。

## 测试与原始记录

- 完整后端离线回归：`73 passed, 0 failed in 2.09s`，pytest 退出码 `0`。TestClient 使用独立 SQLite；AI/ASR/TTS 显式 disabled；外部 HTTP 由夹具阻断。
- `precalibration-results.json` 是首次规则校准前输出；它暴露了同人物不同主题等问题，随后用于调整，因此只算开发材料。
- `development-regression-results.json` 是调整后的开发回归输出，不称为独立验收。
- `frozen-new-cases.json` 在运行前固定题目、教材参考要点和评分口径；由同一开发者准备并执行，只称“冻结后的新题验证”，不是严格独立盲测。
- `frozen-new-results.json` 是同一固定题组首次 keyword/vector 原始 API 回答、候选、`used_evidence`、模式和支持判断；未覆盖或重跑替换。
- `manual-scoring.json` 是逐题对照教材参考与实际证据后的语义评分，不以候选关键词或单元测试代替。

Top 3 预算并不相同：keyword 单位是知识点，vector 单位是去重教材来源片段，因此本轮不是公平检索对照实验。

## 实际结果

| 模式 | 题数 | 语义通过 | 误拒 | 误放 | 完整比较实际覆盖 | 缺维度比较正确拒答 |
|---|---:|---:|---:|---:|---:|---:|
| keyword | 8 | 7 | 1 | 0 | 1/1 | 1/1 |
| vector | 8 | 6 | 1 | 1 | 1/1 | 1/1 |

已修复原故障类型：范围外历史题和非历史题即使在 vector 下始终得到 Top K 近邻，也只保留为候选，不再进入回答，实际证据为空。完整比较题的实际证据覆盖双方；缺少所问维度的比较题正确拒答。

仍失败：

- `FN-02` 明显换问/别称在两种模式均误拒。keyword Top K 没有召回技术知识点；vector 已召回正确原文，但当前解释性门控未把该别称映射为教材主题。
- `FN-06` vector 对“北京人如何发明文字”发生误放。同人物近邻满足了当前通用 `process` 判断，但实际原文完全不支持“发明文字”。keyword 正确拒答。
- `FN-01`、`FN-05` 虽覆盖核心结论与限定词，但 fallback 仍会渲染部分同人物/同来源的无关原文，回答冗长；这是生成基线和主题粒度的剩余限制。

本轮真实使用本地缓存 `BAAI/bge-small-zh-v1.5`（revision `7999e1d3359715c523056ef9478215996d62a620`）、现有 35 条来源向量索引、HF/Transformers 离线模式和 TestClient API 链路。没有调用真实 LLM、ASR、TTS；没有完成正式 keyword/vector 公平对照实验，也没有复测真实语音链路。

## 浏览器人工验收准备

2026-10-22 检查时 `127.0.0.1:8000` 与 `5173` 均无监听进程，因此无需停止或复用服务。以下命令创建全新的 `tmp/support_assessment_acceptance_20261022_01.db`，不读取或写入原 65 条历史所在验收数据库。

后端 PowerShell：

```powershell
Set-Location D:\Graduation-Design\HistoryAI-System\backend
$env:DATABASE_URL = 'sqlite:///D:/Graduation-Design/HistoryAI-System/tmp/support_assessment_acceptance_20261022_01.db'
$env:KNOWLEDGE_MODE = 'textbook'
$env:RETRIEVAL_MODE = 'vector'
$env:EMBEDDING_MODEL = 'BAAI/bge-small-zh-v1.5'
$env:EMBEDDING_MODEL_REVISION = '7999e1d3359715c523056ef9478215996d62a620'
$env:VECTOR_INDEX_PATH = 'D:/Graduation-Design/HistoryAI-System/data/vector_index/textbook_bge_small_zh_v1_5.npz'
$env:HF_HOME = 'D:/Graduation-Design/HistoryAI-System/.cache/huggingface'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:AI_PROVIDER = 'disabled'
$env:AI_API_KEY = ''
$env:ASR_PROVIDER = 'disabled'
$env:ASR_API_KEY = ''
$env:TTS_PROVIDER = 'disabled'
$env:TTS_API_KEY = ''
.\.venv\Scripts\python.exe -c "from app.database import Base, engine; import app.models; Base.metadata.create_all(bind=engine)"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

不要加 `--reload`。首次加载本地模型可能需要数十秒；等待控制台显示服务启动后再提问。

前端 PowerShell：

```powershell
Set-Location D:\Graduation-Design\HistoryAI-System\frontend
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000/api'
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

建议人工题与检查点：

1. `元谋人和蓝田人的发现地点与年代有何不同？`：回答与 `used_evidence` 必须覆盖双方及地点、年代。
2. `北京人与山顶洞人的迁徙原因有什么不同？`：应拒答，候选可保留，`used_evidence=[]`。
3. `能否确定陶寺古城就是尧都？`：必须保留“有学者推论”“很有可能”，不能写成已证实。
4. `汉武帝推恩令有什么作用？`：vector 可显示近邻，但不得采用为证据或作答。
5. `北京人如何发明文字？`：当前已知 vector 误放，用于人工确认剩余缺陷，不应记录为通过。

页面没有新增诊断界面；`retrieval_mode`、`answer_mode`、`support_assessment` 和 `used_evidence` 请在浏览器开发者工具的 `/api/question` 响应中核对。

切回 keyword：停止后端，在同一后端 PowerShell 中执行 `$env:RETRIEVAL_MODE='keyword'`，再用同一条、不带 `--reload` 的 Uvicorn 命令重启。keyword 不加载 Embedding 模型。
