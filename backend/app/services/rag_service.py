import json
from pathlib import Path


# 历史知识 JSON 文件路径，保持读取现有 data 目录，不改变项目结构
DATA_FILE = Path(__file__).resolve().parents[3] / "data" / "history_knowledge.json"


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


def _build_search_terms(item: dict) -> list[str]:
    """提取可用于匹配的搜索词，包括标题、朝代和显式关键词。"""
    terms = []

    for field in ("title", "dynasty"):
        value = str(item.get(field, "")).strip()
        if value:
            terms.append(value)

    terms.extend(_normalize_keywords(item.get("keywords")))
    return terms


def retrieve_history_knowledge(question: str) -> list[dict]:
    """根据用户问题检索相关历史知识。

    第一版使用关键词包含匹配：只要问题中包含标题、朝代或关键词，即认为相关。
    """
    question_text = question.strip()
    if not question_text:
        return []

    matched_items = []
    for item in load_history_knowledge():
        terms = _build_search_terms(item)
        matched_terms = [term for term in terms if term and term in question_text]

        # 如果关键词没有直接命中，则尝试用正文中的重要短语做弱匹配
        content = str(item.get("content", ""))
        if not matched_terms:
            matched_terms = [term for term in terms if term and term in content and term in question_text]

        if matched_terms:
            matched_item = {
                "title": item.get("title", ""),
                "dynasty": item.get("dynasty", ""),
                "keywords": _normalize_keywords(item.get("keywords")),
                "content": item.get("content", ""),
                "matched_terms": matched_terms,
            }
            matched_items.append(matched_item)

    # 命中词越多，排序越靠前，方便问答服务优先使用更相关的知识点
    return sorted(matched_items, key=lambda item: len(item["matched_terms"]), reverse=True)
