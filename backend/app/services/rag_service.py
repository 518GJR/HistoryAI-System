import json
from pathlib import Path


# 历史知识 JSON 文件路径，保持读取现有 data 目录，不改变项目结构
DATA_FILE = Path(__file__).resolve().parents[3] / "data" / "history_knowledge.json"

# 不同字段的匹配权重：标题最高，关键词次之，朝代再次
FIELD_WEIGHTS = {
    "title": 10,
    "keywords": 7,
    "dynasty": 5,
    "people": 4,
    "event": 3,
    "time": 2,
    "reason": 2,
    "impact": 2,
    "content": 1,
}

# 第一版检索最多返回 3 条，避免回答过长
TOP_K = 3


def load_history_knowledge() -> list[dict]:
    """读取本地历史知识 JSON 数据。"""
    if not DATA_FILE.exists():
        return []

    with DATA_FILE.open("r", encoding="utf-8") as file:
        data = json.load(file)

    return data if isinstance(data, list) else []


def _normalize_keywords(keywords) -> list[str]:
    """将关键词字段统一转换为字符串列表，兼容列表和逗号分隔字符串。"""
    if isinstance(keywords, list):
        return [str(keyword).strip() for keyword in keywords if str(keyword).strip()]

    if isinstance(keywords, str):
        return [keyword.strip() for keyword in keywords.split(",") if keyword.strip()]

    return []


def _normalize_list(value) -> list[str]:
    """将人物等字段统一转换为字符串列表，兼容列表和字符串。"""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str) and value.strip():
        return [value.strip()]

    return []


def _build_field_terms(item: dict) -> dict[str, list[str]]:
    """按字段提取检索词，兼容旧数据和 v0.3 新数据结构。"""
    field_terms = {
        "title": _normalize_list(item.get("title")),
        "dynasty": _normalize_list(item.get("dynasty")),
        "time": _normalize_list(item.get("time")),
        "people": _normalize_list(item.get("people")),
        "event": _normalize_list(item.get("event")),
        "reason": _normalize_list(item.get("reason")),
        "impact": _normalize_list(item.get("impact")),
        "keywords": _normalize_keywords(item.get("keywords")),
        "content": _normalize_list(item.get("content")),
    }

    return field_terms


def _score_item(question_text: str, item: dict) -> tuple[int, list[str]]:
    """计算单条知识点与问题的匹配分数。"""
    score = 0
    matched_terms = []
    field_terms = _build_field_terms(item)

    for field, terms in field_terms.items():
        weight = FIELD_WEIGHTS.get(field, 1)
        for term in terms:
            if term and term in question_text:
                score += weight
                matched_terms.append(term)

    # 去重后保留命中顺序，便于回答中展示匹配关键词
    unique_terms = list(dict.fromkeys(matched_terms))
    return score, unique_terms


def retrieve_history_knowledge(question: str) -> list[dict]:
    """根据用户问题检索相关历史知识。

    v0.3 使用加权关键词匹配，并返回分数最高的 Top 3 相关知识。
    """
    question_text = question.strip()
    if not question_text:
        return []

    matched_items = []
    for item in load_history_knowledge():
        score, matched_terms = _score_item(question_text, item)

        if score > 0:
            matched_item = {
                "title": item.get("title", ""),
                "dynasty": item.get("dynasty", ""),
                "time": item.get("time", ""),
                "people": _normalize_list(item.get("people")),
                "event": item.get("event", ""),
                "reason": item.get("reason", ""),
                "impact": item.get("impact", ""),
                "keywords": _normalize_keywords(item.get("keywords")),
                "content": item.get("content", ""),
                "matched_terms": matched_terms,
                "score": score,
            }
            matched_items.append(matched_item)

    # 分数越高，排序越靠前；只返回 Top 3，供问答和前端来源展示使用
    return sorted(matched_items, key=lambda item: item["score"], reverse=True)[:TOP_K]
