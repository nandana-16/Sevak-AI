"""Speech to text for audio that was captured offline.

Live capture uses Android's on-device SpeechRecognizer, which costs nothing,
needs no key, and works without a network once the Hindi language pack is
installed - so the phone normally sends text, not audio.

Audio reaches this module only when the on-device recogniser could not run: no
language pack, or a recording made in airplane mode on a device where offline
recognition is unavailable. Those files sit in the phone's queue and are
transcribed here when they finally sync.

Providers, in the order they are worth using:

  bhashini      The Government of India's own platform (ai4bharat conformer
                models). Best provenance for an NHM-facing system, trained on
                Indian speech, and the audio stays inside government
                infrastructure. Needs WAV - see the conversion note below.
  groq_whisper  whisper-large-v3. Accepts the app's audio as-is, good on
                code-mixed speech, and the automatic fallback when Bhashini is
                unreachable.
  whisper       faster-whisper running locally. No network, no key.
  mock          A canned transcript, so the pipeline runs with nothing set up.
"""

from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import settings
from app.services import bhashini

log = logging.getLogger("sevakai.stt")

SUPPORTED = {"hi", "en", "hi-IN", "en-IN"}

# Formats Bhashini's ASR endpoint accepts. Anything else is converted first.
BHASHINI_NATIVE = {".wav", ".flac"}


class TranscriptionError(RuntimeError):
    pass


def transcribe(path: Path, language: str = "hi") -> str:
    provider = settings.stt_provider

    if provider == "bhashini":
        try:
            return _bhashini(path, language)
        except Exception as exc:
            # Falling back rather than failing: a queued visit that reaches the
            # server should not be lost because one provider is down. The
            # substitution is logged, and the pipeline records the step as
            # degraded, so it is never silent.
            log.warning("Bhashini failed (%s); falling back to Whisper", exc)
            if settings.groq_api_key:
                return _groq_whisper(path, language)
            raise TranscriptionError(str(exc)) from exc

    if provider == "groq_whisper":
        return _groq_whisper(path, language)
    if provider == "whisper":
        return _local_whisper(path, language)
    return _mock(path)


# ---------------------------------------------------------------------------
# Bhashini
# ---------------------------------------------------------------------------

def _bhashini(path: Path, language: str) -> str:
    """Bhashini ASR, converting the audio first if needed.

    The phone records AAC in an MP4 container because it is roughly fourteen
    times smaller than the equivalent WAV - 13 KB against 190 KB for the same
    clip - and that difference is the whole point when a day's queue has to go
    up over a weak rural connection. Bhashini's endpoint rejects that container
    (HTTP 500), so the conversion happens here, on the server, where bandwidth
    and CPU are cheap. The constrained link keeps carrying the small file.
    """
    source = path
    temporary: Path | None = None

    if path.suffix.lower() not in BHASHINI_NATIVE:
        temporary = _to_wav(path)
        source = temporary

    try:
        return bhashini.transcribe(source, language)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _to_wav(path: Path) -> Path:
    """Decode any container PyAV can read into 16 kHz mono PCM WAV."""
    try:
        import av
    except ImportError as exc:
        raise TranscriptionError(
            "Converting this recording needs PyAV (pip install av), or set "
            "STT_PROVIDER=groq_whisper which accepts the app's audio directly"
        ) from exc

    target = path.with_suffix(".converted.wav")
    try:
        with av.open(str(path)) as container, av.open(str(target), "w") as out:
            stream = out.add_stream("pcm_s16le", rate=16000)
            stream.layout = "mono"
            resampler = av.audio.resampler.AudioResampler(
                format="s16", layout="mono", rate=16000
            )
            for frame in container.decode(audio=0):
                for resampled in resampler.resample(frame):
                    resampled.pts = None
                    for packet in stream.encode(resampled):
                        out.mux(packet)
            for packet in stream.encode(None):
                out.mux(packet)
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise TranscriptionError(f"Could not convert the recording: {exc}") from exc

    if not target.exists() or target.stat().st_size < 1024:
        target.unlink(missing_ok=True)
        raise TranscriptionError("Converted recording was empty")
    return target


# ---------------------------------------------------------------------------
# Whisper
# ---------------------------------------------------------------------------

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
