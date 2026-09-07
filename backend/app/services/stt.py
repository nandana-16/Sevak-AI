"""Speech to text for audio that was captured offline.

Live capture uses Android's on-device SpeechRecognizer, which costs nothing,
needs no key, and works without a network once the Hindi language pack is
installed - so the phone normally sends text, not audio.

Audio reaches this module only in the case the on-device recogniser could not
run: no language pack, or a recording made in airplane mode on a device where
offline recognition is unavailable. Those files sit in the phone's queue and
are transcribed here when they finally sync.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import settings

log = logging.getLogger("sevakai.stt")

SUPPORTED = {"hi", "en", "hi-IN", "en-IN"}


class TranscriptionError(RuntimeError):
    pass


def transcribe(path: Path, language: str = "hi") -> str:
    provider = settings.stt_provider
    if provider == "groq_whisper":
        return _groq_whisper(path, language)
    if provider == "whisper":
        return _local_whisper(path, language)
    return _mock(path)


def _groq_whisper(path: Path, language: str) -> str:
    """whisper-large-v3 on Groq. Free tier, and markedly better on accented
    and code-mixed Hindi than the on-device recogniser."""
    from groq import Groq

    if not settings.groq_api_key:
        raise TranscriptionError("No Groq API key configured for transcription")

    client = Groq(api_key=settings.groq_api_key)
    with path.open("rb") as handle:
        response = client.audio.transcriptions.create(
            file=(path.name, handle.read()),
            model=settings.whisper_model,
            language=language.split("-")[0] if language else None,
            # Priming the decoder with the vocabulary it will actually hear
            # measurably reduces garbled clinical terms.
            prompt=(
                "ASHA health worker field notes. Terms: bukhar, sar dard, "
                "pet dard, ulti, dast, khansi, sujan, kamzori, chakkar, "
                "BP, Hb, IFA, ANC, tika, doodh, naabhi."
            ),
            temperature=0.0,
        )
    text = (response.text or "").strip()
    if not text:
        raise TranscriptionError("Transcription returned nothing")
    return text


def _local_whisper(path: Path, language: str) -> str:
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise TranscriptionError(
            "faster-whisper is not installed; pip install faster-whisper "
            "or set STT_PROVIDER=groq_whisper"
        ) from exc

    model = WhisperModel(settings.whisper_model, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(path), language=language.split("-")[0])
    return " ".join(segment.text.strip() for segment in segments).strip()


def _mock(path: Path) -> str:
    log.warning("STT_PROVIDER=mock: returning a canned transcript for %s", path.name)
    return (
        "Mareez ko do din se bukhar hai aur kamzori mahsoos ho rahi hai. "
        "Koi aur shikayat nahi hai."
    )
