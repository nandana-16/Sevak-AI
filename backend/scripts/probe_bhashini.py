"""Discover what Bhashini's API actually returns, before writing code against it.

Bhashini (ULCA) works in two steps and the details matter:

  1. Ask the auth service for a *pipeline config* - which model to use for the
     task and language you want, plus a short-lived inference endpoint and the
     header to authenticate against it.
  2. Call that inference endpoint with the audio.

The shape of step 1's response decides everything in step 2, so this script
prints it rather than assuming it.

Run:  python -m scripts.probe_bhashini
"""

from __future__ import annotations

import json
import sys
import warnings

warnings.filterwarnings("ignore")

import httpx

from app.core.config import settings

AUTH_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"


def probe(task: str, source: str = "hi", target: str | None = None) -> dict | None:
    config: dict = {"language": {"sourceLanguage": source}}
    if target:
        config["language"]["targetLanguage"] = target

    payload = {
        "pipelineTasks": [{"taskType": task, "config": config}],
        "pipelineRequestConfig": {"pipelineId": settings.bhashini_pipeline_id},
    }
    headers = {
        "userID": settings.bhashini_user_id,
        "ulcaApiKey": settings.bhashini_api_key,
        "Content-Type": "application/json",
    }

    print(f"\n=== {task}  ({source}{' -> ' + target if target else ''}) ===")
    try:
        response = httpx.post(AUTH_URL, json=payload, headers=headers, timeout=60)
    except Exception as exc:
        print(f"  request failed: {type(exc).__name__}: {exc}")
        return None

    print(f"  HTTP {response.status_code}")
    if response.status_code != 200:
        print(f"  body: {response.text[:400]}")
        return None

    data = response.json()

    # What can we actually call, and how do we authenticate to it?
    endpoint = data.get("pipelineInferenceAPIEndPoint", {})
    print(f"  callbackUrl : {endpoint.get('callbackUrl')}")
    scheme = endpoint.get("inferenceApiKey", {})
    print(f"  auth header : {scheme.get('name')} = {str(scheme.get('value'))[:22]}...")
    print(f"  async only  : {endpoint.get('isMultilingualEnabled')} / "
          f"schema={bool(endpoint.get('inferenceApiKey'))}")

    for config_block in data.get("pipelineResponseConfig", []):
        print(f"  task        : {config_block.get('taskType')}")
        for entry in config_block.get("config", [])[:3]:
            service_id = entry.get("serviceId")
            lang = entry.get("language", {})
            print(f"     serviceId: {service_id}")
            print(f"     language : {lang}")
            # ASR entries advertise the audio formats they accept, which is
            # the thing most likely to bite: the app records AAC/M4A.
            for key in ("modelId", "supportedAudioFormats", "samplingRate", "domain"):
                if key in entry:
                    print(f"     {key}: {entry[key]}")
    return data


def main() -> int:
    if not settings.bhashini_api_key or not settings.bhashini_user_id:
        print("Bhashini credentials are not set in backend/.env")
        return 1

    print(f"userID    : {settings.bhashini_user_id[:8]}...")
    print(f"pipelineId: {settings.bhashini_pipeline_id}")

    asr = probe("asr", "hi")
    probe("translation", "hi", "en")

    if asr:
        out = "bhashini_asr_config.json"
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(asr, handle, indent=2, ensure_ascii=False)
        print(f"\nFull ASR config written to backend/{out}")
    return 0 if asr else 1


if __name__ == "__main__":
    sys.exit(main())
