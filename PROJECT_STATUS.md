# PROJECT_STATUS.md

## 1. 项目名称

面向中小学历史知识点的语音驱动问答与知识梳理系统

项目目录：`HistoryAI-System`

## 2. 项目目标

本项目用于毕业设计，目标是构建一个面向中小学历史学习场景的智能系统，支持用户通过文本或语音提出历史问题，系统结合历史知识库进行检索、问答和知识梳理。

当前阶段版本为 v0.5.1，已在 v0.4 问答闭环和测试覆盖的基础上，完成 v0.5 第一阶段数据库基础建设，并同步整理项目文档。当前问答主链路仍使用本地 JSON 知识库检索，数据库初始化和 JSON 导入 MySQL 脚本已补充，后续将切换为优先 MySQL、失败或无数据时回退 JSON 的检索流程。

## 3. 当前技术栈

- 后端：Python + FastAPI
- 前端：Vue3 + Vite
- 数据库：MySQL
- ORM：SQLAlchemy
- 接口数据校验：Pydantic
- 环境变量管理：python-dotenv
- 测试框架：pytest
- 后端服务运行：Uvicorn
- 预留能力：AI 问答、RAG 知识库检索、语音识别、语音合成

## 4. 已完成任务

- 创建项目根目录 `HistoryAI-System`
- 创建后端目录 `backend`
- 创建前端目录 `frontend`
- 创建数据目录 `data`
- 搭建 FastAPI 后端应用入口
- 添加基础跨域配置
- 添加用户模块测试路由
- 添加历史问答接口 `POST /api/question`
- 创建 MySQL 数据库连接配置
- 创建 SQLAlchemy 基础模型
- 创建用户表模型 `User`
- 创建历史知识表模型 `HistoryKnowledge`
- 创建 Pydantic 请求和响应模型
- 创建 AI、RAG、语音服务占位模块
- 创建 Vue3 简单聊天页面
- 创建历史知识示例数据文件
- 创建项目说明文档 `README.md`
- 创建项目状态记录文件 `PROJECT_STATUS.md`
- 创建 `.gitignore`
- 创建 `.env` 和 `.env.example`
- 将数据库连接配置改为从环境变量读取
- 实现基于 `data/history_knowledge.json` 的关键词检索
- 将问答接口改为“知识检索 + 回答生成”的第一版闭环
- 补充 Vite 配置，支持 Vue 单文件组件生产构建
- 扩展历史知识 JSON 数据结构，增加时间、人物、事件、原因、影响等字段
- 实现 RAG 加权评分机制
- RAG 检索返回 Top 3 相关知识点
- 问答接口返回 `sources` 知识来源
- 前端聊天页面展示知识来源和命中分数
- 扩充历史知识库，覆盖中国古代史、中国近现代史和世界史常见知识点
- 添加 RAG 检索函数测试
- 添加 `/api/question` 问答接口测试
- 测试覆盖正常命中、多知识点排序和无匹配问题
- 完善 `HistoryKnowledge` 数据库模型，补齐结构化历史知识字段
- 创建问答历史表模型 `QuestionHistory`
- 创建数据库初始化脚本 `backend/app/init_db.py`
- 创建 JSON 导入 MySQL 脚本 `backend/app/scripts/import_history_knowledge.py`
- 完成 v0.5.1 文档同步整理，修正版本和任务状态说明

## 5. 当前文件结构

以下结构只记录项目源码和核心文件，不包含 `.venv`、`__pycache__` 等本地环境或缓存文件。

```text
HistoryAI-System/
├── README.md
├── PROJECT_STATUS.md
├── backend/
│   ├── requirements.txt
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── database.py
│       ├── models.py
│       ├── schemas.py
│       ├── init_db.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── user.py
│       │   └── question.py
│       ├── scripts/
│       │   ├── __init__.py
│       │   └── import_history_knowledge.py
│       └── services/
│           ├── __init__.py
│           ├── ai_service.py
│           ├── rag_service.py
│           └── speech_service.py
│   └── tests/
│       ├── test_rag_service.py
│       └── test_question_api.py
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── App.vue
│       └── style.css
└── data/
    └── history_knowledge.json
```

