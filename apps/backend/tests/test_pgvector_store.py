from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import cast

import pytest

import super_ai.vector_store.pgvector as pgvector_module
from super_ai.vector_store import (
    PgvectorConnectionManager,
    PgvectorSettings,
    PgvectorStore,
    VectorChunkRecord,
    load_pgvector_settings,
)
from super_ai.vector_store.pgvector import ConnectionProtocol


def test_importing_vector_store_does_not_import_psycopg() -> None:
    sys.modules.pop("psycopg", None)

    __import__("super_ai.vector_store")

    assert "psycopg" not in sys.modules


def test_load_pgvector_settings_and_reject_unsafe_table(tmp_path: Path) -> None:
    config_path = tmp_path / "project.json"
    config_path.write_text(
        json.dumps(
            {
                "vectorStore": {
                    "dsn": "postgresql://user:secret@postgres.test:5544/vectors",
                    "tableName": "knowledge_chunks",
                    "vectorDimension": 3,
                    "timeoutSeconds": 4,
                    "hnswM": 16,
                    "hnswEfConstruction": 200,
                    "hnswEfSearch": 64,
                }
            }
        ),
        encoding="utf-8",
    )

    settings = load_pgvector_settings(config_path)

    assert settings.host == "postgres.test"
    assert settings.port == 5544
    assert settings.database == "vectors"
    assert "secret" not in repr((settings.host, settings.port, settings.database))

    content = json.loads(config_path.read_text(encoding="utf-8"))
    content["vectorStore"]["tableName"] = "chunks; DROP TABLE users"
    config_path.write_text(json.dumps(content), encoding="utf-8")
    with pytest.raises(RuntimeError, match="SQL identifier"):
        load_pgvector_settings(config_path)


def test_connection_is_lazy_and_closed() -> None:
    created: list[FakeConnection] = []

    def factory(_settings: PgvectorSettings) -> ConnectionProtocol:
        connection = FakeConnection()
        created.append(connection)
        return connection

    manager = PgvectorConnectionManager(
        settings=PgvectorSettings(), connection_factory=factory
    )
    assert created == []

    with manager.connect():
        assert len(created) == 1
        assert created[0].closed is False

    assert created[0].closed is True


def test_search_is_tenant_scoped_and_empty_scope_skips_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection(
        rows=[
            (
                "chunk_1", "doc_1", "kb_1", "user_1", "tenant_1", "CPU runbook",
                "runbook.md", 123, {"section": "CPU"}, 0.91,
            )
        ]
    )
    store = _store(connection)
    monkeypatch.setattr(pgvector_module, "_register_vector", _noop_register)
    monkeypatch.setattr(pgvector_module, "_vector", _fake_vector)

    assert store.search_chunks(
        query_vector=[0.1, 0.2, 0.3], tenant_id="tenant_1",
        knowledge_base_ids=[], limit=5,
    ) == []
    assert connection.cursor_instance.executions == []

    results = store.search_chunks(
        query_vector=[0.1, 0.2, 0.3], tenant_id="tenant_1",
        knowledge_base_ids=["kb_1"], limit=5,
    )

    query, params = connection.cursor_instance.executions[-1]
    assert "tenant_id = %s" in query
    assert "knowledge_base_id = ANY(%s)" in query
    assert params is not None
    assert "tenant_1" in cast(tuple[object, ...], params)
    assert results[0].chunk_id == "chunk_1"
    assert results[0].score == 0.91


def test_insert_validates_dimension_and_adds_ownership_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    connection = FakeConnection()
    store = _store(connection)
    monkeypatch.setattr(pgvector_module, "_register_vector", _noop_register)
    monkeypatch.setattr(pgvector_module, "_vector", _fake_vector)
    monkeypatch.setattr(pgvector_module, "_jsonb", _fake_jsonb)
    chunk = VectorChunkRecord(
        chunk_id="chunk_1", document_id="doc_1", knowledge_base_id="kb_1",
        owner_user_id="user_1", tenant_id="tenant_1", content="runbook",
        vector=[0.1, 0.2, 0.3], metadata={"section": "CPU"},
    )

    store.insert_chunks([chunk])

    row = connection.cursor_instance.executemany_rows[0]
    metadata = cast(dict[str, object], row[8])
    assert metadata["tenantId"] == "tenant_1"
    assert metadata["ownerUserId"] == "user_1"
    assert connection.commits == 1

    with pytest.raises(ValueError, match="dimension 2"):
        store.insert_chunks(
            [
                VectorChunkRecord(
                    chunk_id="chunk_2", document_id="doc_1", knowledge_base_id="kb_1",
                    owner_user_id="user_1", tenant_id="tenant_1", content="runbook",
                    vector=[0.1, 0.2],
                )
            ]
        )


def test_health_check_is_secret_safe() -> None:
    healthy = _store(FakeConnection(fetchone=(True,))).health_check()
    failing = _store(FakeConnection(error=RuntimeError("password=secret"))).health_check()

    assert healthy.ok is True
    assert failing.ok is False
    assert failing.error == "PostgreSQL + pgvector is unavailable."
    assert "secret" not in repr(failing)


def _store(connection: FakeConnection) -> PgvectorStore:
    settings = PgvectorSettings(
        dsn="postgresql://user:secret@postgres.test:5432/oncall", vector_dimension=3
    )
    manager = PgvectorConnectionManager(
        settings=settings, connection_factory=lambda _settings: connection
    )
    return PgvectorStore(settings=settings, connection_manager=manager)


def _noop_register(_connection: ConnectionProtocol) -> None:
    return None


def _fake_vector(vector: Sequence[float]) -> object:
    return list(vector)


def _fake_jsonb(value: Mapping[str, object]) -> object:
    return dict(value)


class FakeCursor:
    def __init__(
        self,
        *,
        rows: list[tuple[object, ...]] | None = None,
        fetchone: tuple[object, ...] | None = (True,),
        error: Exception | None = None,
    ) -> None:
        self.rows = rows or []
        self.fetchone_value = fetchone
        self.error = error
        self.executions: list[tuple[str, object | None]] = []
        self.executemany_rows: list[tuple[object, ...]] = []

    def execute(self, query: str, params: object | None = None) -> object:
        if self.error is not None:
            raise self.error
        self.executions.append((query, params))
        return self

    def executemany(self, query: str, params_seq: object) -> object:
        self.executions.append((query, None))
        self.executemany_rows = [tuple(row) for row in cast(list[list[object]], params_seq)]
        return self

    def fetchone(self) -> tuple[object, ...] | None:
        return self.fetchone_value

    def fetchall(self) -> list[tuple[object, ...]]:
        return self.rows

    def __enter__(self) -> FakeCursor:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class FakeConnection:
    def __init__(
        self,
        *,
        rows: list[tuple[object, ...]] | None = None,
        fetchone: tuple[object, ...] | None = (True,),
        error: Exception | None = None,
    ) -> None:
        self.cursor_instance = FakeCursor(rows=rows, fetchone=fetchone, error=error)
        self.closed = False
        self.commits = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        self.closed = True
