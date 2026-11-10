"""Scenario-driven log and metric generation for the public live drill.

Everything produced here is synthetic and labelled `simulated=true`. It is used only by the
public `/live` drill through the fault simulator MCP server, never by authenticated diagnostics.
The generator never emits an incident's root cause. It emits clue logs that point at it,
plus unrelated decoys, so the diagnosis has to infer the cause from evidence.
"""

from __future__ import annotations

import json
import random
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import cast

from super_ai.aiops.fixtures import (
    JAVA_ECOMMERCE_INCIDENTS,
    LIVE_DRILL_INCIDENTS,
    JavaEcommerceIncident,
    clues_for,
)

SIMULATED_FAULT_ENV = "SUPER_AI_SIMULATED_FAULT"
SIMULATOR_SOURCE = "fault-simulator"
LOG_TOOL = "query_service_logs"
METRIC_TOOL = "query_service_metrics"
SIMULATOR_TOOLS = (LOG_TOOL, METRIC_TOOL)

# The alert fires after its threshold has held for a few minutes, so the fault starts earlier.
FAULT_LEAD = timedelta(minutes=6)
DEFAULT_WINDOW = timedelta(minutes=30)
MAX_WINDOW = timedelta(hours=2)
MAX_LOG_LIMIT = 50
# An unrelated, harmless deploy well before the fault: a deliberate red herring.
DECOY_DEPLOY_LEAD = timedelta(minutes=18)
MAX_METRIC_POINTS = 60
ERROR_RATE_METRIC = "error_rate_percent"
LATENCY_METRIC = "request_latency_p95_ms"

SIMULATED_INCIDENTS: tuple[JavaEcommerceIncident, ...] = (
    LIVE_DRILL_INCIDENTS + JAVA_ECOMMERCE_INCIDENTS
)
_EVENT_OVERRIDES = {"checkout-db-pool-exhausted": "database_connection_pool_exhausted"}
_ENDPOINTS = {
    "checkout-service": "POST /api/checkout",
    "payment-service": "POST /api/payments/confirm",
    "inventory-service": "POST /api/inventory/reserve",
    "order-service": "POST /api/orders",
    "cart-service": "GET /api/cart",
    "api-gateway": "POST /api/checkout",
    "promotion-service": "POST /api/promotions/apply",
    "order-event-consumer": "consume order-events",
    "product-search-service": "GET /api/search",
    "auth-service": "POST /api/auth/verify",
    "fulfillment-service": "POST /api/shipments",
}


class SimulatorError(ValueError):
    """Raised when a simulated fault or tool argument is invalid."""


@dataclass(frozen=True, slots=True)
class SimulatedFault:
    """One fault injected for a single drill run."""

    run_id: str
    scenario_id: str
    injected_at: datetime

    @property
    def incident(self) -> JavaEcommerceIncident:
        return find_simulated_incident(self.scenario_id)

    @property
    def onset(self) -> datetime:
        return self.injected_at - FAULT_LEAD

    def payload(self) -> dict[str, object]:
        return {
            "runId": self.run_id,
            "scenarioId": self.scenario_id,
            "service": self.incident.service,
            "injectedAt": _iso(self.injected_at),
        }

    def to_env_value(self) -> str:
        return json.dumps(self.payload(), ensure_ascii=False)


def find_simulated_incident(scenario_id: str) -> JavaEcommerceIncident:
    for incident in SIMULATED_INCIDENTS:
        if incident.incident_id == scenario_id:
            return incident
    raise SimulatorError(f"Unknown simulated scenario: {scenario_id}")


def simulated_fault_from_payload(value: object) -> SimulatedFault:
    if not isinstance(value, Mapping):
        raise SimulatorError("Simulated fault must be an object.")
    payload = cast(Mapping[str, object], value)
    run_id = payload.get("runId")
    scenario_id = payload.get("scenarioId")
    injected_at = payload.get("injectedAt")
    if not isinstance(run_id, str) or not run_id:
        raise SimulatorError("Simulated fault requires runId.")
    if not isinstance(scenario_id, str):
        raise SimulatorError("Simulated fault requires scenarioId.")
    if not isinstance(injected_at, str):
        raise SimulatorError("Simulated fault requires injectedAt.")
    fault = SimulatedFault(
        run_id=run_id, scenario_id=scenario_id, injected_at=_parse_time(injected_at)
    )
    find_simulated_incident(scenario_id)
    return fault


