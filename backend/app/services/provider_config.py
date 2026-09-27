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
    if provider != "openai_compatible" or not all((key, model, url)) or not 0 < timeout <= 300:
        return None
    if not url.startswith(("https://", "http://")):
        return None
    config = {"key": key, "model": model, "url": url, "timeout": timeout}
    if prefix == "TTS":
        config["voice"] = os.getenv("TTS_VOICE", "alloy").strip() or "alloy"
        config["format"] = os.getenv("TTS_FORMAT", "mp3").strip().lower() or "mp3"
    return config
