import json
from datetime import datetime

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import QuestionHistory
from app.services import ai_service, rag_service


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
    assert "当前检索资料中暂时没有匹配到" in data["answer"]
    assert "不表示整本教材或知识库没有相关内容" in data["answer"]
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


def test_question_history_api_accepts_legacy_source_snapshot():
    db = TestingSessionLocal()
    try:
        db.add(
            QuestionHistory(
                user_id=None,
                question="legacy question",
                answer="legacy answer",
                sources=json.dumps(
                    [{"title": "旧来源", "dynasty": "秦朝", "score": 3}],
                    ensure_ascii=False,
                ),
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/question/history")

    assert response.status_code == 200
    source = response.json()["histories"][0]["sources"][0]
    assert source["title"] == "旧来源"
    assert source["book_title"] == ""
    assert source["source_refs"] == []


def test_textbook_source_metadata_reaches_api_and_history(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")

    post_response = client.post(
        "/api/question", json={"question": "北京人用火有什么作用？"}
    )
    history_response = client.get("/api/question/history")

    assert post_response.status_code == 200
    source = post_response.json()["sources"][0]
    assert source["book_id"] == "H7A"
    assert source["lesson_number"] == 1
    assert source["section_title"]
    assert source["textbook_pages"]
    assert source["pdf_pages"]
    assert source["source_refs"][0]["excerpt"]
    assert post_response.json()["knowledge_outline"]["sources"][0] == source
    assert history_response.json()["histories"][0]["sources"] == post_response.json()["sources"]


def test_textbook_ai_evidence_selection_reaches_question_api(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")
    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setenv("AI_BASE_URL", "https://mock.example/v1")

    def handler(request):
        payload = json.loads(request.content)
        user_payload = json.loads(payload["messages"][1]["content"])
        assert user_payload["source_titles"][0] == "北京人用火"
        first_line = user_payload["evidence_lines"][0]
        assert first_line["text"] == (
            "北京人遗址中发现有灰烬、烧石和烧骨等，这反映出北京人已经会使用火。"
            "北京人用火烧烤食物、防寒、照明、驱兽，从而改善了生存条件。"
            "学会用火是人类演化史上的里程碑。"
        )
        assert first_line["knowledge_ids"] == ["H7A-L01-010"]
        assert first_line["source_ids"] == ["H7A-P006-B"]
        assert first_line["evidence_kind"] == "textbook_excerpt"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": '{"selected_ids":["E1"]}'}}
                ]
            },
        )

    monkeypatch.setattr(
        ai_service,
        "_create_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
    )

    response = client.post(
        "/api/question", json={"question": "北京人用火有什么作用和意义？"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer_mode"] == "evidence_selection"
    assert data["answer"] == (
        "教材原文：\n"
        "1. 【北京人用火】北京人遗址中发现有灰烬、烧石和烧骨等，"
        "这反映出北京人已经会使用火。北京人用火烧烤食物、防寒、照明、驱兽，"
        "从而改善了生存条件。学会用火是人类演化史上的里程碑。"
    )
    assert len(data["used_evidence"]) == 1
    assert data["used_evidence"][0]["knowledge_id"] == "H7A-L01-010"
    assert data["used_evidence"][0]["knowledge_ids"] == ["H7A-L01-010"]
    assert data["used_evidence"][0]["source_ids"] == ["H7A-P006-B"]
    assert data["sources"][0]["used_evidence"] == data["used_evidence"]
    assert data["sources"][0]["knowledge_id"] == "H7A-L01-010"
    assert data["sources"][0]["textbook_pages"] == "6"
    assert data["sources"][0]["pdf_pages"] == "11"


def test_textbook_data_error_returns_503(monkeypatch, tmp_path):
    monkeypatch.setenv("KNOWLEDGE_MODE", "textbook")
    monkeypatch.setattr(rag_service, "TEXTBOOK_DATA_FILE", tmp_path / "missing.json")

    response = client.post("/api/question", json={"question": "北京人"})

    assert response.status_code == 503
    assert response.json()["detail"] == "所选知识库不可用，请检查配置和数据文件"


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


def test_sqlite_history_timestamp_is_serialized_as_explicit_utc():
    db = TestingSessionLocal()
    try:
        db.add(
            QuestionHistory(
                question="timezone test",
                answer="timezone answer",
                sources="[]",
                created_at=datetime(2026, 10, 19, 8, 30),
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/api/question/history")

    assert response.status_code == 200
    assert response.json()["histories"][0]["created_at"] == "2026-10-19T08:30:00Z"


def test_question_answer_survives_history_save_failure():
    class BrokenDb:
        def add(self, value):
            pass

        def commit(self):
            raise RuntimeError("mock database failure")

        def rollback(self):
            pass

        def close(self):
            pass

    def override_broken_db():
        yield BrokenDb()

    previous = app.dependency_overrides[get_db]
    app.dependency_overrides[get_db] = override_broken_db
    try:
        response = client.post("/api/question", json={"question": "秦始皇统一六国"})
    finally:
        app.dependency_overrides[get_db] = previous

    assert response.status_code == 200
    assert response.json()["answer"]
    assert response.json()["history_saved"] is False
