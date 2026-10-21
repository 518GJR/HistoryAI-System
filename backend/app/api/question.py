import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QuestionHistory
from app.schemas import (
    QuestionHistoryListResponse,
    QuestionHistoryResponse,
    QuestionRequest,
    QuestionResponse,
    KnowledgeSource,
)
from app.services.ai_service import generate_answer_result
from app.services.knowledge_service import build_knowledge_outline
from app.services.rag_service import (
    KnowledgeDataError,
    knowledge_item_to_source,
    retrieve_history_knowledge,
)


router = APIRouter()
logger = logging.getLogger(__name__)


def _serialize_created_at(value: datetime, dialect_name: str) -> datetime:
    """Mark known SQLite UTC values; preserve unknown legacy DB semantics."""
    if value.tzinfo is None and dialect_name == "sqlite":
        return value.replace(tzinfo=timezone.utc)
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc)


def _parse_sources(sources_text: str | None) -> list[dict]:
    if not sources_text:
        return []

    try:
        parsed_sources = json.loads(sources_text)
    except (json.JSONDecodeError, TypeError):
        return []

    if not isinstance(parsed_sources, list):
        return []

    sources = []
    for source in parsed_sources:
        if not isinstance(source, dict):
            continue

        source_snapshot = dict(source)
        try:
            source_snapshot["score"] = int(source.get("score", 0) or 0)
        except (TypeError, ValueError):
            source_snapshot["score"] = 0

        try:
            sources.append(KnowledgeSource.model_validate(source_snapshot).model_dump())
        except ValidationError:
            continue

    return sources


@router.post("/question", response_model=QuestionResponse)
def ask_question(request: QuestionRequest, db: Session = Depends(get_db)):
    """Run RAG, generate an answer, and save history without blocking delivery."""
    try:
        knowledge_items = retrieve_history_knowledge(request.question)
    except KnowledgeDataError as exc:
        raise HTTPException(status_code=503, detail="所选知识库不可用，请检查配置和数据文件") from exc
    answer, answer_mode, used_evidence = generate_answer_result(
        request.question, knowledge_items
    )

    sources = [knowledge_item_to_source(item) for item in knowledge_items]
    sources_by_id = {source["knowledge_id"]: source for source in sources}
    for evidence in used_evidence:
        for knowledge_id in evidence.get("knowledge_ids", []):
            source = sources_by_id.get(knowledge_id)
            if source is not None:
                source.setdefault("used_evidence", []).append(evidence)
    outline = build_knowledge_outline(request.question, knowledge_items)

    question_history = QuestionHistory(
        user_id=None,
        question=request.question,
        answer=answer,
        sources=json.dumps(sources, ensure_ascii=False),
    )
    history_saved = True
    try:
        db.add(question_history)
        db.commit()
    except Exception as exc:
        history_saved = False
        try:
            db.rollback()
        except Exception:
            logger.exception("Question history rollback also failed")
        logger.warning("History save failed; returning generated answer: %s", exc)

    return QuestionResponse(
        answer=answer,
        sources=sources,
        history_saved=history_saved,
        answer_mode=answer_mode,
        used_evidence=used_evidence,
        knowledge_outline=outline,
    )


@router.get("/question/history", response_model=QuestionHistoryListResponse)
def get_question_history(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Return recent question history records."""
    history_rows = (
        db.query(QuestionHistory)
        .order_by(QuestionHistory.created_at.desc(), QuestionHistory.id.desc())
        .limit(limit)
        .all()
    )

    dialect_name = db.get_bind().dialect.name
    histories = [
        QuestionHistoryResponse(
            id=row.id,
            user_id=row.user_id,
            question=row.question,
            answer=row.answer,
            sources=_parse_sources(row.sources),
            created_at=_serialize_created_at(row.created_at, dialect_name),
        )
        for row in history_rows
    ]

    return QuestionHistoryListResponse(histories=histories)
