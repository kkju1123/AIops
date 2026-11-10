"""Public live incident drill: scenarios, limits, run tokens, and alert publishing."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol, cast

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from super_ai.aiops.fixtures import (
    JAVA_ECOMMERCE_INCIDENTS,
    LIVE_DRILL_INCIDENTS,
    JavaEcommerceIncident,
)
from super_ai.auth.repositories import UserRecord
from super_ai.memory.models import LiveDemoRunModel
from super_ai.memory.repositories import DiagnosticMemoryRepository
from super_ai.project_config import ProjectConfigurationError, load_project_config

LIVE_DEMO_TOKEN_HEADER = "X-Live-Demo-Token"
OBSERVABILITY_SIMULATOR = "simulator"
OBSERVABILITY_CLOUDWATCH = "aws-cloudwatch"
OBSERVABILITY_MODES = frozenset({OBSERVABILITY_SIMULATOR, OBSERVABILITY_CLOUDWATCH})
TERMINAL_TASK_STATUSES = frozenset({"succeeded", "failed", "cancelled"})

DRILL_INCIDENTS: tuple[JavaEcommerceIncident, ...] = LIVE_DRILL_INCIDENTS + JAVA_ECOMMERCE_INCIDENTS

SCENARIO_TITLES: Mapping[str, str] = {
    "checkout-db-pool-exhausted": "结算服务数据库连接池耗尽",
    "java-ecom-payment-gateway-timeout": "支付网关超时",
    "java-ecom-inventory-lock-wait": "库存预占锁等待",
    "java-ecom-order-db-pool-exhausted": "订单库连接池耗尽",
    "java-ecom-cart-redis-latency": "购物车 Redis 延迟",
    "java-ecom-gateway-circuit-open": "网关熔断打开",
    "java-ecom-promotion-cpu-saturation": "促销服务 CPU 饱和",
    "java-ecom-order-kafka-lag": "订单 Kafka 消费积压",
    "java-ecom-search-es-timeout": "搜索 Elasticsearch 超时",
    "java-ecom-auth-jwk-refresh": "认证 JWK 刷新失败",
    "java-ecom-fulfillment-provider-503": "履约服务商 503",
}


class LiveDemoError(RuntimeError):
    """Safe live drill error mapped to the shared API error catalog."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True, slots=True)
class LiveDemoSettings:
    enabled: bool
    service_account_email: str
    scenario_ids: tuple[str, ...]
    per_visitor_hourly_limit: int
    daily_limit: int
    max_concurrent_runs: int
    run_timeout_seconds: int
    trust_forwarded_for: bool
    observability: str = OBSERVABILITY_SIMULATOR

    @property
    def simulated(self) -> bool:
        return self.observability == OBSERVABILITY_SIMULATOR


DISABLED_LIVE_DEMO_SETTINGS = LiveDemoSettings(
    enabled=False,
    service_account_email="",
    scenario_ids=(),
    per_visitor_hourly_limit=0,
    daily_limit=0,
    max_concurrent_runs=0,
    run_timeout_seconds=600,
    trust_forwarded_for=False,
)


