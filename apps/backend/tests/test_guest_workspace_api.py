from __future__ import annotations

import json
from collections.abc import AsyncIterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

import httpx
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from super_ai.api.app import AiopsDiagnosticRunner, create_app
from super_ai.guest_access import load_guest_access_settings
from super_ai.memory.models import AuthSessionModel
from super_ai.memory.repositories import DiagnosticTaskRecord, MemoryRepositories
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
            "id": "evt_guest_1",
            "type": "task.status",
            "channel": "aiops",
            "timestamp": "2026-11-10T00:00:00+00:00",
            "task": {"id": task.id, "status": "running", "message": "Planner", "progress": 10},
        }


@dataclass
class AcceptingPublisher:
    async def publish(self, alerts: Sequence[Mapping[str, object]]) -> bool:
        del alerts
        return True


@pytest.mark.asyncio
async def test_guest_entry_creates_distinct_password_less_accounts(
    migrated_database_url: str, tmp_path: Path
) -> None:
    app = _app(migrated_database_url, tmp_path)
    async with _client(app) as client:
        first = await client.post("/auth/guest")
        second = await client.post("/auth/guest")
        first_data = first.json()["data"]
        me = await client.get("/auth/me", headers=_bearer(first_data["accessToken"]))
        login = await client.post(
            "/auth/login",
            json={"email": first_data["user"]["email"], "password": "anything at all"},
        )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first_data["user"]["accountKind"] == "guest"
    assert first_data["user"]["id"] != second.json()["data"]["user"]["id"]
    assert first_data["user"]["displayName"].startswith("访客")
    assert me.status_code == 200
    assert me.json()["data"]["accountKind"] == "guest"
    assert login.status_code == 401
    assert login.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_member_payload_reports_member_account_kind(
    migrated_database_url: str, tmp_path: Path
) -> None:
    app = _app(migrated_database_url, tmp_path)
    async with _client(app) as client:
        member = await _register(client, "owner@example.com")

    assert member["user"]["accountKind"] == "member"


@pytest.mark.asyncio
async def test_guest_entry_respects_disable_switch_and_hourly_limit(
    migrated_database_url: str, tmp_path: Path
) -> None:
    disabled_app = _app(migrated_database_url, tmp_path / "disabled", guest={"enabled": False})
    limited_app = _app(
        migrated_database_url, tmp_path / "limited", guest={"hourlyCreationLimit": 1}
    )
    async with _client(disabled_app) as client:
        disabled = await client.post("/auth/guest")
    async with _client(limited_app) as client:
        allowed = await client.post("/auth/guest")
        blocked = await client.post("/auth/guest")

    assert disabled.status_code == 503
    assert disabled.json()["error"]["code"] == "SYSTEM_UNAVAILABLE"
    assert allowed.status_code == 201
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "BUSINESS_RATE_LIMITED"


@pytest.mark.asyncio
async def test_guest_session_expires_after_ttl(
    migrated_database_url: str, tmp_path: Path
) -> None:
    app = _app(migrated_database_url, tmp_path, guest={"sessionTtlHours": 1})
    async with _client(app) as client:
        guest = (await client.post("/auth/guest")).json()["data"]
        member = await _register(client, "owner@example.com")
        await _age_sessions(app, hours=2)
        expired = await client.get("/auth/me", headers=_bearer(guest["accessToken"]))
        member_me = await client.get("/auth/me", headers=_bearer(member["accessToken"]))

    assert expired.status_code == 401
    assert expired.json()["error"]["code"] == "AUTH_SESSION_REVOKED"
    assert member_me.status_code == 200


@pytest.mark.asyncio
async def test_guest_write_operations_are_forbidden(
    migrated_database_url: str, tmp_path: Path
) -> None:
    runner = RecordingRunner()
    app = _app(migrated_database_url, tmp_path, runner=runner)
    async with _client(app) as client:
        guest = (await client.post("/auth/guest")).json()["data"]
        headers = _bearer(guest["accessToken"])
        kb = f"kb_{guest['user']['id']}"
        responses = [
            await client.post("/aiops/diagnostics", json={"query": "排查"}, headers=headers),
            await client.post(
                "/mcp/connections",
                json={"name": "x", "transport": "sse", "url": "http://127.0.0.1:1/sse"},
                headers=headers,
            ),
            await client.post(
                f"/knowledge-bases/{kb}/documents",
                files={"file": ("sop.md", b"# SOP\n", "text/markdown")},
                headers=headers,
            ),
            await client.delete(f"/knowledge-bases/{kb}/documents/doc_x", headers=headers),
            await client.post("/aiops/diagnostics/diag_x:save-to-knowledge", headers=headers),
            await client.get("/aiops/alerts/active", headers=headers),
        ]
        reads = [
            await client.get("/aiops/diagnostics", headers=headers),
            await client.get("/mcp/connections", headers=headers),
            await client.get(f"/knowledge-bases/{kb}/documents", headers=headers),
        ]

    for response in responses:
        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "AUTH_FORBIDDEN"
    assert all(response.status_code == 200 for response in reads)
    assert runner.tasks == []


