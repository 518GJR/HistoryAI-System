# PROJECT_STATUS.md

## 1. 当前版本

- 项目：面向中小学历史知识点的语音驱动问答与知识梳理系统
- 版本：**v0.6.0 核心架构演示版**
- 日期：2026-09-27

## 2. 已实现

- 原有 Vue 文字问答和历史记录功能保留
- RAG 优先读取 MySQL，失败或无数据时回退本地 JSON
- RAG 按标题、关键词、朝代、人物、事件、原因、影响、正文加权并返回 Top 3
- 真实大模型调用代码：OpenAI-compatible `/chat/completions`
- 模型仅接收用户问题和检索资料，系统提示要求基于资料回答
- AI 未配置或失败时保留原模板 fallback
- 问答返回 `answer`、`sources`、`answer_mode`、`history_saved` 和 `knowledge_outline`
- 历史记录保存失败不会阻断答案返回
- ASR 接口：上传浏览器音频，调用 OpenAI-compatible `/audio/transcriptions`
- TTS 接口：提交回答文字，调用 OpenAI-compatible `/audio/speech` 并返回音频字节
- 前端完成录音、停止、上传、识别文字回填和修改
- 前端完成提问、来源展示、知识梳理、TTS 自动播放和手动重试
- 基础知识梳理包含：主题、时间、人物、事件、原因、内容/经过、结果/影响、相关知识点
- 所有 API Key、模型名、Base URL、超时、TTS voice/format 均从环境变量读取

## 3. 新增 API

- `POST /api/speech/asr`
- `POST /api/speech/tts`
- `GET /api/knowledge/outline?topic=...`

原有 API 继续保留：

- `POST /api/question`
- `GET /api/question/history`
- `GET /api/user/ping`
- `GET /`

## 4. 自动测试与构建

### 已通过

- 完整 pytest：**17 passed in 1.12s**
- 前端 `npm run build`：通过
- AI 成功响应和失败 fallback：MockTransport 通过
- ASR multipart 请求和识别响应：MockTransport 通过
- TTS 请求、voice 参数和音频响应：MockTransport 通过
- 未配置语音服务返回 503：通过
- 数据库保存失败仍返回答案：通过
- 知识梳理字段和问答内嵌梳理：通过
- 原有 RAG、问答、历史测试：继续通过

### 尚未验证

- 未使用真实 AI API Key 发起调用
- 未使用真实 ASR API Key/真实录音发起调用
- 未使用真实 TTS API Key播放供应商生成的音频
- 未完成浏览器麦克风到真实云服务的现场端到端验证

以上三种外部能力目前是“代码已实现 + Mock 测试通过”，不能表述为真实服务验证通过。

## 5. 本轮主要文件

### 上一会话遗留（接手时已存在）

- `backend/app/services/ai_service.py`：已加入外部模型调用雏形，但系统提示词损坏为问号
- `backend/app/api/question.py`：已改为返回生成模式，并尝试处理 SQLAlchemy 保存异常
- `backend/app/schemas.py`：已增加 `answer_mode`、`history_saved` 和问题长度限制
- `backend/app/services/provider_config.py`：未跟踪的环境变量配置模块
- `backend/tests/conftest.py`：未跟踪的外部网络隔离 fixture

### 本次完成/修改

- `backend/app/services/ai_service.py`
- `backend/app/services/provider_config.py`
- `backend/app/services/speech_service.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/api/question.py`
- `backend/app/api/speech.py`
- `backend/app/api/knowledge.py`
- `backend/app/schemas.py`
- `backend/app/main.py`
- `backend/tests/conftest.py`
- `backend/tests/test_ai_service.py`
- `backend/tests/test_speech_api.py`
- `backend/tests/test_knowledge_api.py`
- `backend/tests/test_question_api.py`
- `frontend/src/App.vue`
- `frontend/src/style.css`
- `.env.example`
- `README.md`
- `PROJECT_STATUS.md`

`backend/requirements.txt` 无需修改：所需的 `httpx` 和 `python-multipart` 已在原依赖中。

## 6. 配置要求

需要在根目录 `.env` 配置：

- `DATABASE_URL`
- AI：`AI_PROVIDER`、`AI_API_KEY`、`AI_MODEL`、`AI_BASE_URL`
- ASR：`ASR_PROVIDER`、`ASR_API_KEY`、`ASR_MODEL`、`ASR_BASE_URL`
- TTS：`TTS_PROVIDER`、`TTS_API_KEY`、`TTS_MODEL`、`TTS_BASE_URL`
- 可选：`TTS_VOICE`、`TTS_FORMAT`、各服务 `*_TIMEOUT`

Provider 必须设为 `openai_compatible` 才启用对应外部服务。默认 `disabled` 可安全运行文字问答 fallback。

## 7. 风险与后续

- 不同 OpenAI-compatible 供应商的模型名和音频参数可能不同，正式演示前必须真实联调
- 前端 TTS 会在回答后自动请求；浏览器禁止自动播放时仍可使用音频控件手动播放
- 当前 RAG 是轻量关键词加权，适合演示，不是高级向量检索
- 本轮按要求未做大规模评估、人工评分、登录注册、复杂知识图谱和部署
