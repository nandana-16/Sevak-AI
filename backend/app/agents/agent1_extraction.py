"""Agent 1 — Voice Comprehension & Clinical Entity Extraction (FR-02)."""
from app.agents.llm_client import get_llm_client
from app.agents.prompts import EXTRACTION_SYSTEM_PROMPT


def run_extraction(transcript: str) -> dict:
    client = get_llm_client()
    return client.generate_json(EXTRACTION_SYSTEM_PROMPT, transcript)
