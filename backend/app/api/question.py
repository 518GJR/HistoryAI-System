import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import QuestionHistory
from app.schemas import QuestionRequest, QuestionResponse
from app.services.ai_service import generate_answer
from app.services.rag_service import retrieve_history_knowledge


router = APIRouter()


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
