from typing import TypedDict


class PipelineState(TypedDict, total=False):
    transcript: str
    language_code: str
    structured: dict
    risk_result: dict
    actions_result: dict
    hmis_fields: dict
    escalation_deadline: str | None