def load_live_demo_settings(*, config_path: Path | str | None = None) -> LiveDemoSettings:
    """Load the optional `liveDemo` section; a missing section means disabled."""
    raw = load_project_config(config_path).get("liveDemo")
    if raw is None:
        return DISABLED_LIVE_DEMO_SETTINGS
    if not isinstance(raw, dict):
        raise ProjectConfigurationError("Project config section must be an object: liveDemo")
    section = cast(Mapping[str, Any], raw)
    enabled = section.get("enabled")
    if not isinstance(enabled, bool):
        raise ProjectConfigurationError("Project config field must be a boolean: enabled")
    email = section.get("serviceAccountEmail")
    if not isinstance(email, str):
        raise ProjectConfigurationError(
            "Project config field must be a string: serviceAccountEmail"
        )
    raw_ids = section.get("scenarioIds")
    if not isinstance(raw_ids, list) or not all(
        isinstance(item, str) for item in cast(list[object], raw_ids)
    ):
        raise ProjectConfigurationError("Project config field must be a string list: scenarioIds")
    scenario_ids = tuple(cast(list[str], raw_ids))
    known = {incident.incident_id for incident in DRILL_INCIDENTS}
    unknown = [item for item in scenario_ids if item not in known]
    if unknown:
        raise ProjectConfigurationError("liveDemo.scenarioIds contains unknown scenarios.")
    trust_forwarded_for = section.get("trustForwardedFor", False)
    if not isinstance(trust_forwarded_for, bool):
        raise ProjectConfigurationError(
            "Project config field must be a boolean: trustForwardedFor"
        )
    observability = section.get("observability", OBSERVABILITY_SIMULATOR)
    if observability not in OBSERVABILITY_MODES:
        raise ProjectConfigurationError(
            "liveDemo.observability must be 'simulator' or 'aws-cloudwatch'."
        )
    return LiveDemoSettings(
        observability=cast(str, observability),
        enabled=enabled,
        service_account_email=email.strip().lower(),
        scenario_ids=scenario_ids,
        per_visitor_hourly_limit=_non_negative_int(section, "perVisitorHourlyLimit"),
        daily_limit=_non_negative_int(section, "dailyLimit"),
        max_concurrent_runs=_non_negative_int(section, "maxConcurrentRuns"),
        run_timeout_seconds=max(_non_negative_int(section, "runTimeoutSeconds"), 60),
        trust_forwarded_for=trust_forwarded_for,
    )


@dataclass(frozen=True, slots=True)
class LiveDemoScenario:
    id: str
    title: str
    service: str
    alert_name: str
    severity: str
    symptom: str
    incident: JavaEcommerceIncident

    def diagnostic_query(self, *, simulated: bool = False) -> str:
        evidence = "日志、指标与 SOP" if simulated else "真实日志与 SOP"
        return (
            f"{self.service} 触发告警 {self.alert_name}：{self.symptom}"
            f"请基于{evidence}定位根因，并给出处置建议。"
        )

    def public_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "service": self.service,
            "alertName": self.alert_name,
            "severity": self.severity,
            "symptom": self.symptom,
        }


def enabled_scenarios(settings: LiveDemoSettings) -> list[LiveDemoScenario]:
    incidents = {incident.incident_id: incident for incident in DRILL_INCIDENTS}
    return [
        _scenario(incidents[scenario_id])
        for scenario_id in settings.scenario_ids
        if scenario_id in incidents
    ]


def find_scenario(settings: LiveDemoSettings, scenario_id: str) -> LiveDemoScenario:
    for scenario in enabled_scenarios(settings):
        if scenario.id == scenario_id:
            return scenario
    raise LiveDemoError("VALIDATION_INVALID_ARGUMENT", "该故障场景未开放。")


def build_live_demo_alertmanager_payload(
    scenario: LiveDemoScenario, *, run_id: str, now: datetime
) -> list[dict[str, object]]:
    """Build one Alertmanager v2 alert; the root cause is intentionally omitted."""
    incident = scenario.incident
    starts_at = _as_utc(now)
    return [
        {
            "labels": {
                "alertname": incident.alert_name,
                "service": incident.service,
                "environment": "test",
                "namespace": "java-ecommerce",
                "severity": incident.severity,
                "team": "ecommerce-platform",
                "fixture": "live-incident-drill",
                "incident_id": incident.incident_id,
                "drill_run_id": run_id,
            },
            "annotations": _alert_annotations(incident),
            "startsAt": _iso8601(starts_at),
            "endsAt": _iso8601(starts_at + timedelta(minutes=30)),
            "generatorURL": (
                f"http://localhost:9090/graph?g0.expr={incident.metric_name}"
            ),
        }
    ]


def _alert_annotations(incident: JavaEcommerceIncident) -> dict[str, str]:
    annotations = {
        "summary": incident.symptom,
        "description": (
            f"{incident.metric_name}={incident.metric_value}; threshold {incident.threshold}."
        ),
        "dependency": incident.dependency,
    }
    if incident.trace_id:
        annotations["trace_id"] = incident.trace_id
    return annotations


