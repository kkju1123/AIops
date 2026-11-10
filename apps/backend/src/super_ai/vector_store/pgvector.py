"""PostgreSQL + pgvector repository with tenant-scoped operations."""

from __future__ import annotations

from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from time import monotonic
from typing import Any, Protocol, cast

from .config import PgvectorSettings, load_pgvector_settings


class CursorProtocol(Protocol):
    def execute(self, query: str, params: object | None = None) -> object: ...
    def executemany(self, query: str, params_seq: Sequence[Sequence[object]]) -> object: ...
    def fetchone(self) -> Sequence[object] | None: ...
    def fetchall(self) -> Sequence[Sequence[object]]: ...
    def __enter__(self) -> CursorProtocol: ...
    def __exit__(self, *args: object) -> None: ...


class ConnectionProtocol(Protocol):
    def cursor(self) -> CursorProtocol: ...
    def commit(self) -> None: ...
    def close(self) -> None: ...


ConnectionFactory = Callable[[PgvectorSettings], ConnectionProtocol]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _empty_metadata() -> dict[str, object]:
    return {}


@dataclass(frozen=True, slots=True)
class PgvectorHealthCheckResult:
    """Secret-safe pgvector readiness result."""

    ok: bool
    host: str
    port: int
    database: str
    table_name: str
    latency_ms: float
    error: str | None = None


@dataclass(frozen=True, slots=True)
class VectorChunkRecord:
    """Knowledge base chunk to persist in pgvector."""

    chunk_id: str
    document_id: str
    knowledge_base_id: str
    owner_user_id: str
    tenant_id: str
    content: str
    vector: Sequence[float]
    metadata: Mapping[str, object] = field(default_factory=_empty_metadata)
    source: str = ""
    created_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True, slots=True)
class VectorSearchResult:
    """Tenant-scoped vector search hit returned to retrieval code."""

    chunk_id: str
    document_id: str
    knowledge_base_id: str
    owner_user_id: str
    tenant_id: str
    content: str
    source: str
    created_at: int
    metadata: Mapping[str, object]
    score: float


@dataclass(frozen=True, slots=True)
class StoredVectorChunk:
    """Scalar chunk data loaded without its vector for lexical retrieval."""

    chunk_id: str
    document_id: str
    knowledge_base_id: str
    owner_user_id: str
    tenant_id: str
    content: str
    source: str
    created_at: int
    metadata: Mapping[str, object]


class PgvectorConnectionManager:
    """Open connections only during explicit repository operations."""

    def __init__(
        self,
        *,
        settings: PgvectorSettings,
        connection_factory: ConnectionFactory | None = None,
    ) -> None:
        self._settings = settings
        self._connection_factory = connection_factory or _create_connection

    @contextmanager
    def connect(self) -> Generator[ConnectionProtocol, None, None]:
        connection = self._connection_factory(self._settings)
        try:
            yield connection
        finally:
            connection.close()


