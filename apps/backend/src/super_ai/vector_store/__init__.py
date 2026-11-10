"""PostgreSQL + pgvector boundary for knowledge chunk embeddings."""

from super_ai.vector_store.config import (
    PgvectorConfigurationError,
    PgvectorSettings,
    load_pgvector_settings,
)
from super_ai.vector_store.pgvector import (
    PgvectorConnectionManager,
    PgvectorHealthCheckResult,
    PgvectorStore,
    StoredVectorChunk,
    VectorChunkRecord,
    VectorSearchResult,
    build_default_pgvector_store,
)

__all__ = [
    "PgvectorConfigurationError",
    "PgvectorConnectionManager",
    "PgvectorHealthCheckResult",
    "PgvectorSettings",
    "PgvectorStore",
    "StoredVectorChunk",
    "VectorChunkRecord",
    "VectorSearchResult",
    "build_default_pgvector_store",
    "load_pgvector_settings",
]
