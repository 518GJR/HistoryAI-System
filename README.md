# 面向中小学历史知识点的语音驱动问答与知识梳理系统

## 项目介绍

本项目是一个毕业设计项目，目标是构建面向中小学历史知识点的智能问答与知识梳理系统。当前版本为 **v0.5.5**，已完成基础前后端结构、数据库模型、历史知识 RAG 检索、问答接口、问答历史保存与查询接口、前端聊天页面和前端历史问答展示。

当前系统支持用户在前端输入历史问题，后端检索历史知识库并生成结构化回答，同时保存问答历史。前端会展示当前聊天内容和最近 20 条历史问答。

## 技术架构

- 后端：Python + FastAPI
- 前端：Vue3 + Vite
- 数据库：MySQL
- ORM：SQLAlchemy
- 环境变量：python-dotenv
- 测试框架：pytest
- 预留模块：AI 问答服务、RAG 知识库检索服务、语音识别与语音合成服务

## 项目结构

```text
HistoryAI-System/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── init_db.py
│   │   ├── api/
│   │   │   ├── user.py
│   │   │   └── question.py
│   │   ├── scripts/
│   │   │   ├── __init__.py
│   │   │   └── import_history_knowledge.py
│   │   └── services/
│   │       ├── ai_service.py
│   │       ├── rag_service.py
│   │       └── speech_service.py
│   ├── tests/
│   │   ├── test_rag_service.py
│   │   └── test_question_api.py
│   └── requirements.txt
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── index.html
│   └── src/
│       ├── main.js
│       ├── App.vue
│       └── style.css
├── data/
│   └── history_knowledge.json
├── README.md
└── PROJECT_STATUS.md
```

## 已实现功能

- FastAPI 后端服务入口
- Vue3 + Vite 前端页面
- MySQL 数据库连接配置
- `User` 用户模型
- `HistoryKnowledge` 历史知识模型
- `QuestionHistory` 问答历史模型
- 数据库初始化脚本：`backend/app/init_db.py`
- 历史知识 JSON 导入 MySQL 脚本：`backend/app/scripts/import_history_knowledge.py`
- 历史问答接口：`POST /api/question`
- 问答历史查询接口：`GET /api/question/history`
- RAG 历史知识检索
- RAG 检索结果 Top 3 返回
- 问答接口返回知识来源 `sources`
- 问答接口自动保存用户问题、系统回答和来源快照
- 前端聊天页面展示用户问题、AI 回答和知识来源
- 前端历史问答区域展示最近 20 条历史记录
- 前端历史记录展示问题、回答摘要、创建时间和来源数量
- 桌面端聊天区和历史区左右布局
- 移动端聊天区和历史区上下布局
- RAG 与问答接口自动化测试

## 后端运行

进入后端目录：

```bash
cd HistoryAI-System/backend
```

创建并激活 Python 虚拟环境：

```bash
python -m venv .venv
```

Windows PowerShell：

```bash
.\.venv\Scripts\Activate.ps1
```

安装依赖：

```bash
pip install -r requirements.txt
```

配置环境变量：

```bash
copy ..\.env.example ..\.env
```

根据本地 MySQL 配置修改项目根目录下的 `.env`：

```text
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/history_ai?charset=utf8mb4
```

启动 FastAPI 服务：

```bash
uvicorn app.main:app --reload
```

后端默认地址：

```text
http://localhost:8000
```

接口文档地址：

```text
http://localhost:8000/docs
```

## 数据库配置

运行前请先在 MySQL 中创建数据库：

