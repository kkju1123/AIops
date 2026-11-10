from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from alembic import command
from alembic.config import Config

from super_ai.aiops.fixtures import build_live_drill_sop_documents
from super_ai.api.app import AiopsDiagnosticRunner, create_app
from super_ai.live_demo import (
    LIVE_DEMO_TOKEN_HEADER,
    client_ip_for,
    load_live_demo_settings,
)
from super_ai.memory.repositories import DiagnosticTaskRecord
from super_ai.project_config import ProjectConfigurationError

TEMPLATE_PATH = Path(__file__).resolve().parents[3] / "config" / "project.template.json"
SERVICE_EMAIL = "live-demo@example.com"
SCENARIO_ID = "checkout-db-pool-exhausted"


@dataclass
class RecordingRunner:
    tasks: list[DiagnosticTaskRecord] = field(default_factory=lambda: [])

    async def stream(
        self,
        *,
        task: DiagnosticTaskRecord,
        accessible_knowledge_base_ids: Sequence[str],
    ) -> AsyncIterator[dict[str, object]]:
        self.tasks.append(task)
        yield {
            "id": "evt_live_1",
            "type": "task.status",
            "channel": "aiops",
            "timestamp": "2026-11-07T00:00:00+00:00",
            "task": {"id": task.id, "status": "running", "message": "Planner", "progress": 10},
        }


@dataclass
class RecordingPublisher:
    accepted: bool = True
    published: list[list[Mapping[str, object]]] = field(default_factory=lambda: [])

    async def publish(self, alerts: Sequence[Mapping[str, object]]) -> bool:
        self.published.append(list(alerts))
        return self.accepted


@pytest.mark.asyncio
async def test_live_demo_run_uses_service_account_and_run_token(
    migrated_database_url: str, tmp_path: Path
) -> None:
    runner = RecordingRunner()
    publisher = RecordingPublisher()
    app = _app(migrated_database_url, tmp_path, runner, publisher)
    async with _client(app) as client:
        service = await _register(client, SERVICE_EMAIL)
        overview = await client.get("/live-demo")
        created = await client.post(
            "/live-demo/runs",
            json={"scenarioId": SCENARIO_ID, "ownerUserId": "attacker", "tenantId": "x"},
        )
        data = created.json()["data"]
        run_id = data["run"]["id"]
        token = data["runToken"]
        missing = await client.post(f"/live-demo/runs/{run_id}:stream")
        wrong = await client.post(
            f"/live-demo/runs/{run_id}:stream", headers={LIVE_DEMO_TOKEN_HEADER: "wrong"}
        )
        stream = await client.post(
            f"/live-demo/runs/{run_id}:stream", headers={LIVE_DEMO_TOKEN_HEADER: token}
        )
        unknown_run = await client.post(
            "/live-demo/runs/live_run_missing:stream", headers={LIVE_DEMO_TOKEN_HEADER: token}
        )
        token_as_bearer = await client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

    assert overview.status_code == 200
    overview_data = overview.json()["data"]
    assert overview_data["available"] is True
    assert [item["id"] for item in overview_data["scenarios"]] == [SCENARIO_ID]
    assert overview_data["quota"]["visitorRemaining"] == 3
    assert overview_data["latestRun"] is None

    assert created.status_code == 202
    assert data["alertPublished"] is True
    assert data["alert"]["alertName"] == "CheckoutDatabasePoolExhausted"
    assert data["alert"]["service"] == "checkout-service"
    assert "连接未及时归还" not in json.dumps(data["alert"], ensure_ascii=False)
    assert "连接未及时归还" not in json.dumps(publisher.published, ensure_ascii=False)
    assert publisher.published[0][0]["labels"] == {
        **cast(dict[str, Any], publisher.published[0][0]["labels"]),
        "drill_run_id": run_id,
    }

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert unknown_run.status_code == 403
    assert stream.status_code == 200
    assert "event: task.status" in stream.text
    assert token_as_bearer.status_code == 401

    assert len(runner.tasks) == 1
    task = runner.tasks[0]
    assert task.owner_user_id == service["user"]["id"]
    assert task.input_payload["liveDemo"] is True
    assert cast(dict[str, Any], task.input_payload["alert"])["alertName"] == (
        "CheckoutDatabasePoolExhausted"
    )


