# PROJECT_STATUS.md

## 1. 项目名称

面向中小学历史知识点的语音驱动问答与知识梳理系统

项目目录：`HistoryAI-System`

## 2. 项目目标

本项目用于毕业设计，目标是构建一个面向中小学历史学习场景的智能系统，支持用户通过文本或语音提出历史问题，系统结合历史知识库进行检索、问答和知识梳理。

当前阶段版本为 **v0.5.5**。项目已完成基础前后端结构、MySQL 数据库模型、历史知识 RAG 检索、问答接口、问答历史保存与查询接口，以及前端历史问答展示。当前问答主链路支持优先读取 MySQL 历史知识数据，失败或无数据时回退本地 `data/history_knowledge.json`。

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

## 4. 已完成功能

- 创建项目基础目录：`backend`、`frontend`、`data`
- 搭建 FastAPI 后端应用入口
- 添加基础跨域配置
- 添加用户模块测试路由：`GET /api/user/ping`
- 添加历史问答接口：`POST /api/question`
- 添加问答历史查询接口：`GET /api/question/history`
- 创建 MySQL 数据库连接配置
- 创建 SQLAlchemy 基础模型
- 创建用户表模型：`User`
- 创建历史知识表模型：`HistoryKnowledge`
- 创建问答历史表模型：`QuestionHistory`
- 创建 Pydantic 请求和响应模型
- 创建 AI、RAG、语音服务占位模块
- 创建 Vue3 聊天页面
- 创建历史知识示例数据文件：`data/history_knowledge.json`
- 创建 `.gitignore`、`.env` 和 `.env.example`
- 使用环境变量读取数据库连接配置
- 实现基于历史知识数据的关键词检索
- 实现“用户问题 -> RAG 检索 -> 回答生成”的第一版问答闭环
- 实现 RAG 加权评分机制
- RAG 检索返回 Top 3 相关知识点和命中分数
- 问答接口返回 `sources` 知识来源
- 问答接口自动保存问题、回答和来源快照到 `question_history`
- 问答历史查询接口默认返回最近 20 条历史记录
- 前端聊天页面展示用户问题、AI 回答、知识来源和命中分数
- 前端新增历史问答展示区域，展示最近 20 条问答历史
- 前端发送问题成功后自动刷新历史记录
- 扩充历史知识库，覆盖中国古代史、中国近现代史和世界史常见知识点
- 添加 RAG 检索函数测试
- 添加 `/api/question` 问答接口测试
- 添加问答历史查询接口测试
- 创建数据库初始化脚本：`backend/app/init_db.py`
- 创建 JSON 导入 MySQL 脚本：`backend/app/scripts/import_history_knowledge.py`

## 5. 当前文件结构

以下结构只记录项目源码和核心文件，不包含 `.venv`、`__pycache__`、`node_modules`、`dist` 等本地环境、缓存或构建产物。

```text
HistoryAI-System/
├── README.md
├── PROJECT_STATUS.md
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── init_db.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   └── question.py
│   │   ├── scripts/
│   │   │   ├── __init__.py
│   │   │   └── import_history_knowledge.py
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── ai_service.py
│   │       ├── rag_service.py
│   │       └── speech_service.py
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

## 6. 已实现接口与页面

### 后端接口

- `GET /`：后端健康检查
- `GET /api/user/ping`：用户模块测试接口
- `POST /api/question`：历史问答接口
- `GET /api/question/history`：问答历史查询接口

### 问答接口请求示例

```json
{
  "question": "秦始皇为什么统一六国？"
}
```

### 问答接口响应示例

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

### 历史查询接口响应示例

```json
{
  "histories": [
    {
      "id": 1,
      "user_id": null,
      "question": "秦始皇为什么统一六国？",
      "answer": "...",
      "sources": [
        {
          "title": "秦始皇统一六国",
          "dynasty": "秦朝",
          "score": 17
        }
      ],
      "created_at": "2026-07-13T20:30:00"
    }
  ]
}
```

### 前端页面

- 输入历史问题
- 点击发送按钮
- 调用后端问答接口
- 展示用户问题和 AI 回答
- 展示命中的知识来源和分数
- 页面右侧展示最近 20 条历史问答
- 历史记录显示用户问题、AI 回答摘要、创建时间和来源数量
- 移动端改为聊天区和历史区上下布局

## 7. 当前完成状态

- 项目基础骨架：已完成
- 后端基础接口：已完成
- 前端基础聊天页面：已完成
- 数据库模型定义：已完成
- 环境变量配置：已完成
- 第一版 RAG 检索：已完成
- 第一版历史知识问答闭环：已完成
- 知识来源展示：已完成
- 历史知识库扩充：已完成
- 数据库初始化脚本：已完成
- JSON 导入 MySQL 脚本：已完成
- 问答历史保存：已完成
- 问答历史查询接口：已完成
- 前端历史问答展示：已完成
- 自动化测试覆盖：已完成第一版
- 真实大模型问答：未完成
- 用户注册、登录和鉴权：未完成
- 语音转文字：未完成
- 文字转语音：未完成
- 知识点结构化梳理页面：未完成

综合完成度：约 55%

## 8. 下一阶段计划

1. 优化问答历史体验，支持点击历史记录回填或查看完整历史详情。
2. 为问答历史增加删除、清空、分页或按用户筛选能力。
3. 完善用户注册、登录和鉴权，将问答历史绑定到具体用户。
4. 优化 RAG 检索策略，支持分词、同义词和更准确的相关性排序。
5. 接入大模型 API，基于“用户问题 + 检索知识点”生成更自然的学习型回答。
6. 增加语音上传接口，实现语音转文字和文字转语音。
7. 设计知识点结构化梳理页面，支持历史事件、人物、时间线和影响关系展示。
8. 引入 Alembic 等数据库迁移方案，替代直接 `create_all` 的初始化方式。

## 9. 开发记录更新要求

每次开发完成后都需要同步更新本文档，至少记录：

- 新增功能
- 修改文件
- 当前完成度
- 下一步计划
- 已知问题或风险

## 10. 本次开发记录

### 2026-07-13 v0.5.5 前端历史问答展示

新增功能：

- 前端页面新增历史问答展示区域。
- 页面加载时调用 `GET /api/question/history?limit=20` 获取最近 20 条问答历史。
- 发送问题并成功获得回答后，自动刷新历史列表。
- 历史卡片展示用户问题、AI 回答摘要、创建时间和来源数量。
- 桌面端采用聊天区和历史区左右布局。
- 移动端采用聊天区和历史区上下布局。

修改文件：

- `frontend/src/App.vue`
- `frontend/src/style.css`
- `README.md`
- `PROJECT_STATUS.md`

验证结果：

- 前端 `npm run build` 构建通过。
- 本次文档同步仅修改 `README.md` 和 `PROJECT_STATUS.md`。

当前版本：

- v0.5.5：前端历史问答展示版本。

当前完成度：

- 问答主链路：已完成第一版
- 问答历史保存：已完成
- 问答历史查询：已完成
- 前端历史展示：已完成
- 综合完成度：约 55%

下一步计划：

- 优化历史记录交互，例如点击历史记录查看完整问答。
- 增加用户系统后，将历史记录与用户账号关联。
- 继续优化 RAG 检索和回答生成质量。
