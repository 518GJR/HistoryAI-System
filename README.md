# HistoryAI-System

面向中小学历史知识点的语音驱动问答与知识梳理系统。当前核心架构版本为 **v0.6.0**。

五册新修订人教社统编初中历史教材是总体建设目标，包括七、八年级上下册和九年级上册，九年级下册不纳入。首个实现与验收范围是七年级上册第 1—3 课；五册目标不代表已经完成，也不是当前阶段的前置条件。

本文用于项目介绍、当前能力和运行入口。验证证据与缺口见 [PROJECT_STATUS.md](PROJECT_STATUS.md)，范围、阶段和验收条件见 [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)。

## 当前状态

### 已实现

- 文字问答：问题 → 本地/MySQL RAG → 外部大模型 → `answer + sources`
- 大模型不可用、未配置或响应异常时，自动回退原有知识模板回答
- ASR：浏览器录音上传 → 后端转写 → 识别文字回填，用户可修改
- TTS：AI 回答 → 后端合成音频字节流 → 前端自动播放/手动重试
- 语音闭环：录音 → ASR → 修改文字 → 提问 → RAG → AI 回答 → sources → TTS
- 基础知识梳理：主题、时间、人物、事件、原因、内容/经过、结果/影响、相关知识点
- 问答历史保存和最近 20 条记录展示；历史侧边栏独立滚动、只显示问题名称，长问题省略并可悬停查看全文
- 点击历史问题只读取已保存的问题、回答、来源和实际采用证据，不重新调用问答或语音服务；“新建对话”只重置前端当前视图，不删除历史
- 当前历史记录尚未关联真实用户
- 历史记录写入失败时仍返回已经生成的答案，并返回 `history_saved=false`
- 七上第 1—3 课教材库：48 个稳定知识点 ID、35 个可复用原文来源片段，以及册/单元/课/小标题/材料类型/教材页码/PDF 页序/限定词等字段
- `KNOWLEDGE_MODE=textbook` 仅加载教材 JSON；`KNOWLEDGE_MODE=demo` 保留 MySQL 优先、15 条演示 JSON 回退行为
- 教材来源元数据随检索结果进入问答 API、知识梳理、历史来源快照和前端展示
- AI、ASR、TTS 使用环境变量配置，不在代码中硬编码 API Key

### 数据与验证边界

- 当前 `data/history_knowledge.json` 包含 15 条通用演示数据，不是正式教材数据
- 演示数据继续保留；教材数据位于 `data/textbook_history_knowledge.json`，两者由运行模式隔离
- 教材数据依据已确认的 48 主题清单整理，并以本地教材 PDF 核对教材第 4—19 页（PDF 页序 9—24）；PDF 只作本地核对且已加入 Git 忽略
- AI、ASR、TTS 外部 HTTP 调用：已使用 `httpx.MockTransport` 完成 Mock 自动测试
- RAG、知识梳理、问答/语音 API、数据库写入失败降级：本轮自动测试通过
- 本轮测试使用 Mock 外部服务和内存 SQLite，不代表真实 MySQL 或外部服务本轮通过
- 用户此前确认2026-10-03完成真实联调；本轮未复测；仓库待补正式验收记录
- 浏览器麦克风端到端流程已有代码实现，本轮未进行浏览器复测
- 2026-10-21完成七上第1—3课30题修复前浏览器初评：26题通过、3题部分通过、1题失败，样本初评通过率为86.7%；该比例不是系统整体准确率
- 30题原题、参考要点、来源页码、评分口径和逐题修复前结果见[`docs/evaluation/2026-10-21-preliminary-30/`](docs/evaluation/2026-10-21-preliminary-30/)，教材PDF核对、第二人评分和生成路径截图核对仍待完成

功能测试通过、检索命中、模型回答正确、人工评分合格和真实服务联调通过是不同证据，不能混写。Mock 测试通过不等于本轮真实云服务验证通过。

## 技术栈

