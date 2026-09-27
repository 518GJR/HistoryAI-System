from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import knowledge, question, speech, user


app = FastAPI(
    title="面向中小学历史知识点的语音驱动问答与知识梳理系统",
    description="支持 RAG 历史问答、结构化知识梳理、ASR 与 TTS 的毕业设计后端。",
    version="0.6.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router, prefix="/api/user", tags=["用户模块"])
app.include_router(question.router, prefix="/api", tags=["历史问答模块"])
app.include_router(speech.router, prefix="/api", tags=["语音模块"])
app.include_router(knowledge.router, prefix="/api", tags=["知识梳理模块"])


@app.get("/")
def read_root():
    """系统健康检查接口。"""
    return {"message": "HistoryAI-System 后端服务已启动"}