@pytest.mark.asyncio
async def test_live_demo_rejects_unknown_scenario_without_side_effects(
    migrated_database_url: str, tmp_path: Path
) -> None:
    runner = RecordingRunner()
    publisher = RecordingPublisher()
    app = _app(migrated_database_url, tmp_path, runner, publisher)
    async with _client(app) as client:
        await _register(client, SERVICE_EMAIL)
        response = await client.post(
            "/live-demo/runs", json={"scenarioId": "java-ecom-cart-redis-latency"}
        )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_INVALID_ARGUMENT"
    assert publisher.published == []
    assert runner.tasks == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "limits",
    [
        {"perVisitorHourlyLimit": 1, "dailyLimit": 10, "maxConcurrentRuns": 5},
        {"perVisitorHourlyLimit": 5, "dailyLimit": 1, "maxConcurrentRuns": 5},
        {"perVisitorHourlyLimit": 5, "dailyLimit": 10, "maxConcurrentRuns": 1},
    ],
)
async def test_live_demo_enforces_rate_and_concurrency_limits(
    migrated_database_url: str, tmp_path: Path, limits: dict[str, int]
) -> None:
    publisher = RecordingPublisher()
    app = _app(migrated_database_url, tmp_path, _ParkedRunner(), publisher, **limits)
    async with _client(app) as client:
        await _register(client, SERVICE_EMAIL)
        first = await client.post("/live-demo/runs", json={"scenarioId": SCENARIO_ID})
        second = await client.post("/live-demo/runs", json={"scenarioId": SCENARIO_ID})

    assert first.status_code == 202
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "BUSINESS_RATE_LIMITED"
    assert len(publisher.published) == 1


@pytest.mark.asyncio
async def test_live_demo_is_unavailable_without_service_account(
    migrated_database_url: str, tmp_path: Path
) -> None:
    publisher = RecordingPublisher()
    app = _app(migrated_database_url, tmp_path, RecordingRunner(), publisher)
    async with _client(app) as client:
        overview = await client.get("/live-demo")
        created = await client.post("/live-demo/runs", json={"scenarioId": SCENARIO_ID})

    assert overview.json()["data"]["available"] is False
    assert overview.json()["data"]["unavailableReason"]
    assert created.status_code == 503
    assert created.json()["error"]["code"] == "SYSTEM_UNAVAILABLE"
    assert publisher.published == []


@pytest.mark.asyncio
async def test_live_demo_disabled_by_config(migrated_database_url: str, tmp_path: Path) -> None:
    publisher = RecordingPublisher()
    app = _app(migrated_database_url, tmp_path, RecordingRunner(), publisher, enabled=False)
    async with _client(app) as client:
        await _register(client, SERVICE_EMAIL)
        overview = await client.get("/live-demo")
        created = await client.post("/live-demo/runs", json={"scenarioId": SCENARIO_ID})

    assert overview.json()["data"]["available"] is False
    assert created.status_code == 503
    assert publisher.published == []


