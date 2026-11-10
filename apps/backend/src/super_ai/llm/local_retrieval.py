"""Lazy local BGE embedding and reranking adapters."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable, Sequence
from importlib import import_module
from threading import Lock
from typing import Protocol, cast

from super_ai.llm.config import LocalEmbeddingConfig, LocalRerankConfig
from super_ai.llm.rerank import LlmRerankError, RerankResult


class SentenceEncoderProtocol(Protocol):
    def encode(
        self,
        sentences: list[str],
        *,
        batch_size: int,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> object: ...


class CrossEncoderProtocol(Protocol):
    def predict(
        self,
        sentences: list[tuple[str, str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> object: ...


class SentenceEncoderConstructor(Protocol):
    def __call__(self, model_name: str, *, device: str) -> SentenceEncoderProtocol: ...


class CrossEncoderConstructor(Protocol):
    def __call__(self, model_name: str, *, device: str) -> CrossEncoderProtocol: ...


SentenceEncoderFactory = Callable[[LocalEmbeddingConfig], SentenceEncoderProtocol]
CrossEncoderFactory = Callable[[LocalRerankConfig], CrossEncoderProtocol]


class LocalBgeEmbeddingModel:
    """Asynchronous, lazy Sentence Transformers adapter for BGE-M3."""

    def __init__(
        self,
        config: LocalEmbeddingConfig,
        *,
        model_factory: SentenceEncoderFactory | None = None,
    ) -> None:
        self._config = config
        self._model_factory = model_factory or _create_sentence_encoder
        self._model: SentenceEncoderProtocol | None = None
        self._lock = Lock()

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch without blocking the async event loop."""
        if not texts:
            return []
        return await asyncio.to_thread(self._embed, texts)

    def _embed(self, texts: list[str]) -> list[list[float]]:
        raw_vectors = self._get_model().encode(
            texts,
            batch_size=self._config.batch_size,
            normalize_embeddings=self._config.normalize,
            show_progress_bar=False,
        )
        vectors = _matrix(raw_vectors)
        if len(vectors) != len(texts):
            raise RuntimeError("Embedding model returned an unexpected vector count.")
        if any(len(vector) != self._config.dimensions for vector in vectors):
            raise RuntimeError("Embedding model returned an unexpected vector dimension.")
        return vectors

    def _get_model(self) -> SentenceEncoderProtocol:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = self._model_factory(self._config)
        return self._model


class LocalBgeRerankModel:
    """Asynchronous, lazy cross-encoder adapter for BGE reranking."""

    def __init__(
        self,
        config: LocalRerankConfig,
        *,
        model_factory: CrossEncoderFactory | None = None,
    ) -> None:
        self._config = config
        self._model_factory = model_factory or _create_cross_encoder
        self._model: CrossEncoderProtocol | None = None
        self._lock = Lock()

    async def arerank(
        self,
        *,
        query: str,
        documents: Sequence[str],
        top_n: int,
    ) -> list[RerankResult]:
        normalized_query = query.strip()
        if not normalized_query or not documents:
            return []
        if top_n < 1 or top_n > len(documents):
            raise LlmRerankError("Rerank request is invalid.")
        return await asyncio.to_thread(
            self._rerank,
            normalized_query,
            list(documents),
            top_n,
        )

    def _rerank(self, query: str, documents: list[str], top_n: int) -> list[RerankResult]:
        raw_scores = self._get_model().predict(
            [(query, document) for document in documents],
            batch_size=self._config.batch_size,
            show_progress_bar=False,
        )
        scores = _vector(raw_scores)
        if len(scores) != len(documents):
            raise LlmRerankError("Rerank model returned an unexpected score count.")
        ranked = [
            RerankResult(index=index, relevance_score=_sigmoid(score))
            for index, score in enumerate(scores)
        ]
        ranked.sort(key=lambda result: (-result.relevance_score, result.index))
        return ranked[:top_n]

    def _get_model(self) -> CrossEncoderProtocol:
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = self._model_factory(self._config)
        return self._model


def _create_sentence_encoder(config: LocalEmbeddingConfig) -> SentenceEncoderProtocol:
    module = import_module("sentence_transformers")
    factory = cast(SentenceEncoderConstructor, module.SentenceTransformer)
    return factory(config.model, device=config.device)


def _create_cross_encoder(config: LocalRerankConfig) -> CrossEncoderProtocol:
    module = import_module("sentence_transformers")
    factory = cast(CrossEncoderConstructor, module.CrossEncoder)
    return factory(config.model, device=config.device)


def _matrix(value: object) -> list[list[float]]:
    converted = _tolist(value)
    if not isinstance(converted, list):
        raise RuntimeError("Embedding model returned an invalid result.")
    matrix: list[list[float]] = []
    for row in cast(list[object], converted):
        if not isinstance(row, list):
            raise RuntimeError("Embedding model returned an invalid result.")
        matrix.append(
            [_finite_float(item, "Embedding") for item in cast(list[object], row)]
        )
    return matrix


def _vector(value: object) -> list[float]:
    converted = _tolist(value)
    if not isinstance(converted, list):
        raise LlmRerankError("Rerank model returned an invalid result.")
    return [_finite_float(item, "Rerank") for item in cast(list[object], converted)]


def _tolist(value: object) -> object:
    tolist = getattr(value, "tolist", None)
    return tolist() if callable(tolist) else value


def _finite_float(value: object, label: str) -> float:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise RuntimeError(f"{label} model returned a non-numeric value.")
    converted = float(value)
    if not math.isfinite(converted):
        raise RuntimeError(f"{label} model returned a non-finite value.")
    return converted


def _sigmoid(value: float) -> float:
    if value >= 0:
        return 1.0 / (1.0 + math.exp(-value))
    exp_value = math.exp(value)
    return exp_value / (1.0 + exp_value)
