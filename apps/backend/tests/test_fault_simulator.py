from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, cast

import pytest

from super_ai.aiops.fixtures import clues_for
from super_ai.simulator import (
    SIMULATED_INCIDENTS,
    SimulatedFault,
    SimulatorError,
    find_simulated_incident,
    simulate_logs,
    simulate_metrics,
    simulated_fault_from_payload,
)
from super_ai.simulator.client import build_simulator_client

INJECTED_AT = datetime(2026, 11, 8, 4, 0, tzinfo=timezone.utc)
NOW = INJECTED_AT + timedelta(seconds=5)


def _fault(
    scenario_id: str = "java-ecom-cart-redis-latency", run_id: str = "run-a"
) -> SimulatedFault:
    return SimulatedFault(run_id=run_id, scenario_id=scenario_id, injected_at=INJECTED_AT)


@pytest.mark.parametrize("incident", SIMULATED_INCIDENTS, ids=lambda item: item.incident_id)
def test_every_scenario_produces_labelled_faulty_logs_without_root_cause(incident: Any) -> None:
    fault = _fault(incident.incident_id)

    logs = simulate_logs(fault, service=incident.service, now=NOW, limit=50)
    metrics = simulate_metrics(fault, service=incident.service, now=NOW)

    records = cast(list[dict[str, object]], logs["records"])
    summary = cast(dict[str, object], logs["summary"])
    assert logs["simulated"] is True
    assert all(record["simulated"] is True for record in records)
    assert cast(int, summary["errorCount"]) > 0
    assert summary["exceptions"] == [incident.exception]
    assert incident.root_cause not in json.dumps(logs, ensure_ascii=False)
    assert incident.root_cause not in json.dumps(metrics, ensure_ascii=False)
    key_metric = cast(list[dict[str, Any]], metrics["metrics"])[0]
    assert key_metric["name"] == incident.metric_name
    assert key_metric["threshold"] == incident.threshold
    assert key_metric["max"] > key_metric["baseline"]


def test_output_is_reproducible_per_run_and_differs_between_runs() -> None:
    first = simulate_logs(_fault(run_id="run-a"), service="cart-service", now=NOW)
    again = simulate_logs(_fault(run_id="run-a"), service="cart-service", now=NOW)
    other = simulate_logs(_fault(run_id="run-b"), service="cart-service", now=NOW)

    assert first == again
    assert first["records"] != other["records"]


def test_unaffected_service_stays_healthy() -> None:
    fault = _fault("java-ecom-cart-redis-latency")

    logs = simulate_logs(fault, service="payment-service", now=NOW)
    metrics = simulate_metrics(fault, service="payment-service", now=NOW)

    assert cast(dict[str, object], logs["summary"])["errorCount"] == 0
    error_rate = next(
        item
        for item in cast(list[dict[str, Any]], metrics["metrics"])
        if item["name"] == "error_rate_percent"
    )
    assert error_rate["max"] < 1


def test_fault_starts_before_the_alert_and_metrics_ramp_after_onset() -> None:
    fault = _fault("java-ecom-cart-redis-latency")
    logs = simulate_logs(fault, service="cart-service", now=NOW)
    metrics = simulate_metrics(fault, service="cart-service", now=NOW)

    first_error = datetime.fromisoformat(
        str(cast(dict[str, object], logs["summary"])["firstErrorAt"]).replace("Z", "+00:00")
    )
    assert fault.onset <= first_error < INJECTED_AT
    redis = cast(list[dict[str, Any]], metrics["metrics"])[0]
    onset = "2026-11-08T03:54"
    before = [point["value"] for point in redis["points"] if point["timestamp"] < onset]
    assert max(before) < 500 < redis["latest"]