def diagnostic_alert_input(
    scenario: LiveDemoScenario, *, run_id: str, now: datetime
) -> dict[str, object]:
    """Normalize the published alert into the ActiveAlert shape used by diagnostics."""
    raw = build_live_demo_alertmanager_payload(scenario, run_id=run_id, now=now)[0]
    labels = cast(dict[str, str], raw["labels"])
    annotations = cast(dict[str, str], raw["annotations"])
    return {
        "id": f"live-drill:{run_id}",
        "source": "local-alertmanager",
        "alertName": scenario.alert_name,
        "service": scenario.service,
        "severity": scenario.severity,
        "status": "firing",
        "startsAt": str(raw["startsAt"]),
        "summary": scenario.symptom,
        "labels": labels,
        "annotations": annotations,
        "context": {"liveDemoRunId": run_id},
    }


class LiveDemoAlertPublisher(Protocol):
    async def publish(self, alerts: Sequence[Mapping[str, object]]) -> bool:
        """Publish alerts; return whether the alert provider accepted them."""
        ...


class AlertmanagerLiveDemoPublisher:
    """POST alerts to the configured local Alertmanager v2 API."""

    def __init__(
        self,
        *,
        alerts_api: str | None,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._alerts_api = alerts_api
        self._timeout_seconds = timeout_seconds
        self._transport = transport

    async def publish(self, alerts: Sequence[Mapping[str, object]]) -> bool:
        if not self._alerts_api:
            return False
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds, transport=self._transport
            ) as client:
                response = await client.post(self._alerts_api, json=list(alerts))
        except httpx.HTTPError:
            return False
        return response.status_code in {200, 201, 202}


def build_alertmanager_live_demo_publisher(
    *, config_path: Path | str | None = None
) -> AlertmanagerLiveDemoPublisher:
    raw = load_project_config(config_path).get("prometheusAlerts")
    alerts_api: str | None = None
    timeout_seconds = 5.0
    if isinstance(raw, dict):
        section = cast(Mapping[str, Any], raw)
        timeout = section.get("timeoutSeconds")
        if isinstance(timeout, (int, float)):
            timeout_seconds = float(timeout)
        sources = section.get("sources")
        if isinstance(sources, list):
            for source in cast(list[object], sources):
                if not isinstance(source, dict):
                    continue
                mapping = cast(Mapping[str, Any], source)
                api = mapping.get("alertsApi")
                if (
                    mapping.get("type") == "alertmanager-v2"
                    and isinstance(api, str)
                    and api.strip()
                ):
                    alerts_api = api.strip()
                    break
    return AlertmanagerLiveDemoPublisher(alerts_api=alerts_api, timeout_seconds=timeout_seconds)


@dataclass(frozen=True, slots=True)
class LiveDemoRunRecord:
    id: str
    owner_user_id: str
    diagnostic_task_id: str
    scenario_id: str
    visitor_key_hash: str
    access_token_hash: str
    alert_published: bool
    created_at: datetime
    requester_user_id: str | None = None


