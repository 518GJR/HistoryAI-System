# PROJECT_STATUS.md

## 1. 项目名称

面向中小学历史知识点的语音驱动问答与知识梳理系统

项目目录：`HistoryAI-System`

## 2. 项目目标

本项目用于毕业设计，目标是构建一个面向中小学历史学习场景的智能系统，支持用户通过文本或语音提出历史问题，系统结合历史知识库进行检索、问答和知识梳理。

当前阶段目标是完成第一版基础代码骨架，先保证前后端结构清晰、接口可扩展、数据库模型可继续演进，暂不实现复杂 AI 算法。

## 3. 当前技术栈

- 后端：Python + FastAPI
- 前端：Vue3 + Vite
- 数据库：MySQL
- ORM：SQLAlchemy
- 接口数据校验：Pydantic
- 环境变量管理：python-dotenv
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
│       ├── api/
│       │   ├── __init__.py
│       │   ├── user.py
│       │   └── question.py
│       └── services/
│           ├── __init__.py
│           ├── ai_service.py
│           ├── rag_service.py
│           └── speech_service.py
├── frontend/
│   ├── package.json
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
- 历史知识检索：基于本地 JSON 文件按标题、朝代和关键词匹配
- 问答接口请求格式：

```json
{
  "question": "秦始皇为什么统一六国？"
}
```

- 问答接口响应格式：

```json
{
  "answer": "..."
}
```

- 前端聊天页面：
  - 输入历史问题
  - 点击发送按钮
  - 调用后端问答接口
  - 显示用户问题和 AI 回答

- 数据库基础能力：
  - 配置 MySQL 连接字符串
  - 定义用户表模型
  - 定义历史知识表模型

## 7. 未完成任务

- 尚未实现真实大模型问答
- 已实现第一版 JSON 关键词检索，尚未实现向量检索或分词检索
- 尚未将 `data/history_knowledge.json` 自动导入 MySQL
- 尚未创建数据库迁移脚本
- 尚未实现用户注册、登录和鉴权
- 尚未实现问答历史记录
- 尚未实现语音转文字
- 尚未实现文字转语音
- 尚未实现知识点结构化梳理页面
- 尚未添加单元测试和接口测试
- 尚未配置 `.gitignore`
- 尚未配置环境变量文件 `.env`

## 8. 下一步开发计划

1. 扩充 `data/history_knowledge.json`，增加更多历史知识点。
2. 添加数据库初始化脚本或 Alembic 迁移。
3. 实现历史知识数据导入功能，把 `data/history_knowledge.json` 写入 MySQL。
4. 优化 RAG 检索，支持分词、同义词和更准确的相关性排序。
5. 接入大模型 API，基于“用户问题 + 检索知识点”生成自然语言回答。
6. 前端增加更清晰的知识来源展示、错误提示和问答记录展示。
7. 后续接入语音上传接口，实现语音转文字和文字转语音。

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
