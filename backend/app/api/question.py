import json
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QuestionHistory
from app.schemas import (
    QuestionHistoryListResponse,
    QuestionHistoryResponse,
    QuestionRequest,
    QuestionResponse,
)
from app.services.ai_service import generate_answer_result
from app.services.knowledge_service import build_knowledge_outline
from app.services.rag_service import retrieve_history_knowledge


router = APIRouter()
logger = logging.getLogger(__name__)


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

        try:
            score = int(source.get("score", 0) or 0)
        except (TypeError, ValueError):
            score = 0

        sources.append(
            {
                "title": str(source.get("title", "")),
                "dynasty": str(source.get("dynasty", "")),
                "score": score,
            }
        )

    return sources


@router.post("/question", response_model=QuestionResponse)
def ask_question(request: QuestionRequest, db: Session = Depends(get_db)):
    """Run RAG, generate an answer, and save history without blocking delivery."""
    knowledge_items = retrieve_history_knowledge(request.question)
    answer, answer_mode = generate_answer_result(request.question, knowledge_items)

    sources = [
        {
            "title": item.get("title", ""),
            "dynasty": item.get("dynasty", ""),
            "score": item.get("score", 0),
        }
        for item in knowledge_items
    ]
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

    histories = [
        QuestionHistoryResponse(
            id=row.id,
            user_id=row.user_id,
            question=row.question,
            answer=row.answer,
            sources=_parse_sources(row.sources),
            created_at=row.created_at,
        )
        for row in history_rows
    ]

    return QuestionHistoryListResponse(histories=histories)
