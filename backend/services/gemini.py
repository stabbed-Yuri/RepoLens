from __future__ import annotations

import json
from typing import Any
from urllib import error, parse, request

from backend.config import Settings, get_settings


class GeminiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class GeminiService:
    """Minimal Gemini REST client for text generation and embeddings."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(self.settings.gemini_api_key)

    def generate_text(
        self,
        *,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 400,
    ) -> str:
        if not self.enabled:
            raise RuntimeError("Gemini API key is not configured.")

        endpoint = self._model_endpoint(self.settings.gemini_model, "generateContent")
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        data = self._post_json(endpoint, payload)
        candidates = data.get("candidates", [])
        if not candidates:
            return ""
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        return "\n".join(item for item in text_parts if item).strip()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self.enabled:
            raise RuntimeError("Gemini API key is not configured.")

        endpoint = self._model_endpoint(self.settings.gemini_embedding_model, "embedContent")
        embeddings: list[list[float]] = []
        for text in texts:
            payload = {"content": {"parts": [{"text": text}]}}
            data = self._post_json(endpoint, payload)
            values = data.get("embedding", {}).get("values", [])
            if not isinstance(values, list):
                values = []
            embeddings.append([float(value) for value in values])
        return embeddings

    def _model_endpoint(self, model: str, method: str) -> str:
        encoded_key = parse.quote(self.settings.gemini_api_key or "", safe="")
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:{method}"
            f"?key={encoded_key}"
        )

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=self.settings.gemini_timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise GeminiError(f"Gemini API error: {exc.code} {detail}", status_code=exc.code) from exc
        except error.URLError as exc:
            raise GeminiError(f"Gemini API connection error: {exc.reason}") from exc
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise GeminiError("Gemini API returned invalid JSON.") from exc
