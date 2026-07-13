from datetime import datetime

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    """Request body for the question-answering API."""

    question: str = Field(..., min_length=1, description="User history question")


class KnowledgeSource(BaseModel):
    """Knowledge source returned by the question-answering API."""

    title: str = Field(..., description="Knowledge title")
    dynasty: str = Field("", description="Dynasty or historical period")
    score: int = Field(..., description="RAG match score")


class QuestionResponse(BaseModel):
    """Response body for the question-answering API."""

    answer: str = Field(..., description="Generated answer")
    sources: list[KnowledgeSource] = Field(
        default_factory=list,
        description="Matched history knowledge sources",
    )


class QuestionHistoryResponse(BaseModel):
    """Serialized question history record for later history APIs."""

    id: int = Field(..., description="Question history record ID")
    user_id: int | None = Field(None, description="User ID")
    question: str = Field(..., description="User history question")
    answer: str = Field(..., description="Generated answer")
    sources: list[KnowledgeSource] = Field(
        default_factory=list,
        description="Saved knowledge source snapshot",
    )
    created_at: datetime = Field(..., description="Created time")


class QuestionHistoryListResponse(BaseModel):
    """Response body for question history list API."""

    histories: list[QuestionHistoryResponse] = Field(
        default_factory=list,
        description="Question history records",
    )


class UserCreate(BaseModel):
    """User creation request body reserved for later user features."""

    username: str
    password: str
