"""Fault simulator MCP server (stdio) for the public live drill.

The parent backend starts one process per drill run and injects the fault through the
`SUPER_AI_SIMULATED_FAULT` variable. This is per-process IPC, not project configuration.
"""

from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from super_ai.simulator.faults import (
    LOG_TOOL,
    METRIC_TOOL,
    SIMULATED_FAULT_ENV,
    SimulatedFault,
    simulate_logs,
    simulate_metrics,
    simulated_fault_from_env_value,
)


def build_simulator_server(fault: SimulatedFault) -> FastMCP:
    """Create an MCP server whose tools answer from the injected fault."""
    server = FastMCP(
        "fault-simulator",
        instructions=(
            "Synthetic observability for a public incident drill. Every record is labelled "
            "simulated=true."
        ),
    )

    @server.tool(
        name=LOG_TOOL,
        description=(
            "Query a service's recent application logs (synthetic drill data). Times are "
            "ISO-8601; the window defaults to the last 30 minutes. Returns the newest records "
            "and a summary of all matches."
        ),
    )
    def query_service_logs(  # pyright: ignore[reportUnusedFunction]
        service: str,
        start_time: str | None = None,
        end_time: str | None = None,
        limit: int = 20,
    ) -> dict[str, object]:
        return simulate_logs(
            fault, service=service, start_time=start_time, end_time=end_time, limit=limit
        )

    @server.tool(
        name=METRIC_TOOL,
        description=(
            "Query per-minute metric series for a service (synthetic drill data). Omit "
            "metric_names to get the service's key metric, error rate and p95 latency."
        ),
    )
    def query_service_metrics(  # pyright: ignore[reportUnusedFunction]
        service: str,
        metric_names: list[str] | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict[str, object]:
        return simulate_metrics(
            fault,
            service=service,
            metric_names=metric_names,
            start_time=start_time,
            end_time=end_time,
        )

    return server


def main() -> None:
    fault = simulated_fault_from_env_value(os.environ.get(SIMULATED_FAULT_ENV))
    build_simulator_server(fault).run("stdio")


if __name__ == "__main__":
    main()
