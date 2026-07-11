from fastapi import APIRouter

from app.schemas import QuestionRequest, QuestionResponse
from app.services.ai_service import generate_answer
from app.services.rag_service import retrieve_history_knowledge


router = APIRouter()


@router.post("/question", response_model=QuestionResponse)
def ask_question(request: QuestionRequest):
    """历史问答接口：先检索知识库，再生成回答。"""
    knowledge_items = retrieve_history_knowledge(request.question)
    answer = generate_answer(request.question, knowledge_items)

    # 将命中的知识点来源返回给前端，后续可在页面展示“参考知识点”
    sources = [
        {
            "title": item.get("title", ""),
            "dynasty": item.get("dynasty", ""),
            "score": item.get("score", 0),
        }
        for item in knowledge_items
    ]

    return QuestionResponse(answer=answer, sources=sources)
