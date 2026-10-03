"""Speech recognition and synthesis provider clients."""

import base64
from pathlib import Path

import httpx

from app.services.provider_config import provider_config


class SpeechServiceError(RuntimeError):
    """语音服务未配置、请求失败或响应无效。"""


def _create_client(timeout: float) -> httpx.Client:
    """为自动测试提供安装 httpx.MockTransport 的替换点。"""
    return httpx.Client(timeout=timeout)


def _create_aliyun_synthesizer(config: dict):
    """Create a DashScope synthesizer; kept as a seam for SDK-mocked tests."""
    import dashscope
    from dashscope.audio.tts_v2 import SpeechSynthesizer

    dashscope.api_key = config["key"]
    dashscope.base_websocket_api_url = config["url"]
    return SpeechSynthesizer(
        model=config["model"],
        voice=config["voice"],
    )


def _openai_speech_to_text(
    config: dict,
    audio: bytes,
    filename: str,
    content_type: str,
) -> str:
    """调用 OpenAI-compatible multipart ASR 接口。"""
    with _create_client(config["timeout"]) as client:
        response = client.post(
            f'{config["url"]}/audio/transcriptions',
            headers={"Authorization": f'Bearer {config["key"]}'},
            data={"model": config["model"]},
            files={"file": (filename, audio, content_type)},
        )
        response.raise_for_status()
        return response.json()["text"]


def _aliyun_audio_metadata(filename: str, content_type: str) -> tuple[str, str]:
    """Return the DashScope format and normalized MIME type for a browser upload."""
    normalized_type = content_type.split(";", 1)[0].strip().lower()
    mime_to_format = {
        "audio/aac": "aac",
        "audio/amr": "amr",
        "audio/flac": "flac",
        "audio/mp4": "m4a",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/ogg": "ogg",
        "audio/opus": "opus",
        "audio/wav": "wav",
        "audio/webm": "webm",
        "audio/x-flac": "flac",
        "audio/x-m4a": "m4a",
        "audio/x-wav": "wav",
        "video/webm": "webm",
    }
    extension_to_format = {
        "aac": "aac",
        "amr": "amr",
        "flac": "flac",
        "m4a": "m4a",
        "mp3": "mp3",
        "ogg": "ogg",
        "opus": "opus",
        "wav": "wav",
        "webm": "webm",
    }
    format_to_mime = {
        "aac": "audio/aac",
        "amr": "audio/amr",
        "flac": "audio/flac",
        "m4a": "audio/mp4",
        "mp3": "audio/mpeg",
        "ogg": "audio/ogg",
        "opus": "audio/opus",
        "wav": "audio/wav",
        "webm": "audio/webm",
    }

    audio_format = mime_to_format.get(normalized_type)
    if not audio_format:
        extension = Path(filename).suffix.lstrip(".").lower()
        audio_format = extension_to_format.get(extension)
    if not audio_format:
        raise SpeechServiceError("Unsupported audio format for Aliyun Bailian ASR")

    data_uri_type = normalized_type if normalized_type in mime_to_format else format_to_mime[audio_format]
    if data_uri_type == "video/webm":
        data_uri_type = "audio/webm"
    return audio_format, data_uri_type


def _aliyun_speech_to_text(
    config: dict,
    audio: bytes,
    filename: str,
    content_type: str,
) -> str:
    """调用阿里云百炼 Qwen-Audio JSON ASR 接口。"""
    audio_format, data_uri_type = _aliyun_audio_metadata(filename, content_type)
    encoded_audio = base64.b64encode(audio).decode("ascii")
    data_uri = f"data:{data_uri_type};base64,{encoded_audio}"

    with _create_client(config["timeout"]) as client:
        response = client.post(
            config["url"],
            headers={
                "Authorization": f'Bearer {config["key"]}',
                "Content-Type": "application/json",
                "X-DashScope-SSE": "disable",
            },
            json={
                "model": config["model"],
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_audio",
                                    "input_audio": {"data": data_uri},
                                }
                            ],
                        }
                    ]
                },
                "parameters": {"format": audio_format},
            },
        )
        response.raise_for_status()
        return response.json()["output"]["text"]


def speech_to_text(
    audio: bytes,
    filename: str = "recording.webm",
    content_type: str = "audio/webm",
) -> str:
    """根据 ASR_PROVIDER 调用 OpenAI-compatible 或阿里云百炼语音识别。"""
    config = provider_config("ASR")
    if not config:
        raise SpeechServiceError("ASR service is not configured")
    if not audio:
        raise SpeechServiceError("Audio file is empty")

    try:
        if config.get("provider") == "aliyun_bailian":
            text = _aliyun_speech_to_text(config, audio, filename, content_type)
        else:
            text = _openai_speech_to_text(config, audio, filename, content_type)
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise SpeechServiceError("ASR provider request failed") from exc

    if not isinstance(text, str) or not text.strip():
        raise SpeechServiceError("ASR provider returned empty text")
    return text.strip()


def _openai_text_to_speech(config: dict, text: str) -> tuple[bytes, str]:
    """调用 OpenAI-compatible TTS 接口。"""
    audio_format = config.get("format", "mp3")
    media_types = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "opus": "audio/ogg",
        "aac": "audio/aac",
        "flac": "audio/flac",
    }
    with _create_client(config["timeout"]) as client:
        response = client.post(
            f'{config["url"]}/audio/speech',
            headers={"Authorization": f'Bearer {config["key"]}'},
            json={
                "model": config["model"],
                "voice": config["voice"],
                "input": text,
                "response_format": audio_format,
            },
        )
        response.raise_for_status()
        return response.content, media_types.get(audio_format, "application/octet-stream")


def _aliyun_text_to_speech(config: dict, text: str) -> tuple[bytes, str]:
    """调用阿里云百炼 Qwen-Audio TTS，并返回完整 MP3 音频。"""
    synthesizer = _create_aliyun_synthesizer(config)
    timeout_millis = int(config["timeout"] * 1000)
    return synthesizer.call(text, timeout_millis=timeout_millis), "audio/mpeg"


def text_to_speech(text: str) -> tuple[bytes, str]:
    """根据 TTS_PROVIDER 调用 OpenAI-compatible 或阿里云百炼语音合成。"""
    config = provider_config("TTS")
    if not config:
        raise SpeechServiceError("TTS service is not configured")
    if not text.strip():
        raise SpeechServiceError("Text is empty")

    try:
        if config.get("provider") == "aliyun_bailian":
            audio, media_type = _aliyun_text_to_speech(config, text)
        else:
            audio, media_type = _openai_text_to_speech(config, text)
    except SpeechServiceError:
        raise
    except Exception as exc:
        raise SpeechServiceError("TTS provider request failed") from exc

    if not audio:
        raise SpeechServiceError("TTS provider returned empty audio")
    return audio, media_type
