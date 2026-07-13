import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import QuestionHistory


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_question_history():
    db = TestingSessionLocal()
    try:
        db.query(QuestionHistory).delete()
        db.commit()
    finally:
        db.close()

    yield

    db = TestingSessionLocal()
    try:
        db.query(QuestionHistory).delete()
        db.commit()
    finally:
        db.close()


def test_question_api_hit():
    response = client.post(
        "/api/question",
        json={"question": "\u79e6\u59cb\u7687\u4e3a\u4ec0\u4e48\u7edf\u4e00\u516d\u56fd\uff1f"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "\u79e6\u59cb\u7687\u7edf\u4e00\u516d\u56fd" in data["answer"]
    assert data["sources"]
    assert data["sources"][0]["title"] == "\u79e6\u59cb\u7687\u7edf\u4e00\u516d\u56fd"
    assert data["sources"][0]["score"] > 0


def test_question_api_multiple_sources_sorted():
    response = client.post(
        "/api/question",
        json={
            "question": "\u5927\u4e00\u7edf \u4e2d\u592e\u96c6\u6743 "
            "\u6c49\u6b66\u5e1d \u79e6\u59cb\u7687"
        },
    )

    assert response.status_code == 200
    sources = response.json()["sources"]
    assert 1 <= len(sources) <= 3
    scores = [source["score"] for source in sources]
    assert scores == sorted(scores, reverse=True)


def test_question_api_no_match():
    response = client.post(
        "/api/question",
        json={"question": "\u4eca\u5929\u5348\u996d\u5403\u4ec0\u4e48\u6bd4\u8f83\u597d\uff1f"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "\u6682\u65f6\u6ca1\u6709\u5339\u914d\u5230\u76f8\u5173\u5386\u53f2\u77e5\u8bc6\u70b9" in data["answer"]
    assert data["sources"] == []


def test_question_history_api_returns_200_and_histories_key():
    response = client.get("/api/question/history")

    assert response.status_code == 200
    data = response.json()
    assert "histories" in data
    assert isinstance(data["histories"], list)


def test_question_history_api_returns_sources_as_list():
    db = TestingSessionLocal()
    try:
        db.add(
            QuestionHistory(
                user_id=None,
                question="test question",
                answer="test answer",
                sources="not valid json",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/question/history")

    assert response.status_code == 200
    histories = response.json()["histories"]
    assert len(histories) == 1
    assert histories[0]["sources"] == []


def test_question_history_api_can_query_record_after_post():
    question = "\u79e6\u59cb\u7687\u4e3a\u4ec0\u4e48\u7edf\u4e00\u516d\u56fd\uff1f"

    post_response = client.post("/api/question", json={"question": question})
    history_response = client.get("/api/question/history")

    assert post_response.status_code == 200
    assert history_response.status_code == 200

    histories = history_response.json()["histories"]
    assert histories
    assert histories[0]["question"] == question
    assert isinstance(histories[0]["sources"], list)
    assert histories[0]["sources"] == post_response.json()["sources"]
