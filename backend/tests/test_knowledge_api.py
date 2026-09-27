from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_knowledge_outline_contains_learning_dimensions():
    response = client.get("/api/knowledge/outline", params={"topic": "秦始皇统一六国"})

    assert response.status_code == 200
    data = response.json()
    assert data["topic"] == "秦始皇统一六国"
    assert data["time"]
    assert "秦始皇" in data["people"]
    assert data["event"]
    assert data["reason"]
    assert data["process"]
    assert data["result_impact"]
    assert data["sources"][0]["title"] == "秦始皇统一六国"


def test_question_response_includes_outline():
    response = client.post("/api/question", json={"question": "商鞅变法"})

    assert response.status_code == 200
    outline = response.json()["knowledge_outline"]
    assert outline["topic"] == "商鞅变法"
    assert outline["people"]
