# 面向中小学历史知识点的语音驱动问答与知识梳理系统

## 项目介绍

本项目是一个毕业设计第一版代码骨架，目标是构建面向中小学历史知识点的智能问答与知识梳理系统。当前版本已完成基础前后端结构、数据库模型、问答接口、简单聊天页面，以及基于本地 JSON 历史知识库的第一版关键词检索问答闭环。

## 技术架构

- 后端：Python + FastAPI
- 前端：Vue3 + Vite
- 数据库：MySQL
- ORM：SQLAlchemy
- 环境变量：python-dotenv
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
  "answer": "你提出的问题是：秦始皇为什么统一六国？。当前系统已收到问题，后续版本将结合历史知识库生成更完整的回答。"
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

## 当前问答流程

当前 `POST /api/question` 已形成第一版可用闭环：

```text
用户问题
↓
rag_service.py 读取 data/history_knowledge.json
↓
按标题、朝代、关键词进行基础关键词检索
↓
ai_service.py 将命中的历史知识整理为回答
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

## 下一步开发建议

1. 扩充 `data/history_knowledge.json`，覆盖更多中小学历史知识点。
2. 添加数据库初始化脚本，将 JSON 知识点导入 MySQL。
3. 优化 RAG 检索策略，支持同义词、分词和更精确的排序。
4. 接入大模型 API，将检索到的知识点和用户问题组合成提示词。
5. 添加语音功能：在 `speech_service.py` 中实现语音转文字和文字转语音，并新增上传音频接口。
6. 完善用户模块：添加注册、登录、问答历史记录和知识点收藏功能。