def test_window_and_limit_are_bounded() -> None:
    fault = _fault()

    logs = simulate_logs(
        fault,
        service="cart-service",
        start_time="2026-11-01T00:00:00Z",
        end_time="2026-11-09T00:00:00Z",
        limit=10_000,
        now=NOW,
    )

    window = cast(dict[str, str], logs["window"])
    assert window["end"] == "2026-11-08T04:00:05Z"
    assert window["start"] == "2026-11-08T02:00:05Z"
    assert len(cast(list[object], logs["records"])) == 50
    with pytest.raises(SimulatorError):
        simulate_logs(fault, service="cart-service", start_time="2026-11-08T05:00:00Z", now=NOW)


def test_unknown_metric_is_reported_as_unavailable() -> None:
    metrics = simulate_metrics(
        _fault(), service="cart-service", metric_names=["made_up_metric"], now=NOW
    )

    assert metrics["metrics"] == [{"name": "made_up_metric", "available": False}]


def test_fault_payload_round_trip_and_validation() -> None:
    fault = _fault("checkout-db-pool-exhausted")

    assert simulated_fault_from_payload(fault.payload()) == fault
    assert find_simulated_incident("checkout-db-pool-exhausted").service == "checkout-service"
    with pytest.raises(SimulatorError):
        simulated_fault_from_payload({**fault.payload(), "scenarioId": "unknown"})
    with pytest.raises(SimulatorError):
        simulated_fault_from_payload("not-an-object")


@pytest.mark.asyncio
async def test_simulator_mcp_server_serves_the_injected_fault() -> None:
    fault = SimulatedFault(
        run_id="run-mcp",
        scenario_id="java-ecom-order-kafka-lag",
        injected_at=datetime.now(timezone.utc),
    )
    client = build_simulator_client(fault)

    tools = await client.discover_tools()
    logs_output = await client.call_tool("query_service_logs", {"service": "order-event-consumer"})
    metrics_output = await client.call_tool(
        "query_service_metrics", {"service": "order-event-consumer"}
    )

    assert sorted(tool.name for tool in tools) == ["query_service_logs", "query_service_metrics"]
    logs = json.loads(cast(list[dict[str, str]], logs_output)[0]["text"])
    metrics = json.loads(cast(list[dict[str, str]], metrics_output)[0]["text"])
    assert logs["simulated"] is True
    assert logs["records"][0]["simulation_run_id"] == "run-mcp"
    assert metrics["metrics"][0]["name"] == "kafka_consumer_group_lag"


@pytest.mark.parametrize("incident", SIMULATED_INCIDENTS, ids=lambda item: item.incident_id)
def test_every_scenario_surfaces_its_clues_in_notable_events(incident: Any) -> None:
    fault = _fault(incident.incident_id)

    logs = simulate_logs(fault, service=incident.service, now=NOW, limit=5)

    notable = cast(list[dict[str, Any]], cast(dict[str, object], logs["summary"])["notableEvents"])
    events = {item["event"] for item in notable}
    assert {clue.event for clue in clues_for(incident)} <= events
    assert "deployment_completed" in events


def test_one_off_clue_outside_the_record_limit_is_still_summarised() -> None:
    fault = _fault("java-ecom-promotion-cpu-saturation")

    logs = simulate_logs(fault, service="promotion-service", now=NOW, limit=3)

    records = cast(list[dict[str, Any]], logs["records"])
    notable = cast(list[dict[str, Any]], cast(dict[str, object], logs["summary"])["notableEvents"])
    assert all(record["event"] != "promotion_rule_published" for record in records)
    published = next(item for item in notable if item["event"] == "promotion_rule_published")
    assert published["count"] == 1
    assert "bundle-2026-1111" in published["sample"]


def test_unaffected_service_only_has_decoys() -> None:
    fault = _fault("java-ecom-cart-redis-latency")

    logs = simulate_logs(fault, service="payment-service", now=NOW, limit=50)

    notable = cast(list[dict[str, Any]], cast(dict[str, object], logs["summary"])["notableEvents"])
    assert {item["event"] for item in notable} <= {"deployment_completed", "gc_pause"}
