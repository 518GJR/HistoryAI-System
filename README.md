# 面向中小学历史知识点的语音驱动问答与知识梳理系统

## 项目介绍

本项目是一个毕业设计第一版代码骨架，目标是构建面向中小学历史知识点的智能问答与知识梳理系统。当前版本 v0.4 已完成基础前后端结构、数据库模型、问答接口、简单聊天页面、基于本地 JSON 历史知识库的关键词检索问答闭环、知识来源返回，以及 RAG 和问答接口测试。

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
│   │   ├── api/
│   │   │   ├── user.py
│   │   │   └── question.py
│   │   └── services/
│   │       ├── ai_service.py
│   │       ├── rag_service.py
│   │       └── speech_service.py
│   ├── tests/
│   │   ├── test_rag_service.py
│   │   └── test_question_api.py
│   └── requirements.txt
├── frontend/
├── data/
│   └── history_knowledge.json
└── README.md
```

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

然后根据本地 MySQL 配置修改项目根目录下的 `.env`：

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

问答接口：

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
  "answer": "你提出的问题是：秦始皇为什么统一六国？\n根据当前历史知识库，找到以下相关内容：...",
  "sources": [
    {
      "title": "秦始皇统一六国",
      "dynasty": "秦朝",
      "score": 17
    }
  ]
}
```

## 数据库配置

当前数据库连接通过项目根目录 `.env` 配置，`backend/app/database.py` 会使用 `python-dotenv` 自动读取：

```text
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/history_ai?charset=utf8mb4
```

运行前请先在 MySQL 中创建数据库：

```sql
CREATE DATABASE history_ai DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

当前版本已创建用户表和历史知识表的 SQLAlchemy 模型，后续可继续添加 Alembic 数据库迁移或自动建表脚本。

## 历史知识数据结构

`data/history_knowledge.json` 当前兼容旧字段并扩展了更适合中小学历史学习的结构：

```json
{
  "title": "知识点名称",
  "dynasty": "朝代",
  "time": "时间",
  "people": ["相关人物"],
  "event": "历史事件",
  "reason": "原因",
  "impact": "影响",
  "keywords": ["关键词"],
  "content": "兼容旧版的知识点正文"
}
```

当前知识库已覆盖：

- 中国古代史：秦始皇统一六国、汉武帝巩固大一统、商鞅变法、贞观之治、郑和下西洋等。
- 中国近现代史：鸦片战争、洋务运动、辛亥革命、五四运动、新中国成立等。
- 世界史：文艺复兴、新航路开辟、英国资产阶级革命、法国大革命、第一次工业革命等。

## 当前问答流程

当前 `POST /api/question` 已形成第一版可用闭环：

```text
用户问题
↓
rag_service.py 读取 data/history_knowledge.json
↓
按标题、关键词、朝代、人物、事件、原因、影响等字段进行加权检索
↓
返回 Top 3 相关知识点和命中分数
↓
ai_service.py 将命中的历史知识整理为回答，并返回 sources 来源
```

示例问题：

```text
秦始皇为什么统一六国？
```

可匹配知识点：

```text
秦始皇统一六国、秦朝、统一六国、中央集权
```

如果没有匹配到知识点，系统会提示当前知识库暂时没有相关内容，并建议用户换用历史人物、朝代或事件名称继续提问。

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

## 测试

当前 v0.4 已新增 pytest 测试，覆盖：

- RAG 正常知识命中
- 多知识点排序和 Top 3 返回
- 无匹配问题
- `/api/question` 接口正常命中
- `/api/question` 接口多来源排序
- `/api/question` 接口无匹配提示

运行方式：

```bash
cd HistoryAI-System/backend
python -m pytest tests
```

## 下一步开发建议

1. 添加数据库初始化脚本，将 JSON 知识点导入 MySQL。
2. 增加问答历史记录，保存用户问题、回答和知识来源。
3. 优化 RAG 检索策略，支持同义词、分词和更精确的排序。
4. 接入大模型 API，将检索到的知识点和用户问题组合成提示词。
5. 添加语音功能：在 `speech_service.py` 中实现语音转文字和文字转语音，并新增上传音频接口。
6. 完善用户模块：添加注册、登录、问答历史记录和知识点收藏功能。

## v0.5 第一阶段：数据库基础建设

本阶段在不破坏 v0.4 问答功能的前提下，补充 MySQL 数据库基础能力。当前 `POST /api/question` 仍沿用本地 `data/history_knowledge.json` 检索流程，JSON 知识库继续作为备用数据源。

### 已新增能力

- 完善 `HistoryKnowledge` SQLAlchemy 模型，支持 `time`、`people`、`event`、`reason`、`impact` 等结构化字段。
- 新增 `QuestionHistory` 问答历史模型，为后续保存用户问题、回答和来源快照做准备。
- 新增数据库初始化脚本，用于根据 SQLAlchemy 模型创建数据表。
- 新增 JSON 导入 MySQL 脚本，用于把 `data/history_knowledge.json` 写入 `history_knowledge` 表。

### 初始化数据库

请先确认项目根目录 `.env` 中已经配置 MySQL 连接：

```text
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/history_ai?charset=utf8mb4
```

进入后端目录后运行：

```bash
cd HistoryAI-System/backend
python -m app.init_db
```

### 导入历史知识 JSON

初始化数据表后运行：

```bash
cd HistoryAI-System/backend
python -m app.scripts.import_history_knowledge
```

导入脚本会按照 `title` 判断知识点是否已存在：

- 不存在则新增；
- 已存在则更新；
- `people` 和 `keywords` 使用 JSON 字符串保存到数据库字段中。

### 兼容说明

v0.5 第一阶段暂不修改 `backend/app/api/question.py`、`backend/app/services/rag_service.py` 和前端页面，因此 v0.4 的问答、RAG 检索、知识来源展示和 pytest 接口测试逻辑保持不变。
