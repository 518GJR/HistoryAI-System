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
from app.services.ai_service import generate_answer_result, template_answer
from app.services.knowledge_service import build_knowledge_outline
from app.services.rag_service import (
    KnowledgeDataError,
    get_knowledge_mode,
    knowledge_item_to_source,
    load_textbook_knowledge_from_json,
    retrieve_history_knowledge,
    get_retrieval_mode,
)
from app.services.support_assessment import (
    assess_support,
    evidence_covers_assessment,
    supporting_answer_items,
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
            source_snapshot["score"] = float(source.get("score", 0) or 0)
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
        raise HTTPException(status_code=503, detail=f"检索不可用：{exc}") from exc
    retrieval_mode = get_retrieval_mode()
    support_assessment = None
    answer_items = knowledge_items
    if get_knowledge_mode() == "textbook":
        textbook_points = load_textbook_knowledge_from_json()
        support_assessment = assess_support(
            request.question, retrieval_mode, knowledge_items, textbook_points
        )
        answer_items = (
            supporting_answer_items(knowledge_items, support_assessment)
            if support_assessment.status == "sufficient"
            else []
        )

    answer, answer_mode, used_evidence = generate_answer_result(
        request.question, answer_items
    )
    if support_assessment is not None:
        if support_assessment.status != "sufficient" or not evidence_covers_assessment(
            support_assessment, used_evidence
        ):
            answer = template_answer(request.question, [])
            answer_mode = "insufficient_support"
            used_evidence = []

    sources = [knowledge_item_to_source(item) for item in knowledge_items]
    supporting_source_ids = (
        set(support_assessment.supporting_source_ids) if support_assessment else set()
    )
    for source in sources:
        source["supporting"] = any(
            reference.get("source_id") in supporting_source_ids
            for reference in source.get("source_refs", [])
        )
    sources_by_id = {
        knowledge_id: source
        for source in sources
        for knowledge_id in source.get("knowledge_ids") or [source["knowledge_id"]]
    }
    for evidence in used_evidence:
        for knowledge_id in evidence.get("knowledge_ids", []):
            source = sources_by_id.get(knowledge_id)
            if source is not None:
                source.setdefault("used_evidence", []).append(evidence)
    outline = build_knowledge_outline(request.question, answer_items)
    if outline is not None:
        outline["sources"] = [
            source
            for source in sources
            if support_assessment is None or source.get("supporting")
        ]

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
        retrieval_mode=retrieval_mode,
        used_evidence=used_evidence,
        support_assessment=(support_assessment.public() if support_assessment else None),
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