def simulated_fault_from_env_value(value: str | None) -> SimulatedFault:
    if not value:
        raise SimulatorError("No simulated fault was injected for this simulator process.")
    try:
        decoded: object = json.loads(value)
    except json.JSONDecodeError as exc:
        raise SimulatorError("Simulated fault is not valid JSON.") from exc
    return simulated_fault_from_payload(decoded)


def event_name(incident: JavaEcommerceIncident) -> str:
    override = _EVENT_OVERRIDES.get(incident.incident_id)
    if override is not None:
        return override
    return incident.incident_id.removeprefix("java-ecom-").replace("-", "_")


def default_metric_names(incident: JavaEcommerceIncident) -> list[str]:
    return [incident.metric_name, ERROR_RATE_METRIC, LATENCY_METRIC]


def simulate_logs(
    fault: SimulatedFault,
    *,
    service: str,
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = 20,
    now: datetime | None = None,
) -> dict[str, object]:
    """Return the newest logs for `service` in the window, plus a summary of all matches."""
    start, end = _window(fault, start_time, end_time, now)
    bounded_limit = max(1, min(limit, MAX_LOG_LIMIT))
    incident = fault.incident
    rng = random.Random(f"{fault.run_id}:logs:{service}")
    records: list[dict[str, object]] = []
    endpoint = _ENDPOINTS.get(service, "GET /api")

    cursor = start
    while cursor <= end:
        records.append(_background_log(fault, service, endpoint, cursor, rng))
        cursor += timedelta(seconds=30)

    if service == incident.service:
        warn_at = fault.onset - timedelta(minutes=2)
        while warn_at < fault.onset:
            if start <= warn_at <= end:
                records.append(_precursor_log(fault, endpoint, warn_at, rng))
            warn_at += timedelta(seconds=40)
        cursor = fault.onset
        sequence = 0
        while cursor <= end:
            if cursor >= start:
                sequence += 1
                records.append(_fault_log(fault, endpoint, cursor, sequence, rng))
            cursor += timedelta(seconds=rng.randint(12, 24))
        records.extend(_clue_logs(fault, endpoint, start, end, rng))
    records.extend(_decoy_logs(fault, service, start, end, rng))

    records.sort(key=lambda record: str(record["@timestamp"]), reverse=True)
    errors = [record for record in records if record["level"] == "ERROR"]
    warnings = [record for record in records if record["level"] == "WARN"]
    exceptions = sorted({str(record["exception"]) for record in errors if "exception" in record})
    return {
        "simulated": True,
        "source": SIMULATOR_SOURCE,
        "service": service,
        "window": {"start": _iso(start), "end": _iso(end)},
        "summary": {
            "totalMatched": len(records),
            "returned": min(bounded_limit, len(records)),
            "errorCount": len(errors),
            "warnCount": len(warnings),
            "firstErrorAt": str(errors[-1]["@timestamp"]) if errors else None,
            "exceptions": exceptions,
            "notableEvents": _notable_events(records),
        },
        "records": records[:bounded_limit],
    }