## 6. 已实现功能

- 后端根路径健康检查：`GET /`
- 用户模块测试接口：`GET /api/user/ping`
- 历史问答接口：`POST /api/question`
- 历史知识检索：基于本地 JSON 文件按标题、关键词、朝代、人物、事件、原因、影响等字段加权匹配
- 检索结果：返回 Top 3 相关知识点和命中分数
- 历史知识库：覆盖中国古代史、中国近现代史和世界史常见考点
- 自动化测试：
  - RAG 正常知识命中
  - RAG 多知识点排序和 Top 3 返回
  - RAG 无匹配问题
  - `/api/question` 正常命中
  - `/api/question` 多来源排序
  - `/api/question` 无匹配提示
- 问答接口请求格式：

```json
{
  "question": "秦始皇为什么统一六国？"
}
```

- 问答接口响应格式：

```json
{
  "answer": "...",
  "sources": [
    {
      "title": "秦始皇统一六国",
      "dynasty": "秦朝",
      "score": 17
    }
  ]
}
```

- 前端聊天页面：
  - 输入历史问题
  - 点击发送按钮
  - 调用后端问答接口
  - 显示用户问题和 AI 回答
  - 展示命中的知识来源和分数

- 数据库基础能力：
  - 配置 MySQL 连接字符串
  - 定义用户表模型
  - 定义历史知识表模型
  - 定义问答历史表模型
  - 提供数据库初始化脚本 `backend/app/init_db.py`
  - 提供 JSON 导入 MySQL 脚本 `backend/app/scripts/import_history_knowledge.py`

## 7. 未完成任务

- 尚未实现真实大模型问答
- 已实现第一版 JSON 关键词检索，尚未实现向量检索或分词检索
- 已创建 `data/history_knowledge.json` 导入 MySQL 脚本，尚未接入问答主链路
- 已创建数据库初始化脚本，尚未引入 Alembic 迁移方案
- 尚未实现用户注册、登录和鉴权
- 已创建问答历史表模型，尚未实现问答历史保存和查询接口
- 尚未实现语音转文字
- 尚未实现文字转语音
- 尚未实现知识点结构化梳理页面
- 已添加第一版 RAG 单元测试和问答接口测试
- `.gitignore` 已配置
- `.env` 和 `.env.example` 已配置

## 8. 下一步开发计划

1. 在确认 MySQL 环境可用后运行 `python -m app.init_db` 创建数据表。
2. 运行 `python -m app.scripts.import_history_knowledge` 导入历史知识数据。
3. 将 RAG 数据读取改为优先 MySQL，失败或无数据时回退 `data/history_knowledge.json`。
4. 增加问答历史保存和查询接口。
5. 优化 RAG 检索，支持分词、同义词和更准确的相关性排序。
6. 接入大模型 API，基于“用户问题 + 检索知识点”生成自然语言回答。
7. 前端增加历史记录视图和更清晰的知识来源展示。
8. 后续接入语音上传接口，实现语音转文字和文字转语音。

## 9. 开发记录更新要求

每次开发完成后都需要同步更新本文件，至少记录以下内容：

- 新增功能
- 修改文件
- 当前完成度
- 下一步计划
- 已知问题或风险

## 10. 本次开发记录

### 2026-07-10

新增功能：

- 新增项目状态记录文件 `PROJECT_STATUS.md`
- 梳理当前项目目标、技术栈、已完成任务、已实现功能和未完成任务
- 记录当前源码结构，排除本地虚拟环境和缓存目录
- 明确下一步 RAG、语音、数据库和前端开发计划

修改文件：

- `PROJECT_STATUS.md`

当前完成度：

- 项目基础骨架：已完成
- 后端基础接口：已完成
- 前端基础聊天页面：已完成
- 数据库模型定义：已完成
- RAG 知识库：未完成
- 语音功能：未完成
- 用户系统：未完成
- 综合完成度：约 20%

下一步计划：

- 优先添加 `.gitignore` 和 `.env` 配置
- 实现 MySQL 自动建表或迁移方案
- 实现历史知识数据导入
- 完成第一版关键词检索 RAG 问答流程

### 2026-07-11

新增功能：

