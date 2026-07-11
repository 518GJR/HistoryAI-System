from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """问答接口请求体。"""

    question: str = Field(..., min_length=1, description="用户输入的历史问题")


class KnowledgeSource(BaseModel):
    """问答来源知识点，用于前端后续展示引用来源。"""

    title: str = Field(..., description="知识点名称")
    dynasty: str = Field("", description="所属朝代")
    score: int = Field(..., description="RAG 检索命中分数")


class QuestionResponse(BaseModel):
    """问答接口响应体。"""

    answer: str = Field(..., description="系统生成的回答")
    sources: list[KnowledgeSource] = Field(default_factory=list, description="命中的历史知识来源")


class UserCreate(BaseModel):
    """用户创建请求体，当前仅作为后续功能预留。"""

    username: str
    password: str
