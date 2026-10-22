from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuestionRequest(BaseModel):
    """Request body for the question-answering API."""

    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(..., min_length=1, max_length=2000, description="User history question")


class SourceReference(BaseModel):
    """A verifiable excerpt and its textbook/PDF location."""

    source_id: str
    material_type: str = ""
    textbook_pages: str = ""
    pdf_pages: str = ""
    excerpt: str = ""
    locator: str = ""


class UsedEvidence(BaseModel):
    """A verbatim evidence line actually selected for the final answer."""

    evidence_id: str
    text: str
    knowledge_id: str = ""
    knowledge_ids: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    source_title: str = ""
    source_titles: list[str] = Field(default_factory=list)
    textbook_pages: str = ""
    pdf_pages: str = ""


class KnowledgeSource(BaseModel):
    """Knowledge source returned by the question-answering API."""

    title: str = Field(..., description="Knowledge title")
    dynasty: str = Field("", description="Dynasty or historical period")
    score: float = Field(0, description="Strategy-specific retrieval score")
    retrieval_mode: str = "keyword"
    retrieval_unit: str = "knowledge_point"
    knowledge_id: str = ""
    knowledge_ids: list[str] = Field(default_factory=list)
    book_id: str = ""
    book_title: str = ""
    unit_id: str = ""
    unit_title: str = ""
    lesson_id: str = ""
    lesson_number: int | None = None
    lesson_title: str = ""
    section_title: str = ""
    material_types: list[str] = Field(default_factory=list)
    textbook_pages: str = ""
    pdf_pages: str = ""
    qualifiers: list[str] = Field(default_factory=list)
    evidence_type: str = ""
    certainty: str = ""
    source_refs: list[SourceReference] = Field(default_factory=list)
    used_evidence: list[UsedEvidence] = Field(default_factory=list)
    supporting: bool = False


class SupportAssessmentResponse(BaseModel):
    """Interpretable pre-answer support decision exposed for diagnosis."""

    status: str
    reason_codes: list[str] = Field(default_factory=list)
    required_facets: list[str] = Field(default_factory=list)
    covered_facets: list[str] = Field(default_factory=list)
    supporting_source_ids: list[str] = Field(default_factory=list)
    supporting_knowledge_ids: list[str] = Field(default_factory=list)
    unsupported_facets: list[str] = Field(default_factory=list)
    method: str
    calibration_version: str


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
    retrieval_mode: str = "keyword"
    answer: str = Field(..., description="Generated answer")
    sources: list[KnowledgeSource] = Field(default_factory=list)
    used_evidence: list[UsedEvidence] = Field(default_factory=list)
    support_assessment: SupportAssessmentResponse | None = None
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
