import json

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
from app.services.ai_service import generate_answer
from app.services.rag_service import retrieve_history_knowledge


router = APIRouter()


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
    """Answer a history question and save the generated QA record."""
    knowledge_items = retrieve_history_knowledge(request.question)
    answer = generate_answer(request.question, knowledge_items)

    sources = [
        {
            "title": item.get("title", ""),
            "dynasty": item.get("dynasty", ""),
            "score": item.get("score", 0),
        }
        for item in knowledge_items
    ]

    question_history = QuestionHistory(
        user_id=None,
        question=request.question,
        answer=answer,
        sources=json.dumps(sources, ensure_ascii=False),
    )
    db.add(question_history)
    db.commit()

    return QuestionResponse(answer=answer, sources=sources)


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
