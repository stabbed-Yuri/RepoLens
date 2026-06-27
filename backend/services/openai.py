from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from backend.config import Settings, get_settings


class OpenAIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenAIService:
    """Minimal OpenAI Responses API client for interview generation/evaluation."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.openai_api_key)

    def generate_text(
        self,
        *,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 400,
    ) -> str:
        if not self.enabled:
            raise OpenAIError("OpenAI API key is not configured.")

        payload: dict[str, Any] = {
            "model": self.settings.openai_model,
            "input": self._build_input(user_prompt=user_prompt, system_prompt=system_prompt),
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        data = self._post_json("https://api.openai.com/v1/responses", payload)
        return self._extract_text(data)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self.enabled:
            raise OpenAIError("OpenAI API key is not configured.")
        if not texts:
            return []

        payload: dict[str, Any] = {
            "model": self.settings.openai_embedding_model,
            "input": texts,
        }
        data = self._post_json("https://api.openai.com/v1/embeddings", payload)
        vectors: list[list[float]] = []
        items = data.get("data", [])
        if not isinstance(items, list):
            return vectors
        for item in items:
            if not isinstance(item, dict):
                continue
            embedding = item.get("embedding", [])
            if isinstance(embedding, list):
                vectors.append([float(value) for value in embedding])
        return vectors

    def _build_input(self, *, user_prompt: str, system_prompt: str | None) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append(
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": system_prompt}],
                }
            )
        messages.append(
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}],
            }
        )
        return messages

    def _extract_text(self, payload: dict[str, Any]) -> str:
        output = payload.get("output", [])
        texts: list[str] = []
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content", [])
                if not isinstance(content, list):
                    continue
                for content_item in content:
                    if not isinstance(content_item, dict):
                        continue
                    if content_item.get("type") in {"output_text", "text"}:
                        text = content_item.get("text")
                        if isinstance(text, str) and text.strip():
                            texts.append(text.strip())
        if texts:
            return "\n".join(texts).strip()

        # Fallback for alternate response shapes.
        fallback = payload.get("output_text")
        if isinstance(fallback, str):
            return fallback.strip()
        return ""

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.settings.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.settings.openai_timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise OpenAIError(f"OpenAI API error: {exc.code} {detail}", status_code=exc.code) from exc
        except error.URLError as exc:
            raise OpenAIError(f"OpenAI API connection error: {exc.reason}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OpenAIError("OpenAI API returned invalid JSON.") from exc