@pytest.mark.asyncio
async def test_guest_chat_is_rate_limited(migrated_database_url: str, tmp_path: Path) -> None:
    app = _app(migrated_database_url, tmp_path, guest={"chatMessagesPerHour": 0})
    async with _client(app) as client:
        guest = (await client.post("/auth/guest")).json()["data"]
        headers = _bearer(guest["accessToken"])
        repositories = cast(MemoryRepositories, app.state.memory_repositories)
        session = await repositories.chat.create_session(
            owner_user_id=guest["user"]["id"], session_id="chat_guest_quota"
        )
        session_id = session.id
        streamed = await client.post(
            f"/chat/sessions/{session_id}/messages:stream",
            json={"content": "你好"},
            headers=headers,
        )

    assert streamed.status_code == 429
    assert streamed.json()["error"]["code"] == "BUSINESS_RATE_LIMITED"


@pytest.mark.asyncio
async def test_drill_requester_reads_drill_diagnosis_but_others_cannot(
    migrated_database_url: str, tmp_path: Path
) -> None:
    runner = RecordingRunner()
    app = _app(migrated_database_url, tmp_path, runner=runner)
    async with _client(app) as client:
        service = await _register(client, SERVICE_EMAIL)
        guest_a = (await client.post("/auth/guest")).json()["data"]
        guest_b = (await client.post("/auth/guest")).json()["data"]
        a_headers = _bearer(guest_a["accessToken"])
        b_headers = _bearer(guest_b["accessToken"])

        anonymous = await client.post("/live-demo/runs", json={"scenarioId": SCENARIO_ID})
        created = await client.post(
            "/live-demo/runs", json={"scenarioId": SCENARIO_ID}, headers=a_headers
        )
        diagnostic_id = created.json()["data"]["run"]["diagnosticId"]

        a_list = await client.get("/aiops/diagnostics", headers=a_headers)
        a_detail = await client.get(f"/aiops/diagnostics/{diagnostic_id}", headers=a_headers)
        a_chain = await client.get(
            f"/aiops/diagnostics/{diagnostic_id}/evidence-chain", headers=a_headers
        )
        a_stream = await client.post(
            f"/aiops/diagnostics/{diagnostic_id}:stream", headers=a_headers
        )
        a_save = await client.post(
            f"/aiops/diagnostics/{diagnostic_id}:save-to-knowledge", headers=a_headers
        )
        b_list = await client.get("/aiops/diagnostics", headers=b_headers)
        b_detail = await client.get(f"/aiops/diagnostics/{diagnostic_id}", headers=b_headers)
        b_chain = await client.get(
            f"/aiops/diagnostics/{diagnostic_id}/evidence-chain", headers=b_headers
        )
        b_stream = await client.post(
            f"/aiops/diagnostics/{diagnostic_id}:stream", headers=b_headers
        )

    assert anonymous.status_code == 202
    assert anonymous.json()["data"]["run"]["diagnosticId"] is None
    assert created.status_code == 202
    assert isinstance(diagnostic_id, str)
    assert len(runner.tasks) == 2
    assert all(task.owner_user_id == service["user"]["id"] for task in runner.tasks)

    items = a_list.json()["data"]["items"]
    assert [item["id"] for item in items] == [diagnostic_id]
    assert items[0]["origin"] == "live-drill"
    assert items[0]["simulated"] is True
    assert a_detail.status_code == 200
    assert a_chain.status_code == 200
    assert a_chain.json()["data"]["task"]["id"] == diagnostic_id
    assert a_stream.status_code == 200
    assert "event: task.status" in a_stream.text
    assert a_save.status_code == 403

    assert b_list.json()["data"]["items"] == []
    assert b_detail.status_code == 403
    assert b_chain.status_code == 403
    assert b_stream.status_code == 403


@pytest.mark.asyncio
async def test_member_diagnostics_are_marked_as_workspace_origin(
    migrated_database_url: str, tmp_path: Path
) -> None:
    app = _app(migrated_database_url, tmp_path)
    async with _client(app) as client:
        member = await _register(client, "owner@example.com")
        created = await client.post(
            "/aiops/diagnostics",
            json={"query": "结算服务延迟升高"},
            headers=_bearer(member["accessToken"]),
        )

    assert created.status_code == 202
    assert created.json()["data"]["origin"] == "workspace"
    assert created.json()["data"]["simulated"] is False


