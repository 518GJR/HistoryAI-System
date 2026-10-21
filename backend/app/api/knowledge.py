"""Structured history knowledge outline endpoint."""

from fastapi import APIRouter, HTTPException, Query

from app.schemas import KnowledgeOutline
from app.services.knowledge_service import build_knowledge_outline
from app.services.rag_service import KnowledgeDataError, retrieve_history_knowledge


router = APIRouter()


@router.get("/knowledge/outline", response_model=KnowledgeOutline)
def get_knowledge_outline(
    topic: str = Query(..., min_length=1, max_length=2000),
):
    """Retrieve a topic and organize it into a study-friendly structure."""
    try:
        items = retrieve_history_knowledge(topic)
    except KnowledgeDataError as exc:
        raise HTTPException(status_code=503, detail="所选知识库不可用，请检查配置和数据文件") from exc
    outline = build_knowledge_outline(topic, items)
    if not outline:
        raise HTTPException(status_code=404, detail="当前知识库未找到相关历史知识")
    return outline
