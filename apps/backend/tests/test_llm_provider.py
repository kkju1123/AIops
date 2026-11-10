from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from super_ai.llm import (
    EmbeddingModel,
    LlmConfigurationError,
    OpenAICompatibleProvider,
    load_llm_provider_config,
)


class FakeChatModel:
    def __init__(self, response: object | None = "ok", error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.inputs: list[object] = []

    async def ainvoke(self, input: object) -> object:
        self.inputs.append(input)
        if self.error is not None:
            raise self.error
        return self.response


class FakeEmbeddingModel:
    def __init__(self) -> None:
        self.inputs: list[list[str]] = []

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        self.inputs.append(texts)
        return [[1.0, 0.0, 0.5] for _text in texts]


def test_loads_deepseek_chat_and_local_retrieval_defaults() -> None:
    config = load_llm_provider_config()

    assert config.provider == "deepseek-openai"
    assert config.api_key.startswith("sk-")
    assert config.base_url == "https://api.deepseek.com"
    assert config.chat_model == "deepseek-flash"
    assert config.embedding.model == "BAAI/bge-m3"
    assert config.embedding.dimensions == 1024
    assert config.rerank.model == "BAAI/bge-reranker-v2-m3"
    assert config.context_window_tokens == 1_000_000
    assert config.temperature == 0.2
    assert config.timeout_seconds == 120.0
    assert config.max_retries == 2


def test_loads_explicit_project_config_file(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path,
        api_key="test-secret",
        base_url="https://example.test/v1",
        chat_model="qwen-test-chat",
        embedding_dimensions=768,
        temperature=0.7,
        timeout_seconds=45,
        max_retries=4,
    )

    config = load_llm_provider_config(config_path=config_path)

    assert config.api_key == "test-secret"
    assert config.base_url == "https://example.test/v1"
    assert config.chat_model == "qwen-test-chat"
    assert config.embedding.dimensions == 768
    assert config.temperature == 0.7
    assert config.timeout_seconds == 45.0
    assert config.max_retries == 4


def test_merges_user_project_config_file(tmp_path: Path) -> None:
    config_path = _write_config(
        tmp_path,
        api_key="",
        chat_model="",
    )
    (tmp_path / "user.project.json").write_text(
        json.dumps(
            {
                "llm": {
                    "apiKey": "merged-secret",
                    "chatModel": "merged-chat",
                    "modelCapabilities": {
                        "merged-chat": {"contextWindowTokens": 262144}
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    config = load_llm_provider_config(config_path=config_path)

    assert config.api_key == "merged-secret"
    assert config.chat_model == "merged-chat"
    assert config.context_window_tokens == 262144
    assert config.base_url == "https://api.deepseek.com"


def test_missing_api_key_fails_safely(
    tmp_path: Path,
) -> None:
    config_path = _write_config(tmp_path, api_key="")

    with pytest.raises(LlmConfigurationError) as exc_info:
        load_llm_provider_config(config_path=config_path)

    message = str(exc_info.value)
    assert "apiKey" in message
    assert "sk-" not in message


def test_chat_model_requires_matching_capability_profile(tmp_path: Path) -> None:
    config_path = _write_config(tmp_path, api_key="test-secret")
    raw_config = json.loads(config_path.read_text(encoding="utf-8"))
    raw_config["llm"]["chatModel"] = "unprofiled-model"
    config_path.write_text(json.dumps(raw_config), encoding="utf-8")

    with pytest.raises(LlmConfigurationError, match="unprofiled-model"):
        load_llm_provider_config(config_path=config_path)


def test_provider_constructs_model_with_config() -> None:
    config = load_llm_provider_config()
    captured: dict[str, Any] = {}

    def fake_factory(factory_config: object) -> FakeChatModel:
        captured["config"] = factory_config
        return FakeChatModel()

    provider = OpenAICompatibleProvider(config=config, model_factory=fake_factory)

    model = provider.create_chat_model()

    assert isinstance(model, FakeChatModel)
    assert captured["config"] is config


def test_chat_model_can_disable_deepseek_thinking() -> None:
    config = load_llm_provider_config()
    provider = OpenAICompatibleProvider(config=config)

    default_model: Any = provider.create_chat_model()
    fast_model: Any = provider.create_chat_model(thinking=False)

    assert default_model.extra_body is None
    assert fast_model.extra_body == {"thinking": {"type": "disabled"}}
    assert fast_model.model_name == config.chat_model


def test_provider_constructs_embedding_model_with_config() -> None:
    config = load_llm_provider_config()
    captured: dict[str, object] = {}

    def fake_embedding_factory(factory_config: object) -> EmbeddingModel:
        captured["config"] = factory_config
        return FakeEmbeddingModel()

    provider = OpenAICompatibleProvider(
        config=config,
        model_factory=lambda _: FakeChatModel(),
        embedding_factory=fake_embedding_factory,
    )

    model = provider.create_embedding_model()

    assert isinstance(model, FakeEmbeddingModel)
    assert captured["config"] is config


@pytest.mark.asyncio
async def test_readiness_succeeds_without_exposing_secret() -> None:
    config = load_llm_provider_config()
    fake_model = FakeChatModel(response="ready")
    provider = OpenAICompatibleProvider(config=config, model_factory=lambda _: fake_model)

    result = await provider.check_readiness()

    assert result.ok is True
    assert result.provider == "deepseek-openai"
    assert result.model == "deepseek-flash"
    assert result.base_url == "https://api.deepseek.com"
    assert result.error is None
    assert result.latency_ms >= 0
    assert config.api_key not in repr(result)
    assert fake_model.inputs


@pytest.mark.asyncio
async def test_readiness_failure_is_safe() -> None:
    config = load_llm_provider_config()
    provider = OpenAICompatibleProvider(
        config=config,
        model_factory=lambda _: FakeChatModel(error=RuntimeError("provider unavailable")),
    )

    result = await provider.check_readiness()

    assert result.ok is False
    assert result.error == "provider unavailable"
    assert config.api_key not in repr(result)


def test_provider_source_does_not_import_dashscope() -> None:
    source_root = Path("src/super_ai/llm")
    source = "\n".join(path.read_text(encoding="utf-8") for path in source_root.glob("*.py"))

    assert "dashscope" not in source.lower()


def _write_config(
    tmp_path: Path,
    *,
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    chat_model: str = "deepseek-flash",
    embedding_dimensions: int = 1024,
    context_window_tokens: int = 1_000_000,
    temperature: float = 0.2,
    timeout_seconds: int = 30,
    max_retries: int = 2,
) -> Path:
    config_path = tmp_path / "project.json"
    config_path.write_text(
        json.dumps(
            {
                "llm": {
                    "provider": "deepseek-openai",
                    "apiKey": api_key,
                    "baseUrl": base_url,
                    "chatModel": chat_model,
                    "modelCapabilities": {
                        chat_model: {"contextWindowTokens": context_window_tokens}
                    },
                    "temperature": temperature,
                    "timeoutSeconds": timeout_seconds,
                    "maxRetries": max_retries,
                },
                "retrievalModels": {
                    "embedding": {
                        "provider": "sentence-transformers",
                        "model": "BAAI/bge-m3",
                        "dimensions": embedding_dimensions,
                        "device": "cpu",
                        "batchSize": 8,
                        "normalize": True,
                    },
                    "rerank": {
                        "provider": "sentence-transformers",
                        "model": "BAAI/bge-reranker-v2-m3",
                        "device": "cpu",
                        "batchSize": 8,
                    },
                },
            }
        ),
        encoding="utf-8",
    )
    return config_path
