"""Configuration for remote chat and local retrieval models."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from super_ai.project_config import (
    ProjectConfigurationError,
    project_config_section,
    required_float,
    required_int,
    required_str,
)


class LlmConfigurationError(RuntimeError):
    """Raised when chat or retrieval model settings are invalid."""


@dataclass(frozen=True, slots=True)
class LocalEmbeddingConfig:
    """Local Sentence Transformers embedding settings."""

    provider: str
    model: str
    dimensions: int
    device: str
    batch_size: int
    normalize: bool


@dataclass(frozen=True, slots=True)
class LocalRerankConfig:
    """Local Sentence Transformers cross-encoder settings."""

    provider: str
    model: str
    device: str
    batch_size: int


@dataclass(frozen=True, slots=True)
class LlmProviderConfig:
    """Remote OpenAI-compatible chat plus local retrieval settings."""

    provider: str
    api_key: str = field(repr=False)
    base_url: str = ""
    chat_model: str = ""
    context_window_tokens: int = 0
    temperature: float = 0.2
    timeout_seconds: float = 120.0
    max_retries: int = 2
    embedding: LocalEmbeddingConfig = field(
        default_factory=lambda: LocalEmbeddingConfig(
            provider="sentence-transformers",
            model="BAAI/bge-m3",
            dimensions=1024,
            device="cpu",
            batch_size=8,
            normalize=True,
        )
    )
    rerank: LocalRerankConfig = field(
        default_factory=lambda: LocalRerankConfig(
            provider="sentence-transformers",
            model="BAAI/bge-reranker-v2-m3",
            device="cpu",
            batch_size=8,
        )
    )


def load_llm_provider_config(
    config_path: Path | str | None = None,
) -> LlmProviderConfig:
    """Load remote chat and local retrieval settings from project config."""
    try:
        chat = project_config_section("llm", config_path=config_path)
        retrieval = project_config_section("retrievalModels", config_path=config_path)
        embedding = _mapping_section(retrieval, "embedding")
        rerank = _mapping_section(retrieval, "rerank")
        chat_model = required_str(chat, "chatModel")
        model_profile = _model_profile(chat, chat_model)
        config = LlmProviderConfig(
            provider=required_str(chat, "provider"),
            api_key=required_str(chat, "apiKey"),
            base_url=required_str(chat, "baseUrl"),
            chat_model=chat_model,
            context_window_tokens=required_int(model_profile, "contextWindowTokens"),
            temperature=required_float(chat, "temperature"),
            timeout_seconds=required_float(chat, "timeoutSeconds"),
            max_retries=required_int(chat, "maxRetries"),
            embedding=LocalEmbeddingConfig(
                provider=required_str(embedding, "provider"),
                model=required_str(embedding, "model"),
                dimensions=required_int(embedding, "dimensions"),
                device=required_str(embedding, "device"),
                batch_size=required_int(embedding, "batchSize"),
                normalize=_required_bool(embedding, "normalize"),
            ),
            rerank=LocalRerankConfig(
                provider=required_str(rerank, "provider"),
                model=required_str(rerank, "model"),
                device=required_str(rerank, "device"),
                batch_size=required_int(rerank, "batchSize"),
            ),
        )
    except ProjectConfigurationError as exc:
        raise LlmConfigurationError(str(exc)) from exc

    for key, value in (
        ("contextWindowTokens", config.context_window_tokens),
        ("embedding.dimensions", config.embedding.dimensions),
        ("embedding.batchSize", config.embedding.batch_size),
        ("rerank.batchSize", config.rerank.batch_size),
    ):
        if value <= 0:
            raise LlmConfigurationError(f"Model configuration must be positive: {key}")
    if config.embedding.provider != "sentence-transformers":
        raise LlmConfigurationError("Unsupported local embedding provider")
    if config.rerank.provider != "sentence-transformers":
        raise LlmConfigurationError("Unsupported local rerank provider")
    return config


def _mapping_section(raw: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = raw.get(key)
    if not isinstance(value, Mapping):
        raise ProjectConfigurationError(f"Project config field must be an object: {key}")
    return {
        str(item_key): item_value
        for item_key, item_value in cast(Mapping[object, object], value).items()
    }


def _model_profile(raw: Mapping[str, object], model: str) -> Mapping[str, object]:
    profiles = _mapping_section(raw, "modelCapabilities")
    profile = profiles.get(model)
    if not isinstance(profile, Mapping):
        raise ProjectConfigurationError(
            f"No model capability profile configured for chatModel: {model}"
        )
    return {
        str(key): value
        for key, value in cast(Mapping[object, object], profile).items()
    }


def _required_bool(raw: Mapping[str, object], key: str) -> bool:
    value = raw.get(key)
    if not isinstance(value, bool):
        raise ProjectConfigurationError(f"Project config field must be a boolean: {key}")
    return value