def simulate_metrics(
    fault: SimulatedFault,
    *,
    service: str,
    metric_names: Sequence[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    """Return per-minute series; the scenario metric rises after the fault onset."""
    start, end = _window(fault, start_time, end_time, now)
    incident = fault.incident
    names = list(metric_names) if metric_names else default_metric_names(incident)
    faulted = service == incident.service
    step = max(timedelta(minutes=1), (end - start) / MAX_METRIC_POINTS)
    series: list[dict[str, object]] = []
    for name in names[:6]:
        profile = _metric_profile(incident, name)
        if profile is None:
            series.append({"name": name, "available": False})
            continue
        unit, baseline, peak, threshold = profile
        rng = random.Random(f"{fault.run_id}:metric:{service}:{name}")
        points: list[dict[str, object]] = []
        cursor = start
        while cursor <= end:
            value = _metric_value(cursor, fault.onset, baseline, peak, faulted, rng)
            points.append({"timestamp": _iso(cursor), "value": value})
            cursor += step
        values = [cast(float, point["value"]) for point in points]
        series.append(
            {
                "name": name,
                "available": True,
                "unit": unit,
                "threshold": threshold,
                "latest": values[-1] if values else None,
                "max": max(values) if values else None,
                "baseline": round(baseline, 2),
                "points": points,
            }
        )
    return {
        "simulated": True,
        "source": SIMULATOR_SOURCE,
        "service": service,
        "window": {"start": _iso(start), "end": _iso(end)},
        "metrics": series,
    }


MAX_NOTABLE_EVENTS = 10
NOTABLE_SAMPLE_CHARS = 180


def _notable_events(records: Sequence[Mapping[str, object]]) -> list[dict[str, object]]:
    """Aggregate non-routine events over the whole window, like `stats count() by event`."""
    grouped: dict[str, dict[str, object]] = {}
    for record in sorted(records, key=lambda item: str(item["@timestamp"])):
        event = str(record.get("event"))
        if event == "request_completed":
            continue
        timestamp = str(record["@timestamp"])
        entry = grouped.get(event)
        if entry is None:
            grouped[event] = {
                "event": event,
                "level": record.get("level"),
                "count": 1,
                "firstAt": timestamp,
                "lastAt": timestamp,
                "sample": str(record.get("message", ""))[:NOTABLE_SAMPLE_CHARS],
            }
        else:
            entry["count"] = cast(int, entry["count"]) + 1
            entry["lastAt"] = timestamp
    return list(grouped.values())[:MAX_NOTABLE_EVENTS]


def _clue_logs(
    fault: SimulatedFault,
    endpoint: str,
    start: datetime,
    end: datetime,
    rng: random.Random,
) -> list[dict[str, object]]:
    incident = fault.incident
    records: list[dict[str, object]] = []
    for clue in clues_for(incident):
        cursor = fault.onset + timedelta(seconds=clue.offset_seconds)
        while cursor <= end:
            if cursor >= start:
                records.append(
                    {
                        "@timestamp": _iso(cursor),
                        "level": clue.level,
                        "service": incident.service,
                        "host": f"{incident.service}-0{rng.randint(1, 3)}",
                        "logger": clue.logger or incident.logger,
                        "event": clue.event,
                        "endpoint": endpoint,
                        "trace_id": _hex(rng, 32),
                        "message": clue.message,
                        "simulated": True,
                        "simulation_run_id": fault.run_id,
                    }
                )
            if clue.repeat_seconds <= 0:
                break
            cursor += timedelta(seconds=clue.repeat_seconds)
    return records


def _decoy_logs(
    fault: SimulatedFault,
    service: str,
    start: datetime,
    end: datetime,
    rng: random.Random,
) -> list[dict[str, object]]:
    """Unrelated but plausible events, so evidence must be read rather than pattern-matched."""
    records: list[dict[str, object]] = []
    deploy_at = fault.onset - DECOY_DEPLOY_LEAD
    if start <= deploy_at <= end:
        records.append(
            {
                "@timestamp": _iso(deploy_at),
                "level": "INFO",
                "service": service,
                "host": f"{service}-01",
                "event": "deployment_completed",
                "message": f"Rolling deployment of {service} finished: log format tweak, "
                "no code path changes",
                "simulated": True,
                "simulation_run_id": fault.run_id,
            }
        )
    cursor = start + timedelta(seconds=rng.randint(30, 200))
    while cursor <= end:
        records.append(
            {
                "@timestamp": _iso(cursor),
                "level": "INFO",
                "service": service,
                "host": f"{service}-0{rng.randint(1, 3)}",
                "event": "gc_pause",
                "message": f"G1 Young Generation pause {rng.randint(18, 60)}ms",
                "simulated": True,
                "simulation_run_id": fault.run_id,
            }
        )
        cursor += timedelta(seconds=rng.randint(240, 420))
    return records


def _background_log(
    fault: SimulatedFault,
    service: str,
    endpoint: str,
    at: datetime,
    rng: random.Random,
) -> dict[str, object]:
    latency = rng.randint(60, 220)
    return {
        "@timestamp": _iso(at),
        "level": "INFO",
        "service": service,
        "host": f"{service}-0{rng.randint(1, 3)}",
        "event": "request_completed",
        "endpoint": endpoint,
        "status": 200,
        "latency_ms": latency,
        "trace_id": _hex(rng, 32),
        "message": f"{endpoint} completed in {latency}ms",
        "simulated": True,
        "simulation_run_id": fault.run_id,
    }


def _precursor_log(
    fault: SimulatedFault, endpoint: str, at: datetime, rng: random.Random
) -> dict[str, object]:
    incident = fault.incident
    latency = rng.randint(450, 900)
    return {
        "@timestamp": _iso(at),
        "level": "WARN",
        "service": incident.service,
        "host": f"{incident.service}-0{rng.randint(1, 3)}",
        "logger": incident.logger,
        "event": "dependency_latency_rising",
        "endpoint": endpoint,
        "dependency": incident.dependency,
        "latency_ms": latency,
        "trace_id": _hex(rng, 32),
        "message": f"{incident.dependency} responded slowly ({latency}ms)",
        "simulated": True,
        "simulation_run_id": fault.run_id,
    }


def _fault_log(
    fault: SimulatedFault,
    endpoint: str,
    at: datetime,
    sequence: int,
    rng: random.Random,
) -> dict[str, object]:
    incident = fault.incident
    minutes_in = max(0.0, (at - fault.onset).total_seconds() / 60)
    error_rate = round(min(0.45, 0.04 + minutes_in * 0.03 + rng.random() * 0.02), 3)
    latency = rng.randint(1800, 3200)
    trace_id = incident.trace_id or _hex(rng, 32)
    message = (
        incident.symptom
        if sequence % 2
        else f"{incident.exception}: call to {incident.dependency} failed after {latency}ms"
    )
    return {
        "@timestamp": _iso(at),
        "level": "ERROR",
        "service": incident.service,
        "host": f"{incident.service}-0{rng.randint(1, 3)}",
        "logger": incident.logger,
        "thread": f"http-nio-8080-exec-{rng.randint(1, 48)}",
        "event": event_name(incident),
        "endpoint": endpoint,
        "status": 503,
        "exception": incident.exception,
        "dependency": incident.dependency,
        "latency_ms": latency,
        "error_rate": error_rate,
        "metric_name": incident.metric_name,
        "metric_value": incident.metric_value,
        "trace_id": trace_id,
        "message": message,
        "simulated": True,
        "simulation_run_id": fault.run_id,
    }


def _metric_profile(
    incident: JavaEcommerceIncident, name: str
) -> tuple[str, float, float, str | None] | None:
    if name == incident.metric_name:
        peak, unit = _parse_metric_value(incident.metric_value)
        baseline = 0.0 if peak <= 1 else peak * (0.08 if unit == "%" else 0.12)
        return unit, baseline, peak, incident.threshold
    if name == ERROR_RATE_METRIC:
        return "%", 0.3, 18.0, None
    if name == LATENCY_METRIC:
        return "ms", 150.0, 2400.0, None
    return None


def _metric_value(
    at: datetime,
    onset: datetime,
    baseline: float,
    peak: float,
    faulted: bool,
    rng: random.Random,
) -> float:
    noise = 1 + (rng.random() - 0.5) * 0.12
    if not faulted or at < onset:
        return round(baseline * noise, 2)
    ramp = min(1.0, (at - onset).total_seconds() / 120)
    return round((baseline + (peak - baseline) * ramp) * noise, 2)


def _parse_metric_value(raw: str) -> tuple[float, str]:
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*(%|ms|s)?\s*", raw)
    if match is None:
        raise SimulatorError(f"Unsupported metric value: {raw}")
    return float(match.group(1)), match.group(2) or "count"


def _window(
    fault: SimulatedFault,
    start_time: str | None,
    end_time: str | None,
    now: datetime | None,
) -> tuple[datetime, datetime]:
    current = _as_utc(now or datetime.now(timezone.utc))
    end = _parse_time(end_time) if end_time else current
    end = min(end, current)
    start = _parse_time(start_time) if start_time else end - DEFAULT_WINDOW
    if start >= end:
        raise SimulatorError("start_time must be earlier than end_time.")
    if end - start > MAX_WINDOW:
        start = end - MAX_WINDOW
    return start, end


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SimulatorError(f"Invalid ISO-8601 time: {value}") from exc
    return _as_utc(parsed)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _as_utc(value).isoformat(timespec="seconds").replace("+00:00", "Z")


def _hex(rng: random.Random, length: int) -> str:
    return "".join(rng.choice("0123456789abcdef") for _ in range(length))
