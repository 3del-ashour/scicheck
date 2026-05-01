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
    def __init__(self, model: str | None = None) -> None:
        s = get_settings()
        self._client = OpenAI(api_key=s.openai_api_key)
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
    """Used in tests. Returns canned responses based on substrings in `user`."""

    def __init__(self, responses: dict[str, str] | None = None) -> None:
        self.responses = responses or {}
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str, **kwargs) -> str:
        self.calls.append((system, user))
        for key, value in self.responses.items():
            if key in user:
                return value
        return ""