@pytest.mark.asyncio
async def test_drill_sop_library_is_read_only_for_authenticated_users(
    migrated_database_url: str, tmp_path: Path
) -> None:
    app = _app(migrated_database_url, tmp_path)
    async with _client(app) as client:
        service = await _register(client, SERVICE_EMAIL)
        service_id = service["user"]["id"]
        repositories = cast(MemoryRepositories, app.state.memory_repositories)
        document = await repositories.documents.create_document(
            owner_user_id=service_id,
            document_id="doc_sop_checkout",
            knowledge_base_id=f"kb_{service_id}",
            filename="checkout-db-pool.md",
            size_bytes=24,
            mime_type="text/markdown",
            content_hash="sha256:sop",
            source="upload",
            metadata={"indexableText": "# 结算连接池耗尽 SOP\n"},
        )
        guest = (await client.post("/auth/guest")).json()["data"]
        headers = _bearer(guest["accessToken"])
        anonymous = await client.get("/live-demo/sop-documents")
        listed = await client.get("/live-demo/sop-documents", headers=headers)
        detail = await client.get(f"/live-demo/sop-documents/{document.id}", headers=headers)
        missing = await client.get("/live-demo/sop-documents/doc_missing", headers=headers)

    assert anonymous.status_code == 401
    assert listed.status_code == 200
    assert [item["filename"] for item in listed.json()["data"]["items"]] == [
        "checkout-db-pool.md"
    ]
    assert "ownerUserId" not in listed.json()["data"]["items"][0]
    assert detail.status_code == 200
    assert detail.json()["data"]["content"] == "# 结算连接池耗尽 SOP\n"
    assert missing.status_code == 404


def test_guest_access_settings_validation(tmp_path: Path) -> None:
    missing = tmp_path / "missing.json"
    missing.write_text("{}", encoding="utf-8")
    assert load_guest_access_settings(config_path=missing).enabled is False

    template = load_guest_access_settings(config_path=TEMPLATE_PATH)
    assert template.enabled is False
    assert template.session_ttl_hours == 24

    invalid = tmp_path / "invalid.json"
    invalid.write_text(
        json.dumps({"guestAccess": {**_guest_section(), "sessionTtlHours": 0}}),
        encoding="utf-8",
    )
    with pytest.raises(ProjectConfigurationError):
        load_guest_access_settings(config_path=invalid)


def test_guest_migration_adds_account_kind_and_drill_requester(
    migrated_database_url: str,
) -> None:
    database_path = migrated_database_url.removeprefix("sqlite+aiosqlite:///")
    engine = create_engine(f"sqlite:///{database_path}")
    try:
        inspector = inspect(engine)
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        run_columns = {column["name"] for column in inspector.get_columns("live_demo_runs")}
        run_indexes = {index["name"] for index in inspector.get_indexes("live_demo_runs")}
    finally:
        engine.dispose()

    assert "account_kind" in user_columns
    assert "requester_user_id" in run_columns
    assert "ix_live_demo_runs_requester_created" in run_indexes


def _guest_section(**overrides: object) -> dict[str, object]:
    return {
        "enabled": True,
        "sessionTtlHours": 24,
        "hourlyCreationLimit": 60,
        "chatMessagesPerHour": 20,
        **overrides,
    }


def _app(
    database_url: str,
    tmp_path: Path,
    *,
    runner: object | None = None,
    guest: Mapping[str, object] | None = None,
) -> Any:
    tmp_path.mkdir(parents=True, exist_ok=True)
    config = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    config["liveDemo"] = {
        **config["liveDemo"],
        "enabled": True,
        "serviceAccountEmail": SERVICE_EMAIL,
        "scenarioIds": [SCENARIO_ID],
        "perVisitorHourlyLimit": 10,
        "dailyLimit": 50,
        "maxConcurrentRuns": 5,
    }
    config["guestAccess"] = _guest_section(**(guest or {}))
    config_path = tmp_path / "project.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return create_app(
        database_url=database_url,
        project_config_path=config_path,
        aiops_diagnostic_runner=cast(AiopsDiagnosticRunner, runner or RecordingRunner()),
        live_demo_alert_publisher=AcceptingPublisher(),
    )


async def _age_sessions(app: Any, *, hours: int) -> None:
    factory = cast(async_sessionmaker[AsyncSession], app.state.memory_session_factory)
    async with factory() as session:
        await session.execute(
            update(AuthSessionModel).values(
                created_at=datetime.now(timezone.utc) - timedelta(hours=hours)
            )
        )
        await session.commit()


def _client(app: Any) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver")


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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
    database_path = tmp_path / "guest-workspace.sqlite3"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database_path}")
    command.upgrade(config, "head")
    return f"sqlite+aiosqlite:///{database_path}"
