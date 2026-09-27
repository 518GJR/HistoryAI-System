import json

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services import speech_service


client = TestClient(app)


def _enable_provider(monkeypatch, prefix, model):
    monkeypatch.setenv(f"{prefix}_PROVIDER", "openai_compatible")
    monkeypatch.setenv(f"{prefix}_API_KEY", "test-key")
    monkeypatch.setenv(f"{prefix}_MODEL", model)
    monkeypatch.setenv(f"{prefix}_BASE_URL", "https://mock.example/v1")


def test_asr_api_with_mock_transport(monkeypatch):
    _enable_provider(monkeypatch, "ASR", "mock-whisper")

    def handler(request):
        assert request.url.path == "/v1/audio/transcriptions"
        assert request.headers["authorization"] == "Bearer test-key"
        assert "multipart/form-data" in request.headers["content-type"]
        return httpx.Response(200, json={"text": "识别后的历史问题"})

    monkeypatch.setattr(
        speech_service,
        "_create_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
    )
    response = client.post(
        "/api/speech/asr",
        files={"audio": ("recording.webm", b"mock-audio", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "识别后的历史问题"}


def test_tts_api_with_mock_transport(monkeypatch):
    _enable_provider(monkeypatch, "TTS", "mock-tts")
    monkeypatch.setenv("TTS_VOICE", "alloy")
    monkeypatch.setenv("TTS_FORMAT", "mp3")

    def handler(request):
        assert request.url.path == "/v1/audio/speech"
        payload = json.loads(request.content)
        assert payload["input"] == "这是一段历史回答"
        assert payload["voice"] == "alloy"
        return httpx.Response(200, content=b"mock-mp3-bytes")

    monkeypatch.setattr(
        speech_service,
        "_create_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
    )
    response = client.post("/api/speech/tts", json={"text": "这是一段历史回答"})

    assert response.status_code == 200
    assert response.content == b"mock-mp3-bytes"
    assert response.headers["content-type"].startswith("audio/mpeg")


def test_speech_endpoints_report_unconfigured_service():
    asr_response = client.post(
        "/api/speech/asr",
        files={"audio": ("recording.webm", b"mock-audio", "audio/webm")},
    )
    tts_response = client.post("/api/speech/tts", json={"text": "回答"})

    assert asr_response.status_code == 503
    assert tts_response.status_code == 503
