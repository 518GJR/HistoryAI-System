from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_question_api_hit():
    """测试问答接口正常命中知识点并返回 sources。"""
    response = client.post("/api/question", json={"question": "秦始皇为什么统一六国？"})

    assert response.status_code == 200
    data = response.json()
    assert "秦始皇统一六国" in data["answer"]
    assert data["sources"]
    assert data["sources"][0]["title"] == "秦始皇统一六国"
    assert data["sources"][0]["score"] > 0


def test_question_api_multiple_sources_sorted():
    """测试问答接口多知识点来源按分数排序。"""
    response = client.post(
        "/api/question",
        json={"question": "大一统 中央集权 汉武帝 秦始皇"},
    )

    assert response.status_code == 200
    sources = response.json()["sources"]
    assert 1 <= len(sources) <= 3
    scores = [source["score"] for source in sources]
    assert scores == sorted(scores, reverse=True)


def test_question_api_no_match():
    """测试问答接口无匹配时返回提示且 sources 为空。"""
    response = client.post("/api/question", json={"question": "今天午饭吃什么比较好？"})

    assert response.status_code == 200
    data = response.json()
    assert "暂时没有匹配到相关历史知识点" in data["answer"]
    assert data["sources"] == []
