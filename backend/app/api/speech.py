"""ASR and TTS HTTP endpoints."""

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.schemas import AsrResponse, TtsRequest
from app.services.speech_service import (
    SpeechServiceError,
    speech_to_text,
    text_to_speech,
)


router = APIRouter()
MAX_AUDIO_BYTES = 20 * 1024 * 1024


@router.post("/speech/asr", response_model=AsrResponse)
async def recognize_speech(audio: UploadFile = File(...)):
    """Receive a browser recording and return recognized text."""
    content = await audio.read(MAX_AUDIO_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="上传的音频为空")
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="音频不能超过 20MB")

    try:
        text = speech_to_text(
            content,
            filename=audio.filename or "recording.webm",
            content_type=audio.content_type or "application/octet-stream",
        )
    except SpeechServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return AsrResponse(text=text)


@router.post("/speech/tts")
def synthesize_speech(request: TtsRequest):
    """Return synthesized audio bytes for an AI answer."""
    try:
        audio, media_type = text_to_speech(request.text)
    except SpeechServiceError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return Response(
        content=audio,
        media_type=media_type,
        headers={"Content-Disposition": 'inline; filename="answer-audio"'},
    )
