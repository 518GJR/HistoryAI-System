"""OpenAI-compatible speech recognition and synthesis clients."""

import httpx

from app.services.provider_config import provider_config


class SpeechServiceError(RuntimeError):
    """语音服务未配置、请求失败或响应无效。"""


def _create_client(timeout: float) -> httpx.Client:
    """为自动测试提供安装 httpx.MockTransport 的替换点。"""
    return httpx.Client(timeout=timeout)


def speech_to_text(
    audio: bytes,
    filename: str = "recording.webm",
    content_type: str = "audio/webm",
) -> str:
    """调用 OpenAI-compatible ASR 接口识别内存中的音频。"""
    config = provider_config("ASR")
    if not config:
        raise SpeechServiceError("ASR service is not configured")
    if not audio:
        raise SpeechServiceError("Audio file is empty")

    try:
        with _create_client(config["timeout"]) as client:
            response = client.post(
                f'{config["url"]}/audio/transcriptions',
                headers={"Authorization": f'Bearer {config["key"]}'},
                data={"model": config["model"]},
                files={"file": (filename, audio, content_type)},
            )
            response.raise_for_status()
            text = response.json()["text"]
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise SpeechServiceError("ASR provider request failed") from exc

    if not isinstance(text, str) or not text.strip():
        raise SpeechServiceError("ASR provider returned empty text")
    return text.strip()


def text_to_speech(text: str) -> tuple[bytes, str]:
    """调用 OpenAI-compatible TTS 接口并返回音频字节和媒体类型。"""
    config = provider_config("TTS")
    if not config:
        raise SpeechServiceError("TTS service is not configured")
    if not text.strip():
        raise SpeechServiceError("Text is empty")

    voice = config.get("voice", "alloy")
    audio_format = config.get("format", "mp3")
    media_types = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "opus": "audio/ogg",
        "aac": "audio/aac",
        "flac": "audio/flac",
    }
    try:
        with _create_client(config["timeout"]) as client:
            response = client.post(
                f'{config["url"]}/audio/speech',
                headers={"Authorization": f'Bearer {config["key"]}'},
                json={
                    "model": config["model"],
                    "voice": voice,
                    "input": text,
                    "response_format": audio_format,
                },
            )
            response.raise_for_status()
            audio = response.content
    except httpx.HTTPError as exc:
        raise SpeechServiceError("TTS provider request failed") from exc

    if not audio:
        raise SpeechServiceError("TTS provider returned empty audio")
    return audio, media_types.get(audio_format, "application/octet-stream")
