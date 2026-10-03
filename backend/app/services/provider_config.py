"""Environment settings for compatible HTTP providers."""

import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[3] / ".env")


def provider_config(prefix: str) -> dict | None:
    provider = os.getenv(f"{prefix}_PROVIDER", "disabled").strip().lower()
    key = os.getenv(f"{prefix}_API_KEY", "").strip()
    model = os.getenv(f"{prefix}_MODEL", "").strip()
    url = os.getenv(f"{prefix}_BASE_URL", "").strip().rstrip("/")

    try:
        timeout = float(os.getenv(f"{prefix}_TIMEOUT", "60"))
    except ValueError:
        return None

    supported_providers = {"openai_compatible"}
    if prefix in {"ASR", "TTS"}:
        supported_providers.add("aliyun_bailian")

    if provider not in supported_providers or not all((key, model, url)) or not 0 < timeout <= 300:
        return None
    allowed_url_schemes = ("https://", "http://")
    if prefix == "TTS" and provider == "aliyun_bailian":
        allowed_url_schemes = ("wss://",)
    if not url.startswith(allowed_url_schemes):
        return None

    config = {
        "provider": provider,
        "key": key,
        "model": model,
        "url": url,
        "timeout": timeout,
    }
    if prefix == "TTS":
        configured_voice = os.getenv("TTS_VOICE", "").strip()
        audio_format = os.getenv("TTS_FORMAT", "mp3").strip().lower() or "mp3"
        if provider == "aliyun_bailian":
            if not configured_voice or audio_format != "mp3":
                return None
            config["voice"] = configured_voice
        else:
            config["voice"] = configured_voice or "alloy"
        config["format"] = audio_format
    return config
