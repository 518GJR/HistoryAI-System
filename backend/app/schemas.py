from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """问答接口请求体。"""

    question: str = Field(..., min_length=1, description="用户输入的历史问题")


class QuestionResponse(BaseModel):
    """问答接口响应体。"""

    answer: str = Field(..., description="系统生成的回答")


class UserCreate(BaseModel):
    """用户创建请求体，当前仅作为后续功能预留。"""

    username: str
    password: str
