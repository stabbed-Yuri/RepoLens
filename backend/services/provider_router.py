from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from backend.config import Settings, get_settings
from backend.services.gemini import GeminiError, GeminiService
from backend.services.openai import OpenAIError, OpenAIService
from backend.services.retrieval import HashEmbeddingProvider


ModelProvider = Literal["openai", "gemini"]


class TextProvider(Protocol):
    enabled: bool

    def generate_text(
        self,
        *,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 400,
    ) -> str:
        ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


@dataclass(slots=True)
class ProviderResult:
    provider_used: ModelProvider | Literal["hash"] | None
    fallback_used: bool = False
    fallback_reason: str | None = None


@dataclass(slots=True)
class TextResult(ProviderResult):
    text: str = ""


@dataclass(slots=True)
class EmbeddingResult(ProviderResult):
    embeddings: list[list[float]] | None = None


class ProviderRouter:
    """Route model calls to the preferred provider with one fallback attempt."""

    def __init__(
        self,
        *,
        openai: TextProvider | None = None,
        gemini: TextProvider | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.openai = openai or OpenAIService(settings=self.settings)
        self.gemini = gemini or GeminiService(settings=self.settings)
        self.hash_embeddings = HashEmbeddingProvider()

    def generate_text(
        self,
        *,
        preferred_provider: ModelProvider | None,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 400,
    ) -> TextResult:
        preferred = self.normalize_provider(preferred_provider)
        fallback_reason: str | None = None

        for provider in self._provider_order(preferred):
            service = self._service(provider)
            if not service.enabled:
                fallback_reason = fallback_reason or f"{provider} API key is not configured"
                continue
            try:
                text = service.generate_text(
                    user_prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
            except (OpenAIError, GeminiError, RuntimeError) as exc:
                fallback_reason = self._fallback_reason(provider, exc)
                continue
            return TextResult(
                text=text,
                provider_used=provider,
                fallback_used=provider != preferred,
                fallback_reason=fallback_reason if provider != preferred else None,
            )

        return TextResult(
            text="",
            provider_used=None,
            fallback_used=fallback_reason is not None,
            fallback_reason=fallback_reason or "No model provider is configured",
        )

    def embed_texts(
        self,
        *,
        preferred_provider: ModelProvider | None,
        texts: list[str],
    ) -> EmbeddingResult:
        preferred = self.normalize_provider(preferred_provider)
        fallback_reason: str | None = None

        for provider in self._provider_order(preferred):
            service = self._service(provider)
            if not service.enabled:
                fallback_reason = fallback_reason or f"{provider} API key is not configured"
                continue
            try:
                embeddings = service.embed_texts(texts)
                if len(embeddings) != len(texts) or any(not vector for vector in embeddings):
                    fallback_reason = f"{provider} returned incomplete embeddings"
                    continue
            except (OpenAIError, GeminiError, RuntimeError) as exc:
                fallback_reason = self._fallback_reason(provider, exc)
                continue
            return EmbeddingResult(
                embeddings=embeddings,
                provider_used=provider,
                fallback_used=provider != preferred,
                fallback_reason=fallback_reason if provider != preferred else None,
            )

        return EmbeddingResult(
            embeddings=self.hash_embeddings.embed_texts(texts),
            provider_used="hash",
            fallback_used=True,
            fallback_reason=fallback_reason or "No embedding provider is configured",
        )

    def alternate_provider(self, provider: ModelProvider | None) -> ModelProvider:
        return "gemini" if self.normalize_provider(provider) == "openai" else "openai"

    def normalize_provider(self, provider: ModelProvider | str | None) -> ModelProvider:
        return "gemini" if provider == "gemini" else "openai"

    def _provider_order(self, preferred: ModelProvider) -> list[ModelProvider]:
        alternate = self.alternate_provider(preferred)
        return [preferred, alternate]

    def _service(self, provider: ModelProvider) -> TextProvider:
        return self.gemini if provider == "gemini" else self.openai

    def _fallback_reason(self, provider: ModelProvider, exc: BaseException) -> str:
        status_code = getattr(exc, "status_code", None)
        detail = str(exc)
        if status_code == 429:
            return f"{provider} quota or rate limit reached"
        if status_code:
            return f"{provider} provider error {status_code}"
        if "timed out" in detail.lower() or "timeout" in detail.lower():
            return f"{provider} provider timed out"
        return f"{provider} provider unavailable"
