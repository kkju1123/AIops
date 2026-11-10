"""Configuration for the PostgreSQL + pgvector vector store."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

from super_ai.project_config import (
    ProjectConfigurationError,
    project_config_section,
    required_float,
    required_int,
    required_str,
)

DEFAULT_DSN = "postgresql://oncall:oncall@127.0.0.1:5432/oncall"
DEFAULT_TABLE_NAME = "knowledge_chunks"
DEFAULT_VECTOR_DIMENSION = 1024
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_HNSW_M = 16
DEFAULT_HNSW_EF_CONSTRUCTION = 200
DEFAULT_HNSW_EF_SEARCH = 64
_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class PgvectorConfigurationError(RuntimeError):
    """Raised when pgvector settings are invalid."""


@dataclass(frozen=True, slots=True)
class PgvectorSettings:
    """Typed settings for the pgvector repository boundary."""

    dsn: str = DEFAULT_DSN
    table_name: str = DEFAULT_TABLE_NAME
    vector_dimension: int = DEFAULT_VECTOR_DIMENSION
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    hnsw_m: int = DEFAULT_HNSW_M
    hnsw_ef_construction: int = DEFAULT_HNSW_EF_CONSTRUCTION
    hnsw_ef_search: int = DEFAULT_HNSW_EF_SEARCH

    @property
    def host(self) -> str:
        return urlparse(self.dsn).hostname or ""

    @property
    def port(self) -> int:
        return urlparse(self.dsn).port or 5432

    @property
    def database(self) -> str:
        return unquote(urlparse(self.dsn).path.lstrip("/"))


def load_pgvector_settings(config_path: Path | str | None = None) -> PgvectorSettings:
    """Load pgvector settings from the repository project config."""
    try:
        config = project_config_section("vectorStore", config_path=config_path)
        settings = PgvectorSettings(
            dsn=required_str(config, "dsn"),
            table_name=required_str(config, "tableName"),
            vector_dimension=required_int(config, "vectorDimension"),
            timeout_seconds=required_float(config, "timeoutSeconds"),
            hnsw_m=required_int(config, "hnswM"),
            hnsw_ef_construction=required_int(config, "hnswEfConstruction"),
            hnsw_ef_search=required_int(config, "hnswEfSearch"),
        )
    except (ProjectConfigurationError, ValueError) as exc:
        raise PgvectorConfigurationError(str(exc)) from exc

    if not settings.dsn.startswith(("postgresql://", "postgres://")):
        raise PgvectorConfigurationError("pgvector dsn must use postgresql://")
    if not settings.host or not settings.database:
        raise PgvectorConfigurationError("pgvector dsn must include host and database")
    if _SQL_IDENTIFIER.fullmatch(settings.table_name) is None:
        raise PgvectorConfigurationError("pgvector tableName must be a SQL identifier")
    for key, value in (
        ("vectorDimension", settings.vector_dimension),
        ("timeoutSeconds", settings.timeout_seconds),
        ("hnswM", settings.hnsw_m),
        ("hnswEfConstruction", settings.hnsw_ef_construction),
        ("hnswEfSearch", settings.hnsw_ef_search),
    ):
        if value <= 0:
            raise PgvectorConfigurationError(f"pgvector setting must be positive: {key}")
    return settings