class PgvectorStore:
    """Repository boundary for knowledge chunk vectors in PostgreSQL."""

    def __init__(
        self,
        *,
        settings: PgvectorSettings,
        connection_manager: PgvectorConnectionManager | None = None,
    ) -> None:
        self._settings = settings
        self._connections = connection_manager or PgvectorConnectionManager(settings=settings)

    @property
    def settings(self) -> PgvectorSettings:
        return self._settings

    def initialize(self) -> None:
        """Create the vector extension, chunk table, and required indexes."""
        table = self._settings.table_name
        with self._connections.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            connection.commit()
            _register_vector(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""CREATE TABLE IF NOT EXISTS {table} (
                        chunk_id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        knowledge_base_id TEXT NOT NULL,
                        owner_user_id TEXT NOT NULL,
                        tenant_id TEXT NOT NULL,
                        content TEXT NOT NULL,
                        source TEXT NOT NULL,
                        created_at BIGINT NOT NULL,
                        metadata JSONB NOT NULL,
                        embedding vector({self._settings.vector_dimension}) NOT NULL
                    )"""
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS {table}_scope_idx "
                    f"ON {table} (tenant_id, knowledge_base_id, document_id)"
                )
                cursor.execute(
                    f"CREATE INDEX IF NOT EXISTS {table}_embedding_hnsw_idx "
                    f"ON {table} USING hnsw (embedding vector_cosine_ops) "
                    f"WITH (m = {self._settings.hnsw_m}, "
                    f"ef_construction = {self._settings.hnsw_ef_construction})"
                )
            connection.commit()

    def health_check(self) -> PgvectorHealthCheckResult:
        """Check PostgreSQL and extension availability without returning credentials."""
        started_at = monotonic()
        try:
            with self._connections.connect() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                    )
                    row = cursor.fetchone()
                    if row is None or row[0] is not True:
                        raise RuntimeError("vector extension is unavailable")
        except Exception:
            return self._health_result(
                ok=False,
                started_at=started_at,
                error="PostgreSQL + pgvector is unavailable.",
            )
        return self._health_result(ok=True, started_at=started_at)

    def insert_chunks(self, chunks: Sequence[VectorChunkRecord]) -> None:
        """Insert or replace chunk vectors and ownership metadata."""
        if not chunks:
            return
        rows = [self._chunk_row(chunk) for chunk in chunks]
        table = self._settings.table_name
        with self._connections.connect() as connection:
            _register_vector(connection)
            with connection.cursor() as cursor:
                cursor.executemany(
                    f"""INSERT INTO {table} (
                        chunk_id, document_id, knowledge_base_id, owner_user_id, tenant_id,
                        content, source, created_at, metadata, embedding
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        document_id = EXCLUDED.document_id,
                        knowledge_base_id = EXCLUDED.knowledge_base_id,
                        owner_user_id = EXCLUDED.owner_user_id,
                        tenant_id = EXCLUDED.tenant_id,
                        content = EXCLUDED.content,
                        source = EXCLUDED.source,
                        created_at = EXCLUDED.created_at,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding""",
                    rows,
                )
            connection.commit()

    def search_chunks(
        self,
        *,
        query_vector: Sequence[float],
        tenant_id: str,
        knowledge_base_ids: Sequence[str],
        limit: int,
    ) -> list[VectorSearchResult]:
        """Search cosine similarity within an explicit tenant scope."""
        if not knowledge_base_ids:
            return []
        self._validate_vector(query_vector)
        table = self._settings.table_name
        with self._connections.connect() as connection:
            _register_vector(connection)
            with connection.cursor() as cursor:
                cursor.execute(f"SET LOCAL hnsw.ef_search = {self._settings.hnsw_ef_search}")
                cursor.execute(
                    f"""SELECT chunk_id, document_id, knowledge_base_id, owner_user_id,
                        tenant_id, content, source, created_at, metadata,
                        1 - (embedding <=> %s) AS score
                    FROM {table}
                    WHERE tenant_id = %s AND knowledge_base_id = ANY(%s)
                    ORDER BY embedding <=> %s
                    LIMIT %s""",
                    (_vector(query_vector), tenant_id, list(knowledge_base_ids),
                     _vector(query_vector), limit),
                )
                return [_row_to_search_result(row) for row in cursor.fetchall()]

    def list_chunks(
        self,
        *,
        tenant_id: str,
        knowledge_base_ids: Sequence[str],
    ) -> list[StoredVectorChunk]:
        """List lexical-retrieval corpus within an explicit tenant scope."""
        if not knowledge_base_ids:
            return []
        table = self._settings.table_name
        with self._connections.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""SELECT chunk_id, document_id, knowledge_base_id, owner_user_id,
                        tenant_id, content, source, created_at, metadata
                    FROM {table}
                    WHERE tenant_id = %s AND knowledge_base_id = ANY(%s)
                    ORDER BY created_at, chunk_id""",
                    (tenant_id, list(knowledge_base_ids)),
                )
                return [_row_to_stored_chunk(row) for row in cursor.fetchall()]

    def delete_document_chunks(
        self,
        *,
        tenant_id: str,
        knowledge_base_id: str,
        document_id: str,
    ) -> None:
        """Delete chunks only when all ownership scope values match."""
        if not tenant_id or not knowledge_base_id or not document_id:
            raise ValueError("tenant_id, knowledge_base_id, and document_id are required")
        table = self._settings.table_name
        with self._connections.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"DELETE FROM {table} WHERE tenant_id = %s "
                    "AND knowledge_base_id = %s AND document_id = %s",
                    (tenant_id, knowledge_base_id, document_id),
                )
            connection.commit()

    def _chunk_row(self, chunk: VectorChunkRecord) -> Sequence[object]:
        self._validate_vector(chunk.vector)
        metadata = dict(chunk.metadata)
        metadata.update(
            {"ownerUserId": chunk.owner_user_id, "tenantId": chunk.tenant_id,
             "knowledgeBaseId": chunk.knowledge_base_id, "documentId": chunk.document_id,
             "chunkId": chunk.chunk_id}
        )
        return (
            chunk.chunk_id, chunk.document_id, chunk.knowledge_base_id, chunk.owner_user_id,
            chunk.tenant_id, chunk.content, chunk.source, _to_epoch_millis(chunk.created_at),
            _jsonb(metadata), _vector(chunk.vector),
        )

    def _validate_vector(self, vector: Sequence[float]) -> None:
        if len(vector) != self._settings.vector_dimension:
            raise ValueError(
                f"Chunk vector dimension {len(vector)} does not match configured dimension "
                f"{self._settings.vector_dimension}"
            )

    def _health_result(
        self, *, ok: bool, started_at: float, error: str | None = None
    ) -> PgvectorHealthCheckResult:
        return PgvectorHealthCheckResult(
            ok=ok, host=self._settings.host, port=self._settings.port,
            database=self._settings.database, table_name=self._settings.table_name,
            latency_ms=round((monotonic() - started_at) * 1000, 3), error=error,
        )


