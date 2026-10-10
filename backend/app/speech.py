"""Speech-to-text is separate from the selected reasoning provider."""
from __future__ import annotations
import io

class SpeechError(RuntimeError):
    pass

def transcribe(audio: bytes, mime_type: str, client=None) -> str:
    if mime_type not in {"audio/webm", "audio/mp4", "audio/wav", "audio/mpeg", "audio/ogg"}:
        raise SpeechError("Unsupported microphone recording format")
    if not 100 <= len(audio) <= 10 * 1024 * 1024:
        raise SpeechError("Recording must contain 100 bytes to 10 MB")
    if client is None:
        from openai import OpenAI
        client = OpenAI(timeout=25, max_retries=0)
    extension = {"audio/webm": ".webm", "audio/mp4": ".m4a", "audio/wav": ".wav",
                 "audio/mpeg": ".mp3", "audio/ogg": ".ogg"}[mime_type]
    file = ("recording" + extension, io.BytesIO(audio), mime_type)
    result = client.audio.transcriptions.create(model="whisper-1", file=file, timeout=25)
    text = getattr(result, "text", None)
    if not isinstance(text, str) or not text.strip():
        raise SpeechError("Transcription service returned no text")
    return text.strip()
