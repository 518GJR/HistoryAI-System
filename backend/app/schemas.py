from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestionRequest(BaseModel):
    """Request body for the question-answering API."""

    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(..., min_length=1, max_length=2000, description="User history question")


class KnowledgeSource(BaseModel):
    """Knowledge source returned by the question-answering API."""

    title: str = Field(..., description="Knowledge title")
    dynasty: str = Field("", description="Dynasty or historical period")
    score: int = Field(..., description="RAG match score")


class KnowledgeOutline(BaseModel):
    """Structured history-study outline generated from retrieved knowledge."""

    topic: str
    time: str = ""
    people: list[str] = Field(default_factory=list)
    event: str = ""
    reason: str = ""
    process: str = ""
    result_impact: str = ""
    related_points: list[str] = Field(default_factory=list)
    sources: list[KnowledgeSource] = Field(default_factory=list)


class QuestionResponse(BaseModel):
    """Response body for the question-answering API."""

    history_saved: bool = True
    answer_mode: str = "fallback"
    answer: str = Field(..., description="Generated answer")
    sources: list[KnowledgeSource] = Field(default_factory=list)
    knowledge_outline: KnowledgeOutline | None = None


class QuestionHistoryResponse(BaseModel):
    """Serialized question history record for later history APIs."""

    id: int
    user_id: int | None = None
    question: str
    answer: str
    sources: list[KnowledgeSource] = Field(default_factory=list)
    created_at: datetime


class QuestionHistoryListResponse(BaseModel):
    """Response body for question history list API."""

    histories: list[QuestionHistoryResponse] = Field(default_factory=list)


class AsrResponse(BaseModel):
    """Speech recognition response."""

    text: str


class TtsRequest(BaseModel):
    """Speech synthesis request."""

    model_config = ConfigDict(str_strip_whitespace=True)
    text: str = Field(..., min_length=1, max_length=5000)


class UserCreate(BaseModel):
    """User creation request body reserved for later user features."""

    username: str
    password: str
