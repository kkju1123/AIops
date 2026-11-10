from __future__ import annotations

from collections.abc import Sequence

import pytest

from super_ai.llm import (
    LlmRerankError,
    LocalBgeEmbeddingModel,
    LocalBgeRerankModel,
    LocalEmbeddingConfig,
    LocalRerankConfig,
)


class FakeEncoder:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
        self.calls: list[dict[str, object]] = []

    def encode(
        self,
        sentences: list[str],
        *,
        batch_size: int,
        normalize_embeddings: bool,
        show_progress_bar: bool,
    ) -> object:
        self.calls.append(
            {
                "sentences": sentences,
                "batchSize": batch_size,
                "normalize": normalize_embeddings,
                "showProgress": show_progress_bar,
            }
        )
        return self.vectors


class FakeCrossEncoder:
    def __init__(self, scores: list[float]) -> None:
        self.scores = scores
        self.pairs: list[tuple[str, str]] = []

    def predict(
        self,
        sentences: list[tuple[str, str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
    ) -> object:
        assert batch_size == 4
        assert show_progress_bar is False
        self.pairs = sentences
        return self.scores


@pytest.mark.asyncio
async def test_embedding_model_loads_lazily_and_validates_dimension() -> None:
    created: list[FakeEncoder] = []
    encoder = FakeEncoder([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

    def factory(_config: LocalEmbeddingConfig) -> FakeEncoder:
        created.append(encoder)
        return encoder

    model = LocalBgeEmbeddingModel(
        LocalEmbeddingConfig("sentence-transformers", "test", 3, "cpu", 4, True),
        model_factory=factory,
    )
    assert created == []

    vectors = await model.aembed_documents(["one", "two"])

    assert vectors == [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]
    assert len(created) == 1
    assert encoder.calls[0]["normalize"] is True

    invalid = LocalBgeEmbeddingModel(
        LocalEmbeddingConfig("sentence-transformers", "test", 2, "cpu", 4, True),
        model_factory=lambda _config: encoder,
    )
    with pytest.raises(RuntimeError, match="dimension"):
        await invalid.aembed_documents(["one", "two"])


@pytest.mark.asyncio
async def test_reranker_preserves_indexes_and_sorts_scores() -> None:
    cross_encoder = FakeCrossEncoder([-1.0, 3.0, 0.5])
    model = LocalBgeRerankModel(
        LocalRerankConfig("sentence-transformers", "test", "cpu", 4),
        model_factory=lambda _config: cross_encoder,
    )

    results = await model.arerank(
        query="cpu saturation",
        documents=["memory", "cpu", "network"],
        top_n=2,
    )

    assert [result.index for result in results] == [1, 2]
    assert results[0].relevance_score > results[1].relevance_score
    assert cross_encoder.pairs == [
        ("cpu saturation", "memory"),
        ("cpu saturation", "cpu"),
        ("cpu saturation", "network"),
    ]


@pytest.mark.asyncio
async def test_reranker_rejects_invalid_top_n() -> None:
    model = LocalBgeRerankModel(
        LocalRerankConfig("sentence-transformers", "test", "cpu", 4),
        model_factory=lambda _config: FakeCrossEncoder([]),
    )

    with pytest.raises(LlmRerankError, match="invalid"):
        await model.arerank(query="query", documents=cast_documents(["one"]), top_n=2)


def cast_documents(documents: Sequence[str]) -> Sequence[str]:
    return documents