class SQLiteLiveDemoRunRepository:
    """SQLAlchemy persistence for live drill runs."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        *,
        run_id: str,
        owner_user_id: str,
        diagnostic_task_id: str,
        scenario_id: str,
        visitor_key_hash: str,
        access_token_hash: str,
        alert_published: bool,
        created_at: datetime,
        requester_user_id: str | None = None,
    ) -> LiveDemoRunRecord:
        row = LiveDemoRunModel(
            id=run_id,
            owner_user_id=owner_user_id,
            diagnostic_task_id=diagnostic_task_id,
            scenario_id=scenario_id,
            visitor_key_hash=visitor_key_hash,
            access_token_hash=access_token_hash,
            alert_published=alert_published,
            requester_user_id=requester_user_id,
            created_at=created_at,
        )
        async with self._session_factory() as session:
            session.add(row)
            await session.commit()
        return _run_record(row)

    async def get(self, run_id: str) -> LiveDemoRunRecord | None:
        async with self._session_factory() as session:
            row = await session.get(LiveDemoRunModel, run_id)
        return _run_record(row) if row is not None else None

    async def find_for_requester(
        self, *, requester_user_id: str, diagnostic_task_id: str
    ) -> LiveDemoRunRecord | None:
        """Return the run only when `requester_user_id` triggered it."""
        stmt = select(LiveDemoRunModel).where(
            LiveDemoRunModel.requester_user_id == requester_user_id,
            LiveDemoRunModel.diagnostic_task_id == diagnostic_task_id,
        )
        async with self._session_factory() as session:
            row = (await session.scalars(stmt)).one_or_none()
        return _run_record(row) if row is not None else None

    async def list_for_requester(
        self, *, requester_user_id: str, limit: int = 50
    ) -> list[LiveDemoRunRecord]:
        stmt = (
            select(LiveDemoRunModel)
            .where(LiveDemoRunModel.requester_user_id == requester_user_id)
            .order_by(LiveDemoRunModel.created_at.desc())
            .limit(limit)
        )
        async with self._session_factory() as session:
            rows = (await session.scalars(stmt)).all()
        return [_run_record(row) for row in rows]

    async def count_since(self, *, since: datetime, visitor_key_hash: str | None = None) -> int:
        stmt = select(func.count()).select_from(LiveDemoRunModel).where(
            LiveDemoRunModel.created_at >= since
        )
        if visitor_key_hash is not None:
            stmt = stmt.where(LiveDemoRunModel.visitor_key_hash == visitor_key_hash)
        async with self._session_factory() as session:
            return int((await session.scalar(stmt)) or 0)

    async def list_since(self, *, since: datetime) -> list[LiveDemoRunRecord]:
        stmt = (
            select(LiveDemoRunModel)
            .where(LiveDemoRunModel.created_at >= since)
            .order_by(LiveDemoRunModel.created_at.desc())
        )
        async with self._session_factory() as session:
            rows = (await session.scalars(stmt)).all()
        return [_run_record(row) for row in rows]

    async def list_recent(self, *, limit: int) -> list[LiveDemoRunRecord]:
        stmt = select(LiveDemoRunModel).order_by(LiveDemoRunModel.created_at.desc()).limit(limit)
        async with self._session_factory() as session:
            rows = (await session.scalars(stmt)).all()
        return [_run_record(row) for row in rows]


class LiveDemoUserLookup(Protocol):
    async def find_user_by_email(self, email: str) -> UserRecord | None:
        """Find a user by normalized email."""
        ...


@dataclass(frozen=True, slots=True)
class LiveDemoQuota:
    visitor_limit: int
    visitor_remaining: int
    daily_limit: int
    daily_remaining: int
    max_concurrent_runs: int
    running: int

    def payload(self) -> dict[str, int]:
        return {
            "visitorLimit": self.visitor_limit,
            "visitorRemaining": self.visitor_remaining,
            "dailyLimit": self.daily_limit,
            "dailyRemaining": self.daily_remaining,
            "maxConcurrentRuns": self.max_concurrent_runs,
            "running": self.running,
        }


class LiveDemoService:
    """Enforce availability and cost limits for public live drills."""

    def __init__(
        self,
        *,
        settings: LiveDemoSettings,
        users: LiveDemoUserLookup,
        runs: SQLiteLiveDemoRunRepository,
        diagnostics: DiagnosticMemoryRepository,
        now: datetime | None = None,
    ) -> None:
        self._settings = settings
        self._users = users
        self._runs = runs
        self._diagnostics = diagnostics
        self._now = now

    @property
    def settings(self) -> LiveDemoSettings:
        return self._settings

    async def service_account(self) -> UserRecord | None:
        if not self._settings.service_account_email:
            return None
        return await self._users.find_user_by_email(self._settings.service_account_email)

    async def unavailable_reason(self) -> str | None:
        if not self._settings.enabled:
            return "实时演练当前未开启。"
        if not self._settings.scenario_ids:
            return "当前没有开放的故障场景。"
        if await self.service_account() is None:
            return "演练服务账号尚未准备好。"
        return None

    async def quota(self, visitor_key: str) -> LiveDemoQuota:
        now = self._current_time()
        visitor_count = await self._runs.count_since(
            since=now - timedelta(hours=1), visitor_key_hash=visitor_key
        )
        daily_count = await self._runs.count_since(since=now - timedelta(days=1))
        running = await self._running_count(now)
        return LiveDemoQuota(
            visitor_limit=self._settings.per_visitor_hourly_limit,
            visitor_remaining=max(self._settings.per_visitor_hourly_limit - visitor_count, 0),
            daily_limit=self._settings.daily_limit,
            daily_remaining=max(self._settings.daily_limit - daily_count, 0),
            max_concurrent_runs=self._settings.max_concurrent_runs,
            running=running,
        )

    async def ensure_can_start(self, visitor_key: str) -> UserRecord:
        reason = await self.unavailable_reason()
        if reason is not None:
            raise LiveDemoError("SYSTEM_UNAVAILABLE", reason)
        account = await self.service_account()
        if account is None:
            raise LiveDemoError("SYSTEM_UNAVAILABLE", "演练服务账号尚未准备好。")
        quota = await self.quota(visitor_key)
        if quota.visitor_remaining <= 0:
            raise LiveDemoError(
                "BUSINESS_RATE_LIMITED", "你在 1 小时内的演练次数已用完，请稍后再试。"
            )
        if quota.daily_remaining <= 0:
            raise LiveDemoError("BUSINESS_RATE_LIMITED", "今日演练次数已用完，请明天再试。")
        if quota.running >= quota.max_concurrent_runs:
            raise LiveDemoError(
                "BUSINESS_RATE_LIMITED", "当前正在进行的演练较多，请稍后再试。"
            )
        return account

    async def latest_successful_run(self) -> dict[str, object] | None:
        for run in await self._runs.list_recent(limit=20):
            task = await self._diagnostics.get_task(
                owner_user_id=run.owner_user_id, task_id=run.diagnostic_task_id
            )
            if task is None or task.status != "succeeded" or task.completed_at is None:
                continue
            reports = await self._diagnostics.list_reports(
                owner_user_id=run.owner_user_id, task_id=task.id
            )
            if not reports:
                continue
            report = reports[-1]
            scenario = next(
                (item for item in enabled_scenarios(self._settings) if item.id == run.scenario_id),
                None,
            )
            completed_at = _as_utc(task.completed_at)
            return {
                "runId": run.id,
                "scenarioId": run.scenario_id,
                "scenarioTitle": scenario.title if scenario is not None else run.scenario_id,
                "startedAt": run.created_at.isoformat(),
                "completedAt": completed_at.isoformat(),
                "durationSeconds": round((completed_at - run.created_at).total_seconds(), 1),
                "report": {
                    "id": report.id,
                    "title": report.title,
                    "content": report.content,
                    "format": "markdown",
                },
            }
        return None

    async def _running_count(self, now: datetime) -> int:
        since = now - timedelta(seconds=self._settings.run_timeout_seconds)
        running = 0
        for run in await self._runs.list_since(since=since):
            task = await self._diagnostics.get_task(
                owner_user_id=run.owner_user_id, task_id=run.diagnostic_task_id
            )
            if task is not None and task.status not in TERMINAL_TASK_STATUSES:
                running += 1
        return running

    def _current_time(self) -> datetime:
        return self._now if self._now is not None else datetime.now(timezone.utc)


def new_run_token() -> str:
    return secrets.token_urlsafe(32)


def hash_run_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def run_token_matches(run: LiveDemoRunRecord, token: str | None) -> bool:
    if not token:
        return False
    return secrets.compare_digest(run.access_token_hash, hash_run_token(token))


def visitor_key_hash(client_ip: str) -> str:
    return hashlib.sha256(f"live-demo:{client_ip}".encode()).hexdigest()


def client_ip_for(
    *, direct_host: str | None, forwarded_for: str | None, trust_forwarded_for: bool
) -> str:
    if trust_forwarded_for and forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    return direct_host or "unknown"


def _scenario(incident: JavaEcommerceIncident) -> LiveDemoScenario:
    return LiveDemoScenario(
        id=incident.incident_id,
        title=SCENARIO_TITLES.get(incident.incident_id, incident.alert_name),
        service=incident.service,
        alert_name=incident.alert_name,
        severity=incident.severity,
        symptom=incident.symptom,
        incident=incident,
    )


def _run_record(row: LiveDemoRunModel) -> LiveDemoRunRecord:
    return LiveDemoRunRecord(
        id=row.id,
        owner_user_id=row.owner_user_id,
        diagnostic_task_id=row.diagnostic_task_id,
        scenario_id=row.scenario_id,
        visitor_key_hash=row.visitor_key_hash,
        access_token_hash=row.access_token_hash,
        alert_published=row.alert_published,
        created_at=_as_utc(row.created_at),
        requester_user_id=row.requester_user_id,
    )


def _non_negative_int(section: Mapping[str, Any], key: str) -> int:
    value = section.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ProjectConfigurationError(f"Project config field must be a non-negative int: {key}")
    return value


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc)
    return value.replace(tzinfo=timezone.utc)


def _iso8601(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")
