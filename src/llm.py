"""LLM client abstraction.

All agents take an LLMClient. Tests inject FakeClient.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from openai import OpenAI

from src.config import get_settings


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, **kwargs) -> str: ...


class OpenAIClient(LLMClient):
    """OpenAI-compatible chat client.

    Works against OpenAI itself or any OpenAI-compatible endpoint
    (Groq, Together, Ollama, vLLM, …) — set ``LLM_BASE_URL`` and an
    appropriate ``LLM_MODEL`` in the environment.
    """

    def __init__(self, model: str | None = None) -> None:
        s = get_settings()
        kwargs: dict = {"api_key": s.openai_api_key or "not-needed"}
        if s.llm_base_url:
            kwargs["base_url"] = s.llm_base_url
        self._client = OpenAI(**kwargs)
        self._model = model or s.llm_model

    def complete(self, system: str, user: str, **kwargs) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=kwargs.get("temperature", 0.0),
        )
        return resp.choices[0].message.content or ""


class FakeClient(LLMClient):
    """Used in tests. Returns canned responses based on substring matching.

    Each key in ``responses`` is checked (in insertion order) against both the
    user message and the system prompt — the first hit wins. This lets tests
    distinguish between agents that share user content (e.g. claim extractor
    and query-expansion both receive the bare claim) by keying on a unique
    phrase from the system prompt instead.
    """

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str, **kwargs) -> str:
        self.calls.append((system, user))
        for key, value in self.responses.items():
            if key in user or key in system:
                return value
        return ""
