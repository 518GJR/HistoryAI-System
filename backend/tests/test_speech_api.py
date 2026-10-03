import base64
import json

import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services import speech_service


client = TestClient(app)


def _enable_provider(
    monkeypatch,
    prefix,
    model,
    provider="openai_compatible",
    base_url="https://mock.example/v1",
):
    monkeypatch.setenv(f"{prefix}_PROVIDER", provider)
    monkeypatch.setenv(f"{prefix}_API_KEY", "test-key")
    monkeypatch.setenv(f"{prefix}_MODEL", model)
    monkeypatch.setenv(f"{prefix}_BASE_URL", base_url)


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


def test_aliyun_bailian_asr_api_with_mock_transport(monkeypatch):
    endpoint = (
        "https://workspace-id.cn-beijing.maas.aliyuncs.com/"
        "api/v1/services/aigc/multimodal-generation/generation"
    )
    _enable_provider(
        monkeypatch,
        "ASR",
        "qwen-audio-3.1-asr-flash",
        provider="aliyun_bailian",
        base_url=endpoint,
    )

    def handler(request):
        assert str(request.url) == endpoint
        assert request.headers["authorization"] == "Bearer test-key"
        assert request.headers["content-type"].startswith("application/json")
        assert request.headers["x-dashscope-sse"] == "disable"

        payload = json.loads(request.content)
        assert payload["model"] == "qwen-audio-3.1-asr-flash"
        content = payload["input"]["messages"][0]["content"][0]
        assert content["type"] == "input_audio"
        data_uri = content["input_audio"]["data"]
        prefix, encoded_audio = data_uri.split(",", 1)
        assert prefix == "data:audio/webm;base64"
        assert base64.b64decode(encoded_audio) == b"mock-audio"
        assert payload["parameters"] == {"format": "webm"}

        return httpx.Response(
            200,
            json={"output": {"text": "百炼识别后的历史问题"}},
        )

    monkeypatch.setattr(
        speech_service,
        "_create_client",
        lambda timeout: httpx.Client(transport=httpx.MockTransport(handler), timeout=timeout),
    )
    response = client.post(
        "/api/speech/asr",
        files={"audio": ("recording.webm", b"mock-audio", "audio/webm;codecs=opus")},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "百炼识别后的历史问题"}


def test_aliyun_bailian_tts_api_with_sdk_mock(monkeypatch):
    endpoint = (
        "wss://workspace-id.cn-beijing.maas.aliyuncs.com/"
        "api-ws/v1/inference"
    )
    _enable_provider(
        monkeypatch,
        "TTS",
        "qwen-audio-3.1-tts-flash",
        provider="aliyun_bailian",
        base_url=endpoint,
    )
    monkeypatch.setenv("TTS_VOICE", "longanwen_v3.1")
    monkeypatch.setenv("TTS_FORMAT", "mp3")
    captured = {}

    class FakeSynthesizer:
        def call(self, text, timeout_millis=None):
            captured["text"] = text
            captured["timeout_millis"] = timeout_millis
            return b"mock-aliyun-mp3"

    def fake_factory(config):
        captured["config"] = config.copy()
        return FakeSynthesizer()

    monkeypatch.setattr(speech_service, "_create_aliyun_synthesizer", fake_factory)
    response = client.post("/api/speech/tts", json={"text": "这是一段历史讲解"})

    assert response.status_code == 200
    assert response.content == b"mock-aliyun-mp3"
    assert response.headers["content-type"].startswith("audio/mpeg")
    assert captured["text"] == "这是一段历史讲解"
    assert captured["timeout_millis"] == 60000
    assert captured["config"]["provider"] == "aliyun_bailian"
    assert captured["config"]["model"] == "qwen-audio-3.1-tts-flash"
    assert captured["config"]["url"] == endpoint
    assert captured["config"]["voice"] == "longanwen_v3.1"
    assert captured["config"]["key"] == "test-key"


def test_aliyun_bailian_tts_requires_voice(monkeypatch):
    _enable_provider(
        monkeypatch,
        "TTS",
        "qwen-audio-3.1-tts-flash",
        provider="aliyun_bailian",
        base_url="wss://workspace-id.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference",
    )
    monkeypatch.setenv("TTS_VOICE", "")
    monkeypatch.setenv("TTS_FORMAT", "mp3")

    response = client.post("/api/speech/tts", json={"text": "回答"})

    assert response.status_code == 503
    assert response.json()["detail"] == "TTS service is not configured"


def test_aliyun_bailian_tts_sdk_error_does_not_leak_key(monkeypatch):
    _enable_provider(
        monkeypatch,
        "TTS",
        "qwen-audio-3.1-tts-flash",
        provider="aliyun_bailian",
        base_url="wss://workspace-id.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference",
    )
    monkeypatch.setenv("TTS_VOICE", "longanwen_v3.1")
    monkeypatch.setenv("TTS_FORMAT", "mp3")

    class FailingSynthesizer:
        def call(self, text, timeout_millis=None):
            raise RuntimeError("provider failed with test-key")

    monkeypatch.setattr(
        speech_service,
        "_create_aliyun_synthesizer",
        lambda config: FailingSynthesizer(),
    )
    response = client.post("/api/speech/tts", json={"text": "回答"})

    assert response.status_code == 503
    assert response.json()["detail"] == "TTS provider request failed"
    assert "test-key" not in response.text


def test_aliyun_bailian_tts_rejects_empty_audio(monkeypatch):
    _enable_provider(
        monkeypatch,
        "TTS",
        "qwen-audio-3.1-tts-flash",
        provider="aliyun_bailian",
        base_url="wss://workspace-id.cn-beijing.maas.aliyuncs.com/api-ws/v1/inference",
    )
    monkeypatch.setenv("TTS_VOICE", "longanwen_v3.1")
    monkeypatch.setenv("TTS_FORMAT", "mp3")

    class EmptySynthesizer:
        def call(self, text, timeout_millis=None):
            return b""

    monkeypatch.setattr(
        speech_service,
        "_create_aliyun_synthesizer",
        lambda config: EmptySynthesizer(),
    )
    response = client.post("/api/speech/tts", json={"text": "回答"})

    assert response.status_code == 503
    assert response.json()["detail"] == "TTS provider returned empty audio"

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