def test_live_demo_settings_validation(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    missing.write_text("{}", encoding="utf-8")
    assert load_live_demo_settings(config_path=missing).enabled is False

    invalid = tmp_path / "invalid.json"
    invalid.write_text(
        json.dumps({"liveDemo": {**_live_demo_section(), "scenarioIds": ["unknown"]}}),
        encoding="utf-8",
    )
    with pytest.raises(ProjectConfigurationError):
        load_live_demo_settings(config_path=invalid)

    default_mode = tmp_path / "default.json"
    default_mode.write_text(json.dumps({"liveDemo": _live_demo_section()}), encoding="utf-8")
    assert load_live_demo_settings(config_path=default_mode).observability == "simulator"

    bad_mode = tmp_path / "bad-mode.json"
    bad_mode.write_text(
        json.dumps({"liveDemo": {**_live_demo_section(), "observability": "mock"}}),
        encoding="utf-8",
    )
    with pytest.raises(ProjectConfigurationError):
        load_live_demo_settings(config_path=bad_mode)


@pytest.mark.asyncio
@pytest.mark.parametrize("observability", ["simulator", "aws-cloudwatch"])
async def test_live_demo_injects_a_simulated_fault_only_in_simulator_mode(
    migrated_database_url: str, tmp_path: Path, observability: str
) -> None:
    runner = RecordingRunner()
    app = _app(
        migrated_database_url,
        tmp_path,
        runner,
        RecordingPublisher(),
        observability=observability,
        scenarioIds=[SCENARIO_ID, "java-ecom-cart-redis-latency"],
    )
    async with _client(app) as client:
        await _register(client, SERVICE_EMAIL)
        overview = await client.get("/live-demo")
        created = await client.post(
            "/live-demo/runs", json={"scenarioId": "java-ecom-cart-redis-latency"}
        )
        run = created.json()["data"]
        await client.post(
            f"/live-demo/runs/{run['run']['id']}:stream",
            headers={LIVE_DEMO_TOKEN_HEADER: run["runToken"]},
        )

    assert overview.json()["data"]["observability"] == observability
    assert created.status_code == 202
    assert run["observability"] == observability
    payload = runner.tasks[0].input_payload
    if observability == "simulator":
        fault = cast(dict[str, Any], payload["simulatedFault"])
        assert fault["runId"] == run["run"]["id"]
        assert fault["scenarioId"] == "java-ecom-cart-redis-latency"
        assert fault["service"] == "cart-service"
        assert "日志、指标与 SOP" in str(payload["query"])
    else:
        assert "simulatedFault" not in payload
        assert "真实日志与 SOP" in str(payload["query"])


def test_live_drill_sop_matches_cloudwatch_fixture() -> None:
    documents = build_live_drill_sop_documents()

    assert [document.sop_id for document in documents] == ["checkout-db-pool-exhausted-sop"]
    assert "checkout-service" in documents[0].content
    assert "database_connection_pool_exhausted" in documents[0].content
    assert "CloudWatch" in documents[0].content


def test_client_ip_only_trusts_forwarded_header_when_configured() -> None:
    assert client_ip_for(
        direct_host="10.0.0.1", forwarded_for="1.2.3.4, 10.0.0.1", trust_forwarded_for=False
    ) == "10.0.0.1"
    assert client_ip_for(
        direct_host="10.0.0.1", forwarded_for="1.2.3.4, 10.0.0.1", trust_forwarded_for=True
    ) == "1.2.3.4"


class _ParkedRunner:
    """Runner that never finishes the task, so the run stays in flight."""

    async def stream(
        self,
        *,
        task: DiagnosticTaskRecord,
        accessible_knowledge_base_ids: Sequence[str],
    ) -> AsyncIterator[dict[str, object]]:
        del task, accessible_knowledge_base_ids
        if False:  # pragma: no cover - generator marker
            yield {}


@dataclass
class WarmupEmbedding:
    error: Exception | None = None
    calls: list[list[str]] = field(default_factory=lambda: [])

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(texts)
        if self.error is not None:
            raise self.error
        return [[0.0] for _ in texts]


@dataclass
class WarmupRerank:
    queries: list[str] = field(default_factory=lambda: [])

    async def arerank(self, *, query: str, documents: Sequence[str], top_n: int) -> list[object]:
        self.queries.append(query)
        return []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("enabled", "error", "expect_embedding", "expect_rerank"),
    [
        (True, None, True, True),
        (True, RuntimeError("model download failed"), True, False),
        (False, None, False, False),
    ],
)
async def test_lifespan_warms_retrieval_models_without_blocking_startup(
    migrated_database_url: str,
    tmp_path: Path,
    enabled: bool,
    error: Exception | None,
    expect_embedding: bool,
    expect_rerank: bool,
) -> None:
    app = _app(
        migrated_database_url, tmp_path, RecordingRunner(), RecordingPublisher(), enabled=enabled
    )
    embedding = WarmupEmbedding(error=error)
    rerank = WarmupRerank()
    app.state.embedding_model = embedding
    app.state.rerank_model = rerank

    async with app.router.lifespan_context(app):
        for _ in range(50):
            if not expect_embedding or (rerank.queries if expect_rerank else embedding.calls):
                break
            await asyncio.sleep(0.01)
        async with _client(app) as client:
            health = await client.get("/health")

    assert health.status_code == 200
    assert bool(embedding.calls) is expect_embedding
    assert bool(rerank.queries) is expect_rerank


def _live_demo_section(**overrides: object) -> dict[str, object]:
    section: dict[str, object] = {
        "enabled": True,
        "serviceAccountEmail": SERVICE_EMAIL,
        "scenarioIds": [SCENARIO_ID],
        "perVisitorHourlyLimit": 3,
        "dailyLimit": 10,
        "maxConcurrentRuns": 2,
        "runTimeoutSeconds": 600,
        "trustForwardedFor": False,
    }
    section.update(overrides)
    return section


def _app(
    database_url: str,
    tmp_path: Path,
    runner: object,
    publisher: RecordingPublisher,
    **overrides: object,
) -> Any:
    config = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    config["liveDemo"] = _live_demo_section(**overrides)
    config_path = tmp_path / "project.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return create_app(
        database_url=database_url,
        project_config_path=config_path,
        aiops_diagnostic_runner=cast(AiopsDiagnosticRunner, runner),
        live_demo_alert_publisher=publisher,
    )


def _client(app: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


async def _register(client: httpx.AsyncClient, email: str) -> dict[str, Any]:
    response = await client.post(
        "/auth/register",
        json={
            "email": email,
            "displayName": email.split("@")[0],
            "password": "correct horse battery staple",
        },
    )
    assert response.status_code == 201, response.text
    return cast(dict[str, Any], response.json()["data"])


@pytest.fixture
def migrated_database_url(tmp_path: Path) -> str:
    database_path = tmp_path / "live-demo.sqlite3"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database_path}")
    command.upgrade(config, "head")
    return f"sqlite+aiosqlite:///{database_path}"
