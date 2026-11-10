from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
INFRA_DIR = REPO_ROOT / "infra"


def test_compose_declares_only_local_infrastructure_services() -> None:
    compose = _read("compose.yaml")

    for service in ("postgres:", "alertmanager:"):
        assert service in compose

    for removed_service in ("milvus:", "etcd:", "minio:", "attu:"):
        assert removed_service not in compose

    for removed_service in ("\n  backend:\n", "\n  frontend:\n", "\n  cls-mcp-server:\n"):
        assert removed_service not in compose

    assert "agent-py-app:local" not in compose
    assert "dockerfile: infra/app.Dockerfile" not in compose
    assert "env_file:" not in compose
    assert "${" not in compose


def test_compose_configures_pgvector_without_mcp_runtime() -> None:
    compose = _read("compose.yaml")

    assert '"5432:5432"' in compose
    assert "pgvector/pgvector:pg16" in compose
    assert "pg_isready -U oncall -d oncall" in compose
    assert "cls-mcp-server" not in compose


def test_compose_configures_local_alertmanager_without_a_full_monitoring_stack() -> None:
    compose = _read("compose.yaml")

    assert "alertmanager:" in compose
    assert "prom/alertmanager:v0.28.1" in compose
    assert 'profiles: ["observability"]' in compose
    assert '"9093:9093"' in compose
    assert "./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro" in compose
    assert (INFRA_DIR / "alertmanager" / "alertmanager.yml").is_file()


def test_compose_excludes_external_observability_and_upload_startup() -> None:
    compose = _read("compose.yaml").lower()

    for excluded in (
        "prometheus:",
        "grafana:",
        "jaeger:",
        "loki:",
        "elasticsearch:",
        "upload-doc",
        "ingest-document",
    ):
        assert excluded not in compose

    for script_suffix in ("*.sh", "*.bat"):
        assert list(INFRA_DIR.glob(script_suffix)) == []


def test_infrastructure_directory_excludes_application_runtime_assets() -> None:
    assert not (REPO_ROOT / "infra" / "app.Dockerfile").exists()
    assert not (REPO_ROOT / "config" / "project.compose.json").exists()


def test_infra_docs_describe_infrastructure_and_local_application_services() -> None:
    infra_readme = _read("README.md")
    root_readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "PostgreSQL + pgvector" in infra_readme
    assert "CloudWatch MCP Server 由后端" in root_readme


def _read(name: str) -> str:
    return (INFRA_DIR / name).read_text(encoding="utf-8")
