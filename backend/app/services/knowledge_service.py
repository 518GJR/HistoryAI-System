"""Build a demonstrable structured study outline from RAG results."""

from app.services.rag_service import knowledge_item_to_source


def build_knowledge_outline(topic: str, knowledge_items: list[dict]) -> dict | None:
    """Use the highest-scoring item as the main outline and retain related points."""
    if not knowledge_items:
        return None

    main = knowledge_items[0]
    sources = [knowledge_item_to_source(item) for item in knowledge_items]
    related_points = [
        item.get("title", "")
        for item in knowledge_items[1:]
        if item.get("title")
    ]

    return {
        "topic": main.get("title") or topic,
        "time": main.get("time", ""),
        "people": list(main.get("people") or []),
        "event": main.get("event", ""),
        "reason": main.get("reason", ""),
        "process": main.get("content", ""),
        "result_impact": main.get("impact", ""),
        "related_points": related_points,
        "sources": sources,
    }