def build_default_pgvector_store(config_path: str | None = None) -> PgvectorStore:
    """Build the default repository without opening a connection."""
    return PgvectorStore(settings=load_pgvector_settings(config_path=config_path))


def _create_connection(settings: PgvectorSettings) -> ConnectionProtocol:
    from psycopg import connect

    return cast(
        ConnectionProtocol,
        connect(settings.dsn, connect_timeout=max(1, round(settings.timeout_seconds))),
    )


def _register_vector(connection: ConnectionProtocol) -> None:
    from pgvector.psycopg import register_vector

    register_vector(cast(Any, connection))


def _vector(value: Sequence[float]) -> object:
    from pgvector import Vector

    return Vector(list(value))


def _jsonb(value: Mapping[str, object]) -> object:
    from psycopg.types.json import Jsonb

    return Jsonb(dict(value))


def _row_to_search_result(row: Sequence[object]) -> VectorSearchResult:
    return VectorSearchResult(
        chunk_id=_string(row[0]), document_id=_string(row[1]),
        knowledge_base_id=_string(row[2]), owner_user_id=_string(row[3]),
        tenant_id=_string(row[4]), content=_string(row[5]), source=_string(row[6]),
        created_at=_int(row[7]), metadata=_mapping(row[8]), score=_float(row[9]),
    )


def _row_to_stored_chunk(row: Sequence[object]) -> StoredVectorChunk:
    return StoredVectorChunk(
        chunk_id=_string(row[0]), document_id=_string(row[1]),
        knowledge_base_id=_string(row[2]), owner_user_id=_string(row[3]),
        tenant_id=_string(row[4]), content=_string(row[5]), source=_string(row[6]),
        created_at=_int(row[7]), metadata=_mapping(row[8]),
    )


def _mapping(value: object) -> Mapping[str, object]:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else {}


def _string(value: object) -> str:
    return value if isinstance(value, str) else ""


def _int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _float(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _to_epoch_millis(value: datetime) -> int:
    aware_value = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return int(aware_value.timestamp() * 1000)
