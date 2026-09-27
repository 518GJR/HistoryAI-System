# HistoryAI-System

面向中小学历史知识点的语音驱动问答与知识梳理系统。当前核心架构版本为 **v0.6.0**。

## 当前状态

### 已实现

- 文字问答：问题 → 本地/MySQL RAG → 外部大模型 → `answer + sources`
- 大模型不可用、未配置或响应异常时，自动回退原有知识模板回答
- ASR：浏览器录音上传 → 后端转写 → 识别文字回填，用户可修改
- TTS：AI 回答 → 后端合成音频字节流 → 前端自动播放/手动重试
- 语音闭环：录音 → ASR → 修改文字 → 提问 → RAG → AI 回答 → sources → TTS
- 基础知识梳理：主题、时间、人物、事件、原因、内容/经过、结果/影响、相关知识点
- 问答历史保存和最近 20 条记录展示
- 历史记录写入失败时仍返回已经生成的答案，并返回 `history_saved=false`
- AI、ASR、TTS 使用环境变量配置，不在代码中硬编码 API Key

### 验证状态

- 自动化测试：**17 passed**
- AI、ASR、TTS 外部 HTTP 调用：已使用 `httpx.MockTransport` 完成 Mock 自动测试
- RAG、知识梳理、问答/语音 API、数据库写入失败降级：自动测试通过
- 前端：`npm run build` 通过
- 真实 AI 服务：**尚未验证**
- 真实 ASR 服务：**尚未验证**
- 真实 TTS 服务：**尚未验证**
- 浏览器真实麦克风端到端流程：代码已实现，需配置真实 ASR/TTS 后现场验证

Mock 测试通过不等于真实云服务已验证。不同供应商的 OpenAI-compatible 接口仍可能在模型名、音频格式或参数上存在差异。

## 技术栈

- 后端：Python、FastAPI、SQLAlchemy、MySQL
- 前端：Vue 3、Vite
- RAG：MySQL 优先，本地 `data/history_knowledge.json` 回退；字段加权 Top 3 检索
- 外部服务：OpenAI-compatible Chat Completions、Audio Transcriptions、Audio Speech
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
    {"title": "秦始皇统一六国", "dynasty": "秦朝", "score": 17}
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

填好后将对应的 `AI_PROVIDER`、`ASR_PROVIDER`、`TTS_PROVIDER` 改为 `openai_compatible`。可以为三个能力配置同一家或不同供应商。API Key 只放在本地 `.env`，不要提交到 Git。

## 安装与启动

### 1. 数据库

创建 MySQL 数据库：

```sql
CREATE DATABASE history_ai DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

初始化并导入知识：

```powershell
cd backend
python -m app.init_db
python -m app.scripts.import_history_knowledge
```

数据库不可用时，RAG 会回退本地 JSON；但历史列表会需要数据库。

### 2. 后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
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
4. 在前端先输入“秦始皇为什么统一六国？”演示文字问答、sources、知识梳理和 TTS。
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

当前结果：`17 passed`；Vite 生产构建通过。

## 本轮未做

本轮没有实现大规模题目评估、人工评分、登录注册、高级向量数据库、复杂知识图谱或部署。