- 后端：Python、FastAPI、SQLAlchemy、MySQL
- 前端：Vue 3、Vite
- RAG：默认字段加权关键词 Top 3 基线；教材模式可显式切换为本地 BGE 语义向量 Top 3（按去重来源片段计数）
- 外部服务：OpenAI-compatible Chat Completions；OpenAI-compatible 或阿里云百炼 ASR/TTS
- 测试：pytest、FastAPI TestClient、httpx MockTransport

## 核心流程

```text
文字或录音
  → POST /api/speech/asr（录音时）
  → 可编辑问题文字
  → POST /api/question
  → RAG Top 3
  → 外部大模型基于检索资料生成回答
  → 失败时模板 fallback
  → answer + sources + knowledge_outline
  → 尝试保存历史（失败不阻塞回答）
  → POST /api/speech/tts
  → 浏览器播放音频
```

## 新增和现有 API

- `GET /`：健康检查
- `GET /api/user/ping`：原用户模块测试接口
- `POST /api/question`：RAG 历史问答
- `GET /api/question/history?limit=20`：问答历史
- `POST /api/speech/asr`：上传 multipart 音频，字段名 `audio`
- `POST /api/speech/tts`：提交 `{"text": "..."}`，返回音频
- `GET /api/knowledge/outline?topic=秦始皇统一六国`：结构化知识梳理

`POST /api/question` 主要响应字段：

```json
{
  "answer": "基于检索资料生成的回答",
  "sources": [
    {
      "title": "北京人用火",
      "dynasty": "史前时期",
      "score": 17,
      "knowledge_id": "H7A-L01-010",
      "book_title": "义务教育教科书·中国历史七年级上册",
      "lesson_number": 1,
      "lesson_title": "远古时期的人类活动",
      "section_title": "北京人",
      "textbook_pages": "6",
      "pdf_pages": "11",
      "source_refs": [{"source_id": "H7A-P006-B", "excerpt": "..."}]
    }
  ],
  "answer_mode": "ai",
  "history_saved": true,
  "knowledge_outline": {
    "topic": "秦始皇统一六国",
    "time": "公元前230年-公元前221年",
    "people": ["秦始皇", "商鞅"],
    "event": "...",
    "reason": "...",
    "process": "...",
    "result_impact": "...",
    "related_points": [],
    "sources": []
  }
}
```

`answer_mode` 为 `ai` 表示外部模型成功返回，为 `fallback` 表示使用本地模板。

## 配置

复制根目录环境变量示例：

```powershell
Copy-Item .env.example .env
```

必须按所选供应商填写：

- `AI_API_KEY`、`AI_MODEL`、`AI_BASE_URL`
- `ASR_API_KEY`、`ASR_MODEL`、`ASR_BASE_URL`
- `TTS_API_KEY`、`TTS_MODEL`、`TTS_BASE_URL`
- 可选：`TTS_VOICE`、`TTS_FORMAT`

知识库模式：

- `KNOWLEDGE_MODE=demo`：默认模式，MySQL 有数据时优先读取，否则回退原有 15 条演示 JSON。
- `KNOWLEDGE_MODE=textbook`：仅读取项目内 `data/textbook_history_knowledge.json`；文件缺失、格式错误或无匹配时都不会静默切换到演示库。

检索模式：

- `RETRIEVAL_MODE=keyword`：默认值，保留原字段加权知识点检索基线。
- `RETRIEVAL_MODE=vector`：仅支持 `KNOWLEDGE_MODE=textbook`，使用预先构建的本地来源片段向量索引；索引缺失、损坏或数据/模型/预处理版本不一致时明确报错，不回退 keyword。
- 问答响应的顶层 `retrieval_mode` 与每条来源的 `retrieval_mode`、`retrieval_unit` 会记录实际执行模式和计数单元。keyword 的 Top K 是知识点，vector 的 Top K 是去重来源片段，两者相同 K 不代表完全相同的证据预算。

### 本地教材向量索引

