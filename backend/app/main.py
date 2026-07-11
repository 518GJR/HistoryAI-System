from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import question, user


# 创建 FastAPI 应用实例
app = FastAPI(
    title="面向中小学历史知识点的语音驱动问答与知识梳理系统",
    description="毕业设计项目后端服务，当前版本提供基础问答接口骨架。",
    version="0.1.0",
)

# 配置跨域，方便前端本地开发时访问后端接口
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册业务路由
app.include_router(user.router, prefix="/api/user", tags=["用户模块"])
app.include_router(question.router, prefix="/api", tags=["历史问答模块"])


@app.get("/")
def read_root():
    """系统健康检查接口。"""
    return {"message": "HistoryAI-System 后端服务已启动"}
