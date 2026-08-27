"""Pluggable speech-to-text provider.

Two ways audio becomes text in this system:
1. The client (worker web app) does STT itself via the browser's Web Speech API
   and sends `transcript` directly — no server-side STT needed at all. This is
   the default path today since it needs zero credentials and works offline-tolerant.
2. The client uploads raw audio (`audio_base64`) and the server transcribes it via
   this provider — swap STT_PROVIDER=bhashini and add credentials to go live with
   real Bhashini transcription in Hindi/Marathi/Tamil/Telugu/Bengali.
"""
import base64
from abc import ABC, abstractmethod

import httpx

from app.core.config import settings


class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_base64: str, language_code: str) -> str:
        raise NotImplementedError


class BhashiniProvider(STTProvider):
    """Thin wrapper around the Bhashini ULCA speech-to-text pipeline API.

    Requires BHASHINI_API_KEY / BHASHINI_USER_ID from https://bhashini.gov.in.
    """

    def transcribe(self, audio_base64: str, language_code: str) -> str:
        headers = {
            "userID": settings.bhashini_user_id,
            "ulcaApiKey": settings.bhashini_api_key,
            "Content-Type": "application/json",
        }
        pipeline_payload = {
            "pipelineTasks": [{
                "taskType": "asr",
                "config": {"language": {"sourceLanguage": language_code}},
            }],
            "pipelineRequestConfig": {"pipelineId": "64392f96daac500b55c543cd"},
        }
        with httpx.Client(timeout=15) as client:
            config_resp = client.post(settings.bhashini_endpoint, json=pipeline_payload, headers=headers)
            config_resp.raise_for_status()
            config = config_resp.json()

            compute_endpoint = config["pipelineInferenceAPIEndPoint"]["callbackUrl"]
            inference_key = config["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["value"]
            service_id = config["pipelineResponseConfig"][0]["config"][0]["serviceId"]

            infer_payload = {
                "pipelineTasks": [{
                    "taskType": "asr",
                    "config": {"language": {"sourceLanguage": language_code}, "serviceId": service_id},
                }],
                "inputData": {"audio": [{"audioContent": audio_base64}]},
            }
            infer_resp = client.post(
                compute_endpoint,
                json=infer_payload,
                headers={"Authorization": inference_key, "Content-Type": "application/json"},
            )
            infer_resp.raise_for_status()
            result = infer_resp.json()
            return result["pipelineResponse"][0]["output"][0]["source"]


class MockSTTProvider(STTProvider):
    """Decodes nothing — returns a clearly-labeled placeholder so it's obvious
    in the UI/demo that this path needs either a real transcript from the client
    or a real Bhashini key, rather than silently fabricating clinical text."""

    def transcribe(self, audio_base64: str, language_code: str) -> str:
        try:
            size = len(base64.b64decode(audio_base64))
        except Exception:
            size = 0
        return (
            f"[MOCK STT — no Bhashini credentials configured. Received {size} bytes of "
            f"audio in language '{language_code}'. Set STT_PROVIDER=bhashini in .env with "
            f"real credentials, or send `transcript` directly from client-side speech "
            f"recognition to use the real pipeline today.]"
        )


def get_stt_provider() -> STTProvider:
    if settings.stt_provider == "bhashini" and settings.bhashini_api_key:
        return BhashiniProvider()
    return MockSTTProvider()
