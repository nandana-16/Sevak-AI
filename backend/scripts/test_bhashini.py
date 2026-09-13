"""Round-trip test of Bhashini: synthesise Hindi speech, then transcribe it back.

Using Bhashini's own TTS to produce the test audio means this needs no recorded
file and gives a known ground truth to compare the transcript against. It also
exercises the exact two-step ULCA flow the app will use.

Run:  python -m scripts.test_bhashini
"""

from __future__ import annotations

import base64
import sys
import warnings

warnings.filterwarnings("ignore")

import httpx

from app.core.config import settings
from app.services import bhashini

# A sentence an ASHA worker would actually say, with the clinical vocabulary
# that matters - this is what we care about the model getting right.
SENTENCE = "मरीज़ को तीन दिन से बुख़ार है और सर दर्द भी है।"


def synthesise(text: str) -> bytes | None:
    """Bhashini TTS, used only to manufacture a test clip."""
    config = bhashini.pipeline_config("tts", "hi")
    if config is None:
        return None
    service_id = bhashini.service_id(config, "tts")
    url, headers = bhashini.inference_target(config)

    payload = {
        "pipelineTasks": [{
            "taskType": "tts",
            "config": {
                "language": {"sourceLanguage": "hi"},
                "serviceId": service_id,
                "gender": "female",
                "samplingRate": 16000,
            },
        }],
        "inputData": {"input": [{"source": text}]},
    }
    response = httpx.post(url, json=payload, headers=headers, timeout=120)
    print(f"  TTS HTTP {response.status_code}  (service {service_id})")
    if response.status_code != 200:
        print(f"    {response.text[:300]}")
        return None
    audio = response.json()["pipelineResponse"][0]["audio"][0]["audioContent"]
    return base64.b64decode(audio)


def main() -> int:
    if not settings.bhashini_api_key:
        print("No Bhashini credentials in backend/.env")
        return 1

    print("1. Synthesising a Hindi test clip with Bhashini TTS")
    print(f'   text: "{SENTENCE}"')
    wav = synthesise(SENTENCE)
    if not wav:
        print("   TTS unavailable - cannot build a test clip")
        return 1

    path = settings.audio_path / "bhashini_test.wav"
    path.write_bytes(wav)
    header = wav[:4]
    print(f"   wrote {len(wav) // 1024} KB to {path.name} (header {header!r})")

    print("\n2. Transcribing it back with Bhashini ASR")
    try:
        transcript = bhashini.transcribe(path, "hi")
    except Exception as exc:
        print(f"   FAILED: {type(exc).__name__}: {exc}")
        return 1

    print(f'   heard: "{transcript}"')

    # Judge on the clinical words, not on exact punctuation.
    expected = ["बुख़ार", "बुखार", "सर", "दर्द", "तीन", "दिन"]
    hits = [w for w in expected if w in transcript]
    print(f"\n   matched {len(hits)} key words: {hits}")
    ok = len(hits) >= 3
    print("\n" + ("Bhashini ASR works" if ok else "Transcript did not match well"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
