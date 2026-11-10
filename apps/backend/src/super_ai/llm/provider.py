"""OpenAI-compatible chat provider with independent local retrieval models."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Protocol, cast

from langchain_openai import ChatOpenAI

from super_ai.llm.config import LlmProviderConfig, load_llm_provider_config
from super_ai.llm.local_retrieval import LocalBgeEmbeddingModel, LocalBgeRerankModel
from super_ai.llm.rerank import RerankModel


class ChatModel(Protocol):
    """Minimal async chat model protocol used by business code."""

    async def ainvoke(self, input: object) -> object:
        """Invoke the chat model asynchronously."""
        ...


class EmbeddingModel(Protocol):
    """Minimal async embedding model protocol used by indexing code."""

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed document texts asynchronously."""
        ...


ModelFactory = Callable[[LlmProviderConfig], ChatModel]
EmbeddingFactory = Callable[[LlmProviderConfig], EmbeddingModel]
RerankFactory = Callable[[LlmProviderConfig], RerankModel]


class LlmProvider(Protocol):
    """Provider interface for swappable OpenAI-compatible models."""

    def create_chat_model(self, *, thinking: bool = True) -> ChatModel:
        """Create a configured chat model; `thinking=False` skips provider deep reasoning."""
        ...

    def create_embedding_model(self) -> EmbeddingModel:
        """Create a configured embedding model."""
        ...

    def create_rerank_model(self) -> RerankModel:
        """Create a configured text rerank model."""
        ...

    async def check_readiness(self) -> LlmReadinessResult:
        """Verify that the configured provider can answer a small request."""
        ...


@dataclass(frozen=True, slots=True)
class LlmReadinessResult:
    """Safe readiness result that never includes provider credentials."""

    ok: bool
    provider: str
    model: str
    base_url: str
    latency_ms: float
    error: str | None = None


class OpenAICompatibleProvider:
    """Remote chat provider with local embedding and reranking factories."""

    def __init__(
        self,
        config: LlmProviderConfig,
        model_factory: ModelFactory | None = None,
        embedding_factory: EmbeddingFactory | None = None,
        rerank_factory: RerankFactory | None = None,
    ) -> None:
        self._config = config
        self._model_factory = model_factory or _create_chat_openai_model
        self._uses_default_model_factory = model_factory is None
        self._embedding_factory = embedding_factory or _create_local_embedding_model
        self._rerank_factory = rerank_factory or _create_local_rerank_model

    @property
    def config(self) -> LlmProviderConfig:
        """Return the provider configuration."""
        return self._config

    def create_chat_model(self, *, thinking: bool = True) -> ChatModel:
        """Create the configured chat model; `thinking=False` disables DeepSeek reasoning."""
        if not thinking and self._uses_default_model_factory:
            return _create_chat_openai_model(self._config, thinking=False)
        return self._model_factory(self._config)

    def create_embedding_model(self) -> EmbeddingModel:
        """Create the configured local embedding model."""
        return self._embedding_factory(self._config)

    def create_rerank_model(self) -> RerankModel:
        """Create the configured local rerank model."""
        return self._rerank_factory(self._config)

    async def check_readiness(self) -> LlmReadinessResult:
        """Run a minimal async model request and return a secret-safe result."""
        started_at = monotonic()
        try:
            model = self.create_chat_model()
            await model.ainvoke("Return exactly: ready")
        except Exception as exc:
            return LlmReadinessResult(
                ok=False,
                provider=self._config.provider,
                model=self._config.chat_model,
                base_url=self._config.base_url,
                latency_ms=_elapsed_ms(started_at),
                error=_safe_error_message(exc, self._config.api_key),
            )

        return LlmReadinessResult(
            ok=True,
            provider=self._config.provider,
            model=self._config.chat_model,
            base_url=self._config.base_url,
            latency_ms=_elapsed_ms(started_at),
        )


def build_default_llm_provider(config_path: Path | str | None = None) -> LlmProvider:
    """Build the default configured LLM provider."""
    return OpenAICompatibleProvider(load_llm_provider_config(config_path=config_path))


def _create_chat_openai_model(config: LlmProviderConfig, *, thinking: bool = True) -> ChatModel:
    extra_body: dict[str, object] | None = (
        None if thinking else {"thinking": {"type": "disabled"}}
    )
    return cast(
        ChatModel,
        ChatOpenAI(
            api_key=lambda: config.api_key,
            base_url=config.base_url,
            model=config.chat_model,
            temperature=config.temperature,
            timeout=config.timeout_seconds,
            max_retries=config.max_retries,
            extra_body=extra_body,
        ),
    )


def _create_local_embedding_model(config: LlmProviderConfig) -> EmbeddingModel:
    return LocalBgeEmbeddingModel(config.embedding)


def _create_local_rerank_model(config: LlmProviderConfig) -> RerankModel:
    return LocalBgeRerankModel(config.rerank)


def _elapsed_ms(started_at: float) -> float:
    return round((monotonic() - started_at) * 1000, 3)


def _safe_error_message(exc: Exception, secret: str) -> str:
    message = str(exc)
    if secret:
        return message.replace(secret, "[redacted]")
    return message


# Backward-compatible import name for existing integrations.
QwenOpenAIProvider = OpenAICompatibleProvider
