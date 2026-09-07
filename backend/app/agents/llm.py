"""LLM access for the agents.

Two rules this module exists to enforce:

1. The pipeline never hard-fails because an API was down. Every agent has a
   deterministic rule-based fallback, so a worker standing in a courtyard
   always gets a usable answer.
2. A fallback is never silent. When rules stand in for the model, the step
   name is recorded and travels all the way to the phone screen, so nobody
   mistakes canned output for real clinical reasoning during a demo.
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field

from app.core.config import settings

log = logging.getLogger("sevakai.llm")


@dataclass
class LLMResult:
    data: dict
    degraded: bool = False
    reason: str | None = None
    latency_ms: int = 0
    model: str | None = None
    tokens: int = 0


@dataclass
class LLMUsage:
    """Per-visit bookkeeping: which steps degraded, and what it cost.

    Token count matters operationally, not just for accounting: the free tier
    is capped per minute, so knowing a visit costs ~N tokens tells you how
    many visits a demo can do back to back before it starts queueing.
    """

    degraded_steps: list[str] = field(default_factory=list)
    total_tokens: int = 0

    def note(self, step: str, reason: str) -> None:
        entry = f"{step}: {reason}"
        if entry not in self.degraded_steps:
            self.degraded_steps.append(entry)

    def add_tokens(self, count: int) -> None:
        self.total_tokens += count


def _extract_json(text: str) -> dict:
    """Models occasionally wrap JSON in prose or a fenced block."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Model did not return JSON: {text[:200]}")


class GroqClient:
    def __init__(self) -> None:
        from groq import Groq

        self._client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model
        self._supports_reasoning_effort = True

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 3000,
        temperature: float = 0.1,
        reasoning_effort: str | None = None,
    ) -> dict:
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # gpt-oss models spend most of their completion budget on hidden
        # reasoning tokens. Turning that down is the single biggest latency
        # lever we have, and for extraction it costs no accuracy.
        if reasoning_effort and self._supports_reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort

        try:
            response = self._client.chat.completions.create(**kwargs)
        except Exception as exc:
            if reasoning_effort and _is_unsupported_param(str(exc)):
                # Model does not take the parameter; drop it permanently.
                self._supports_reasoning_effort = False
                kwargs.pop("reasoning_effort", None)
                response = self._client.chat.completions.create(**kwargs)
            else:
                raise

        choice = response.choices[0]
        if choice.finish_reason == "length":
            # Truncated mid-JSON. Say so plainly rather than surfacing a
            # confusing parse error two frames up.
            raise ValueError("response truncated at max_tokens")
        tokens = getattr(response.usage, "total_tokens", 0) or 0
        return _extract_json(choice.message.content or ""), tokens


class LLM:
    """Front door for the agents. Retries once, then gives up gracefully."""

    def __init__(self) -> None:
        self.provider = settings.llm_provider
        self._client: GroqClient | None = None
        if self.provider == "groq" and settings.groq_api_key:
            try:
                self._client = GroqClient()
            except Exception as exc:  # pragma: no cover - import/credential issues
                log.warning("Groq unavailable, falling back to rules: %s", exc)
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def json(
        self,
        step: str,
        system: str,
        user: str,
        usage: LLMUsage,
        *,
        max_tokens: int = 3000,
        temperature: float = 0.1,
        reasoning_effort: str | None = "low",
    ) -> LLMResult:
        if self._client is None:
            usage.note(step, "no LLM configured, used rules")
            return LLMResult({}, degraded=True, reason="no LLM configured")

        started = time.time()
        last_error: Exception | None = None

        for attempt in (1, 2):
            try:
                data, tokens = self._client.complete_json(
                    system,
                    user,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    reasoning_effort=reasoning_effort,
                )
                usage.add_tokens(tokens)
                return LLMResult(
                    data,
                    latency_ms=int((time.time() - started) * 1000),
                    model=self._client.model,
                    tokens=tokens,
                )
            except Exception as exc:
                last_error = exc
                message = str(exc)
                log.warning("LLM %s attempt %d failed: %s", step, attempt, message[:200])
                if attempt == 1 and _is_retryable(message):
                    time.sleep(_retry_delay(message))
                    continue
                break

        reason = _short_reason(last_error)
        usage.note(step, f"{reason}, used rules")
        return LLMResult(
            {},
            degraded=True,
            reason=reason,
            latency_ms=int((time.time() - started) * 1000),
        )


def _is_unsupported_param(message: str) -> bool:
    lowered = message.lower()
    return "reasoning_effort" in lowered and (
        "unsupported" in lowered or "not supported" in lowered
        or "unrecognized" in lowered or "invalid" in lowered
    )


def _is_retryable(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in ("rate limit", "429", "timeout", "503", "502", "overloaded",
                      "truncated", "did not return json")
    )


def _retry_delay(message: str) -> float:
    """Honour the provider's own suggested wait when it gives one."""
    match = re.search(r"try again in ([\d.]+)s", message, re.IGNORECASE)
    if match:
        return min(float(match.group(1)) + 0.5, 20.0)
    return 2.0


def _short_reason(error: Exception | None) -> str:
    if error is None:
        return "LLM unavailable"
    message = str(error)
    lowered = message.lower()
    if "rate limit" in lowered or "429" in lowered:
        return "LLM rate limit reached"
    if "timeout" in lowered:
        return "LLM timed out"
    if "auth" in lowered or "401" in lowered or "invalid api key" in lowered:
        return "LLM credentials rejected"
    if "truncated" in lowered:
        return "LLM response was cut short"
    if "did not return json" in lowered:
        return "LLM returned malformed output"
    return "LLM error"


_llm: LLM | None = None


def get_llm() -> LLM:
    global _llm
    if _llm is None:
        _llm = LLM()
    return _llm
