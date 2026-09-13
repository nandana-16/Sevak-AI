"""Bhashini (ULCA) client - the Government of India's language platform.

Two calls, not one:

  1. **Config.** Ask the MeitY auth service which model serves a given task and
     language, and get back a short-lived inference endpoint plus the header to
     authenticate against it.
  2. **Inference.** Post the audio to that endpoint.

Step 1's answer is cached, because it is the same for every visit in a given
language and re-fetching it would double the latency of every transcription.

Why Bhashini at all, when Groq's Whisper already works: it is the government's
own platform, trained on Indian speech, and for a system meant to plug into the
National Health Mission the provenance of the language model is not a detail.
It also keeps the audio inside Indian government infrastructure, which matters
for health data. Whisper stays available as a fallback.
"""

from __future__ import annotations

import base64
import logging
import time
from pathlib import Path

import httpx

from app.core.config import settings

log = logging.getLogger("sevakai.bhashini")

AUTH_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"

# The config rarely changes and costs a round trip, so hold it for an hour.
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL_SECONDS = 3600


class BhashiniError(RuntimeError):
    pass


def configured() -> bool:
    return bool(settings.bhashini_api_key and settings.bhashini_user_id)


def pipeline_config(task: str, source: str, target: str | None = None) -> dict | None:
    """Fetch (and cache) the pipeline config for a task and language."""
    key = f"{task}:{source}:{target or ''}"
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]

    if not configured():
        return None

    language: dict = {"sourceLanguage": source}
    if target:
        language["targetLanguage"] = target

    try:
        response = httpx.post(
            AUTH_URL,
            json={
                "pipelineTasks": [{"taskType": task, "config": {"language": language}}],
                "pipelineRequestConfig": {"pipelineId": settings.bhashini_pipeline_id},
            },
            headers={
                "userID": settings.bhashini_user_id,
                "ulcaApiKey": settings.bhashini_api_key,
                "Content-Type": "application/json",
            },
            timeout=60,
        )
    except Exception as exc:
        raise BhashiniError(f"Could not reach Bhashini: {exc}") from exc

    if response.status_code != 200:
        raise BhashiniError(
            f"Bhashini rejected the pipeline request (HTTP {response.status_code}): "
            f"{response.text[:200]}"
        )

    data = response.json()
    _CACHE[key] = (time.time(), data)
    return data


def service_id(config: dict, task: str) -> str | None:
    for block in config.get("pipelineResponseConfig", []):
        if block.get("taskType") == task:
            entries = block.get("config") or []
            if entries:
                return entries[0].get("serviceId")
    return None


def inference_target(config: dict) -> tuple[str, dict]:
    """The endpoint to call, and the header that authenticates to it."""
    endpoint = config.get("pipelineInferenceAPIEndPoint", {})
    url = endpoint.get("callbackUrl")
    scheme = endpoint.get("inferenceApiKey", {})
    name, value = scheme.get("name"), scheme.get("value")
    if not url or not name or not value:
        raise BhashiniError("Bhashini did not return a usable inference endpoint")
    return url, {name: value, "Content-Type": "application/json"}


def transcribe(path: Path, language: str = "hi") -> str:
    """Speech to text. Returns Devanagari for Hindi, as the recogniser does."""
    source = (language or "hi").split("-")[0]
    config = pipeline_config("asr", source)
    if config is None:
        raise BhashiniError("Bhashini credentials are not configured")

    asr_service = service_id(config, "asr")
    if not asr_service:
        raise BhashiniError(f"Bhashini has no ASR model for '{source}'")

    url, headers = inference_target(config)
    audio_b64 = base64.b64encode(path.read_bytes()).decode()

    payload = {
        "pipelineTasks": [{
            "taskType": "asr",
            "config": {
                "language": {"sourceLanguage": source},
                "serviceId": asr_service,
                "audioFormat": _audio_format(path),
                "samplingRate": 16000,
            },
        }],
        "inputData": {"audio": [{"audioContent": audio_b64}]},
    }

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=180)
    except Exception as exc:
        raise BhashiniError(f"Bhashini transcription failed: {exc}") from exc

    if response.status_code != 200:
        raise BhashiniError(
            f"Bhashini ASR returned HTTP {response.status_code}: {response.text[:200]}"
        )

    try:
        blocks = response.json()["pipelineResponse"]
        for block in blocks:
            if block.get("taskType") == "asr" or "output" in block:
                text = (block.get("output") or [{}])[0].get("source", "")
                if text:
                    return text.strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise BhashiniError(f"Unexpected Bhashini response shape: {exc}") from exc

    raise BhashiniError("Bhashini returned no transcript")


def _audio_format(path: Path) -> str:
    """Bhashini names formats by extension. The app records .m4a (AAC in MP4),
    which Bhashini does not accept, so that case is converted before we get
    here - see services/stt.py."""
    suffix = path.suffix.lower().lstrip(".")
    return {"wav": "wav", "flac": "flac", "mp3": "mp3", "ogg": "ogg"}.get(suffix, "wav")
