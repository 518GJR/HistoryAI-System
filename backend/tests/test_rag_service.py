from app.services.rag_service import retrieve_history_knowledge


def test_retrieve_history_knowledge_hit():
    """测试正常知识命中：秦始皇问题应命中秦始皇统一六国。"""
    results = retrieve_history_knowledge("秦始皇为什么统一六国？")

    assert results
    assert results[0]["title"] == "秦始皇统一六国"
    assert results[0]["score"] > 0


def test_retrieve_history_knowledge_sorting_and_top3():
    """测试多知识点排序：大一统问题应优先返回更相关的知识点，并限制 Top 3。"""
    results = retrieve_history_knowledge("大一统 中央集权 汉武帝 推恩令 秦始皇")

    assert 1 <= len(results) <= 3
    scores = [item["score"] for item in results]
    assert scores == sorted(scores, reverse=True)
    assert results[0]["title"] == "汉武帝巩固大一统"


def test_retrieve_history_knowledge_no_match():
    """测试无匹配问题：无关问题应返回空列表。"""
    results = retrieve_history_knowledge("今天午饭吃什么比较好？")

    assert results == []
