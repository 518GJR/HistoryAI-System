import json

import httpx

from app.services import ai_service


def _enable_ai(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setenv("AI_MODEL", "test-model")
    monkeypatch.setenv("AI_BASE_URL", "https://mock.example/v1")


def test_ai_answer_uses_retrieved_sources_with_mock_transport(monkeypatch):
    _enable_ai(monkeypatch)

    def handler(request):
        assert request.url.path == "/v1/chat/completions"
        payload = json.loads(request.content)
        user_payload = json.loads(payload["messages"][1]["content"])
        assert user_payload["sources"][0]["title"] == "秦始皇统一六国"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "基于资料的模型回答[1]"}}]},
        )

    monkeypatch.setattr(
        ai_service,
        "_create_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
    )
    answer, mode = ai_service.generate_answer_result(
        "秦始皇为什么统一六国？",
        [{"title": "秦始皇统一六国", "content": "秦灭六国。"}],
    )

    assert mode == "ai"
    assert answer == "基于资料的模型回答[1]"


def test_ai_failure_falls_back_to_template(monkeypatch):
    _enable_ai(monkeypatch)

    def handler(request):
        return httpx.Response(500, json={"error": "mock failure"})

    monkeypatch.setattr(
        ai_service,
        "_create_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
    )
    answer, mode = ai_service.generate_answer_result(
        "秦始皇",
        [{"title": "秦始皇统一六国", "dynasty": "秦朝"}],
    )

    assert mode == "fallback"
    assert "秦始皇统一六国" in answer