- 新增 `.gitignore`，忽略 Python 虚拟环境、缓存文件、Node 依赖和前端构建产物
- 新增 `.env` 和 `.env.example`
- 使用 `python-dotenv` 从 `.env` 读取 `DATABASE_URL`
- 完善 `rag_service.py`，读取 `data/history_knowledge.json`
- 实现第一版关键词检索，支持按标题、朝代和关键词匹配历史知识
- 修改 `ai_service.py`，根据检索到的知识点生成回答
- 修改 `/api/question` 流程，实现“用户问题 -> RAG 检索 -> 回答生成”
- 新增 `frontend/vite.config.js`，启用 Vue 单文件组件构建

修改文件：

- `.gitignore`
- `.env`
- `.env.example`
- `README.md`
- `PROJECT_STATUS.md`
- `backend/requirements.txt`
- `backend/app/database.py`
- `backend/app/api/question.py`
- `backend/app/services/rag_service.py`
- `backend/app/services/ai_service.py`
- `frontend/vite.config.js`
- `frontend/package-lock.json`

验证结果：

- 后端 Python 语法检查通过
- 后端 FastAPI 应用导入通过
- RAG 示例问题“秦始皇为什么统一六国？”可命中“秦始皇统一六国”
- 前端 `npm run build` 构建通过

当前完成度：

- 项目基础骨架：已完成
- 后端基础接口：已完成
- 前端基础聊天页面：已完成
- 数据库模型定义：已完成
- 环境变量配置：已完成
- 第一版 JSON 关键词 RAG：已完成
- 第一版历史知识问答闭环：已完成
- 语音功能：未完成
- 用户系统：未完成
- 综合完成度：约 30%

下一步计划：

- 扩充历史知识 JSON 数据
- 实现 JSON 数据导入 MySQL
- 增加知识来源展示
- 优化检索算法，支持分词、同义词和相关性排序
- 接入大模型 API 生成更自然的学习型回答

### 2026-07-11 v0.3

新增功能：

- 优化 `data/history_knowledge.json` 数据结构，新增 `time`、`people`、`event`、`reason`、`impact` 字段
- 保留 `title`、`dynasty`、`keywords`、`content` 字段，兼容已有 RAG 检索和旧数据
- 修改 `rag_service.py`，实现按字段加权评分
- 标题匹配权重最高，关键词次之，朝代再次，同时支持人物、事件、原因、影响等字段匹配
- RAG 检索结果限制为 Top 3，并返回 `score` 命中分数
- 修改问答响应结构，新增 `sources` 知识来源字段
- 前端聊天页面展示知识来源标题、朝代和分数
- 回答内容按“事件、原因、影响、补充说明”组织，更适合中小学历史学习

修改文件：

- `data/history_knowledge.json`
- `backend/app/schemas.py`
- `backend/app/api/question.py`
- `backend/app/services/rag_service.py`
- `backend/app/services/ai_service.py`
- `frontend/src/App.vue`
- `frontend/src/style.css`
- `README.md`
- `PROJECT_STATUS.md`

当前版本：

- v0.3：历史知识问答体验增强版

下一步计划：

- 扩充历史知识数据，增加中国古代史、近代史和世界史常见考点
- 添加接口测试，覆盖 RAG 命中、无命中和 Top 3 排序
- 实现 JSON 数据导入 MySQL
- 增加问答历史记录表和保存接口
- 后续接入语音识别和语音合成能力

### 2026-07-11 v0.4

新增功能：

- 扩充 `data/history_knowledge.json` 历史知识库
- 新增中国古代史知识点：商鞅变法、唐太宗贞观之治、郑和下西洋
- 新增中国近现代史知识点：鸦片战争、洋务运动、辛亥革命、五四运动、新中国成立
- 新增世界史知识点：文艺复兴、新航路开辟、英国资产阶级革命、法国大革命、第一次工业革命
- 保持所有知识点字段格式一致：`title`、`dynasty`、`time`、`people`、`event`、`reason`、`impact`、`keywords`、`content`
- 新增 `backend/tests/test_rag_service.py`
- 新增 `backend/tests/test_question_api.py`
- 新增 pytest 测试依赖和 FastAPI 测试客户端依赖