第一版使用 [`BAAI/bge-small-zh-v1.5`](https://huggingface.co/BAAI/bge-small-zh-v1.5)，固定修订 `7999e1d3359715c523056ef9478215996d62a620`。该模型为中文、24M 参数、512 维、MIT 许可证。查询按官方模型卡增加 `为这个句子生成表示以用于检索相关文章：` 前缀，文档不加该前缀；向量做 L2 归一化后以内积实现余弦排序。模型和索引仅保存在本机并由 Git 忽略，教材文本不会发送到付费接口或外部 Embedding 服务。

在 PowerShell 中使用项目虚拟环境显式建库（工作目录必须是 `backend`）：

```powershell
Set-Location D:\Graduation-Design\HistoryAI-System\backend
$env:HF_HOME = 'D:\Graduation-Design\HistoryAI-System\.cache\huggingface'
$env:HF_HUB_DISABLE_XET = '1'
$env:KNOWLEDGE_MODE = 'textbook'
$env:RETRIEVAL_MODE = 'vector'
$env:EMBEDDING_MODEL = 'BAAI/bge-small-zh-v1.5'
$env:EMBEDDING_MODEL_REVISION = '7999e1d3359715c523056ef9478215996d62a620'
$env:VECTOR_INDEX_PATH = 'data/vector_index/textbook_bge_small_zh_v1_5.npz'
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.scripts.build_textbook_vector_index
```

建库不是问答启动时的隐式操作。建库命令会校验 tokenizer 长度、向量数量/维度、有限值、非零范数和来源元数据，再原子替换索引。索引记录模型修订、数据 SHA-256、预处理规则、相似度、归一化、格式版本和 UTC 构建时间。

启动 vector 模式后端：

```powershell
Set-Location D:\Graduation-Design\HistoryAI-System\backend
$env:DATABASE_URL = 'sqlite:///D:/Graduation-Design/HistoryAI-System/tmp/acceptance_a_offline.db'
$env:HF_HOME = 'D:\Graduation-Design\HistoryAI-System\.cache\huggingface'
$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$env:KNOWLEDGE_MODE = 'textbook'
$env:RETRIEVAL_MODE = 'vector'
$env:EMBEDDING_MODEL = 'BAAI/bge-small-zh-v1.5'
$env:EMBEDDING_MODEL_REVISION = '7999e1d3359715c523056ef9478215996d62a620'
$env:VECTOR_INDEX_PATH = 'data/vector_index/textbook_bge_small_zh_v1_5.npz'
$env:AI_PROVIDER = 'disabled'
$env:ASR_PROVIDER = 'disabled'
$env:TTS_PROVIDER = 'disabled'
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

以上命令显式使用原 A 阶段验收 SQLite；专项测试必须改用独立测试数据库，不能写入该验收文件。`HF_HUB_OFFLINE=1` 和 `TRANSFORMERS_OFFLINE=1` 要求模型已存在于 `HF_HOME` 缓存，并阻止启动时联网补文件。实际模式可从问答响应的 `retrieval_mode` 核对，不能只根据进程环境变量推断。

切回稳定关键词模式只需设置 `$env:RETRIEVAL_MODE = 'keyword'` 并重启后端；keyword 模式不会导入或加载 Embedding 模型，也不要求索引存在。

离线复现真实检索结果（不调用问答模型、不写问答历史）：

```powershell
Set-Location D:\Graduation-Design\HistoryAI-System\backend
$env:HF_HOME = 'D:\Graduation-Design\HistoryAI-System\.cache\huggingface'
$env:HF_HUB_OFFLINE = '1'
$env:KNOWLEDGE_MODE = 'textbook'
$env:EMBEDDING_MODEL = 'BAAI/bge-small-zh-v1.5'
$env:EMBEDDING_MODEL_REVISION = '7999e1d3359715c523056ef9478215996d62a620'
$env:VECTOR_INDEX_PATH = 'data/vector_index/textbook_bge_small_zh_v1_5.npz'
$env:AI_PROVIDER = 'disabled'
$env:ASR_PROVIDER = 'disabled'
$env:TTS_PROVIDER = 'disabled'
.\.venv\Scripts\python.exe -m app.scripts.verify_textbook_retrieval --output ..\docs\evaluation\2026-10-22-vector-retrieval\real-retrieval-results.json
```

向量相似度只用于相对排序，不是答案正确概率，也没有在本轮校准成资料充分性阈值。范围外问题仍会返回最近邻，因此候选来源不能自动视为可回答依据。

AI 当前使用 `openai_compatible`。ASR/TTS 可使用 `openai_compatible` 或代码已支持的 `aliyun_bailian`，可以为三个能力配置同一家或不同供应商。API Key 只放在本地 `.env`，不要提交到 Git。

## 安装与启动

### 1. 数据库

创建 MySQL 数据库：

```sql
CREATE DATABASE history_ai DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

初始化现有表并导入演示知识：

```powershell
cd backend
python -m app.init_db
python -m app.scripts.import_history_knowledge
```

以上命令只针对演示数据。教材模式不需要把 48 个知识点导入数据库；在根目录 `.env` 设置 `KNOWLEDGE_MODE=textbook` 后，后端会按项目根目录定位并校验教材 JSON。问答历史仍使用现有数据库表；数据库不可用时，回答可返回但历史保存会标记失败。

### 2. 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

接口文档：<http://localhost:8000/docs>

### 3. 前端

```powershell
cd frontend
npm install
npm run dev
```

页面：<http://localhost:5173>

录音需要浏览器麦克风权限；localhost 可用于本地安全上下文。

## 老师检查演示顺序

1. 启动 MySQL，执行初始化和知识导入。
2. 在根目录 `.env` 配好真实 AI/ASR/TTS 服务。
3. 启动后端和前端，先在 `/docs` 查看四类核心 API。
4. 教材验收时设置 `KNOWLEDGE_MODE=textbook`，输入“北京人用火有什么作用？”演示文字问答、教材来源、知识梳理和 TTS；演示旧数据时改回 `demo` 并重启后端。
5. 点击“开始录音”，说出问题，停止录音；展示 ASR 回填文字并修改后发送。
6. 展示 AI 回答、来源、结构化梳理、音频播放和右侧历史记录。
7. 可临时将 `AI_PROVIDER=disabled` 并重启后端，演示模板 fallback（`answer_mode=fallback`）。

## 测试

```powershell
cd backend
python -m pytest tests -q

cd ..\frontend
npm run build
```

2026-10-15 A 阶段实际结果：`35 passed in 1.32s`；Vite 生产构建通过。测试使用 Mock 外部服务和内存 SQLite。

2026-10-21历史侧边栏与“新建对话”前端改动完成后，`npm run build`通过（Vite 6.4.3，10个模块转换），`git diff --check`通过。未修改后端，因此本轮未重复完整后端测试。独立滚动、历史点击、网络请求、忙碌禁用和窄屏表现仍需浏览器人工验收；真实MySQL时间语义也仍未验证。

2026-10-22第一版向量检索收尾后，新增 Mock 与 API 测试并执行完整后端离线回归：`64 passed in 2.18s`，退出码 0。测试显式禁用 AI、ASR、TTS 并阻断外部 HTTP；真实本地 Embedding 检索另行执行和记录，不能与 Mock 结果混写。本轮未修改前端，因此未重复前端生产构建。

## 后续范围

A 阶段的七上第 1—3 课教材数据和可追溯来源接入已完成代码与离线测试验证，30题修复前初评基线已经归档。第一版本地向量检索代码、真实索引和小规模检索验证已经完成；正式检索对照实验、教材约束自然语言生成、知识点标注、覆盖统计及小测掌握统计仍未完成。E20错误拒答和E10、E25、E26缺少直接回应的问题尚未修复，修复后复测必须单独保存，不覆盖基线。后续按 [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) 分阶段开展。
