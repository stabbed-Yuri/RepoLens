from __future__ import annotations

import unittest

from backend.services.openai import OpenAIError
from backend.services.provider_router import ProviderRouter


class FakeProvider:
    def __init__(
        self,
        *,
        enabled: bool = True,
        text: str = "ok",
        embeddings: list[list[float]] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.enabled = enabled
        self.text = text
        self.embeddings = embeddings or [[1.0, 0.0]]
        self.error = error
        self.prompts: list[str] = []

    def generate_text(
        self,
        *,
        user_prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_output_tokens: int = 400,
    ) -> str:
        _ = (system_prompt, temperature, max_output_tokens)
        self.prompts.append(user_prompt)
        if self.error:
            raise self.error
        return self.text

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.prompts.extend(texts)
        if self.error:
            raise self.error
        return self.embeddings[: len(texts)]


class ProviderRouterTests(unittest.TestCase):
    def test_gemini_429_falls_back_to_openai_with_same_prompt(self) -> None:
        gemini = FakeProvider(error=OpenAIError("rate limited", status_code=429))
        openai = FakeProvider(text="fallback answer")
        router = ProviderRouter(openai=openai, gemini=gemini)

        result = router.generate_text(
            preferred_provider="gemini",
            user_prompt="same compact context",
        )

        self.assertEqual(result.text, "fallback answer")
        self.assertEqual(result.provider_used, "openai")
        self.assertTrue(result.fallback_used)
        self.assertIn("quota", result.fallback_reason or "")
        self.assertEqual(openai.prompts, ["same compact context"])

    def test_missing_gemini_key_falls_back_to_openai(self) -> None:
        gemini = FakeProvider(enabled=False)
        openai = FakeProvider(text="openai answer")
        router = ProviderRouter(openai=openai, gemini=gemini)

        result = router.generate_text(preferred_provider="gemini", user_prompt="prompt")

        self.assertEqual(result.provider_used, "openai")
        self.assertTrue(result.fallback_used)
        self.assertIn("API key", result.fallback_reason or "")

    def test_openai_429_falls_back_to_gemini(self) -> None:
        openai = FakeProvider(error=OpenAIError("rate limited", status_code=429))
        gemini = FakeProvider(text="gemini answer")
        router = ProviderRouter(openai=openai, gemini=gemini)

        result = router.generate_text(preferred_provider="openai", user_prompt="prompt")

        self.assertEqual(result.text, "gemini answer")
        self.assertEqual(result.provider_used, "gemini")
        self.assertTrue(result.fallback_used)

    def test_both_embedding_providers_fail_uses_hash(self) -> None:
        openai = FakeProvider(error=RuntimeError("down"))
        gemini = FakeProvider(error=RuntimeError("down"))
        router = ProviderRouter(openai=openai, gemini=gemini)

        result = router.embed_texts(preferred_provider="openai", texts=["hello world"])

        self.assertEqual(result.provider_used, "hash")
        self.assertTrue(result.fallback_used)
        self.assertEqual(len(result.embeddings or []), 1)


if __name__ == "__main__":
    unittest.main()