修改文件：

- `data/history_knowledge.json`
- `backend/requirements.txt`
- `backend/tests/test_rag_service.py`
- `backend/tests/test_question_api.py`
- `README.md`
- `PROJECT_STATUS.md`

测试结果：

- JSON 格式校验通过
- 前端 `npm run build` 构建通过
- pytest 测试输出显示 6 个用例全部通过
- 本轮测试覆盖：正常知识命中、多知识点排序、无匹配问题、`/api/question` 接口命中、接口多来源排序、接口无匹配提示

当前版本：

- v0.4：历史知识库扩充与测试增强版

当前完成度：

- 项目基础骨架：已完成
- 后端基础接口：已完成
- 前端基础聊天页面：已完成
- 数据库模型定义：已完成
- 环境变量配置：已完成
- 第一版 JSON 关键词 RAG：已完成
- 第一版历史知识问答闭环：已完成
- 知识来源展示：已完成
- 历史知识库扩充：已完成
- 第一版测试覆盖：已完成
- 语音功能：未完成
- 用户系统：未完成
- 综合完成度：约 40%

下一步计划：

- v0.5 优先实现数据库初始化和历史知识导入 MySQL
- 增加问答历史记录表，保存用户问题、回答和来源知识点
- 增加历史记录查询接口
- 前端增加历史记录展示区域
- 后续再接入分词检索、大模型 API 和语音能力

### 2026-07-12 v0.5 第一阶段

新增功能：
- 完善 `HistoryKnowledge` 数据库模型，补齐 `time`、`people`、`event`、`reason`、`impact`、`updated_at` 字段。
- 新增 `QuestionHistory` 数据库模型，为后续问答历史记录保存做准备。
- 新增数据库初始化脚本 `backend/app/init_db.py`。
- 新增 JSON 导入 MySQL 脚本 `backend/app/scripts/import_history_knowledge.py`。
- 保留 `data/history_knowledge.json` 作为 v0.4 问答流程的备用知识库，当前未修改问答接口、RAG 服务和前端页面。

修改文件：
- `backend/app/models.py`
- `backend/app/init_db.py`
- `backend/app/scripts/__init__.py`
- `backend/app/scripts/import_history_knowledge.py`
- `README.md`
- `PROJECT_STATUS.md`

验证结果：
- Python 语法检查通过。
- 数据库模型导入检查通过。
- v0.4 问答主链路文件未修改。

当前完成度：
- v0.5 数据库基础建设：已完成第一阶段。
- MySQL 建表脚本：已完成。
- JSON 导入 MySQL 脚本：已完成。
- RAG 切换数据库检索：未开始，下一阶段处理。
- 问答历史接口与前端展示：未开始，后续阶段处理。

下一步计划：
- 在确认 MySQL 环境可用后运行 `python -m app.init_db` 创建数据表。
- 运行 `python -m app.scripts.import_history_knowledge` 导入历史知识。
- v0.5 第二阶段将 RAG 数据读取改为优先 MySQL、失败或无数据时回退 JSON。
- v0.5 第三阶段实现问答历史保存和查询接口。

### 2026-07-12 v0.5.1 文档同步整理

新增功能：
- 同步当前版本说明为 v0.5.1。
- 补充 `backend/app/init_db.py` 数据库初始化脚本说明。
- 补充 `backend/app/scripts/import_history_knowledge.py` JSON 导入 MySQL 脚本说明。
- 修正已完成但仍标记未完成的数据库初始化、JSON 导入脚本和问答历史模型相关任务状态。

修改文件：
- `PROJECT_STATUS.md`
- `README.md`

验证结果：
- 本次仅修改文档，不修改 `backend/app/api/question.py`。
- 本次仅修改文档，不修改 `backend/app/services/rag_service.py`。
- 本次仅修改文档，不修改前端文件。

当前版本：
- v0.5.1：文档同步整理版。

下一步计划：
- 确认 MySQL 环境可用后运行数据库初始化和 JSON 导入脚本。
- v0.5 第二阶段将 RAG 数据读取改为优先 MySQL，失败或无数据时回退 JSON。
- v0.5 第三阶段实现问答历史保存和查询接口。