```sql
CREATE DATABASE history_ai DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

初始化数据表：

```bash
cd HistoryAI-System/backend
python -m app.init_db
```

导入历史知识 JSON：

```bash
cd HistoryAI-System/backend
python -m app.scripts.import_history_knowledge
```

`backend/app/init_db.py` 用于根据当前 SQLAlchemy 模型创建数据表。`backend/app/scripts/import_history_knowledge.py` 用于把 `data/history_knowledge.json` 导入 MySQL 的 `history_knowledge` 表。

## API 说明

### 历史问答接口

```text
POST /api/question
```

请求示例：

```json
{
  "question": "秦始皇为什么统一六国？"
}
```

响应示例：

```json
{
  "answer": "你提出的问题是：秦始皇为什么统一六国？...",
  "sources": [
    {
      "title": "秦始皇统一六国",
      "dynasty": "秦朝",
      "score": 17
    }
  ]
}
```

说明：

- 接口会先调用 RAG 检索历史知识。
- 然后根据命中的知识点生成回答。
- 最后自动保存问答历史到 `question_history` 表。
- 返回格式保持 `answer` 和 `sources`，兼容前端聊天页面。

### 问答历史查询接口

```text
GET /api/question/history?limit=20
```

响应示例：

```json
{
  "histories": [
    {
      "id": 1,
      "user_id": null,
      "question": "秦始皇为什么统一六国？",
      "answer": "你提出的问题是：秦始皇为什么统一六国？...",
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

说明：

- 默认返回最近 20 条历史记录。
- 支持 `limit` 参数。
- 当前无登录系统，不按 `user_id` 过滤。
- `sources` 返回列表格式。

## 当前问答流程

```text
用户问题
-> POST /api/question
-> rag_service.py 优先读取 MySQL 历史知识数据
-> 数据库失败或无数据时回退 data/history_knowledge.json
-> 按标题、关键词、朝代、人物、事件、原因、影响、正文等字段加权检索
-> 返回 Top 3 相关知识点和命中分数
-> ai_service.py 将命中的历史知识整理为回答
-> 保存 question_history
-> 返回 answer 和 sources
-> 前端展示聊天内容并刷新历史记录
```

## 前端运行

进入前端目录：

```bash
cd HistoryAI-System/frontend
```

安装依赖：

```bash
npm install
```

启动开发服务：

```bash
npm run dev
```

前端默认地址：

```text
http://localhost:5173
```

构建前端：

```bash
npm run build
```

## 前端历史记录展示

v0.5.5 已在前端增加历史问答展示区域：

- 页面加载时调用 `GET /api/question/history?limit=20`
- 展示最近 20 条问答历史
- 每条历史显示：
  - 用户问题
  - AI 回答摘要
  - 创建时间
  - 来源数量
- 发送新问题并成功获得回答后自动刷新历史列表
- 桌面端为聊天区和历史区左右布局
- 移动端为上下布局

## 测试

当前测试覆盖：

- RAG 正常知识命中
- RAG 多知识点排序和 Top 3 返回
- RAG 无匹配问题
- `/api/question` 接口正常命中
- `/api/question` 接口多来源排序
- `/api/question` 接口无匹配提示
- `/api/question/history` 返回历史列表
- POST 后可通过 GET 查询到历史记录

运行方式：

```bash
cd HistoryAI-System/backend
python -m pytest tests
```

## 下一步开发建议

1. 优化历史记录交互，支持点击历史记录查看完整问答。
2. 增加问答历史删除、清空、分页和按用户筛选能力。
3. 完善用户模块，增加注册、登录、鉴权和用户级历史记录。
4. 优化 RAG 检索策略，支持分词、同义词和更准确的排序。
5. 接入大模型 API，将检索到的知识点和用户问题组合成提示词。
6. 添加语音能力，在 `speech_service.py` 中实现语音转文字和文字转语音，并新增上传音频接口。

## v0.5.5：前端历史问答展示

本阶段在已完成问答历史保存和查询接口的基础上，补充前端历史展示能力。用户可以在聊天页面右侧看到最近 20 条问答历史，发送新问题后历史列表会自动刷新。

修改文件：

- `frontend/src/App.vue`
- `frontend/src/style.css`
- `README.md`
- `PROJECT_STATUS.md`

验证结果：

- 前端 `npm run build` 构建通过。
- 本次文档同步仅修改 `README.md` 和 `PROJECT_STATUS.md`。
