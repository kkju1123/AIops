"""Build an MCP client bound to one drill run's injected fault."""

from __future__ import annotations

import sys

from super_ai.mcp_client import LocalMcpClient, McpServerConnection
from super_ai.simulator.faults import SIMULATED_FAULT_ENV, SimulatedFault

SIMULATOR_CONNECTION_NAME = "fault-simulator"


def simulator_connection(fault: SimulatedFault) -> McpServerConnection:
    """A stdio connection that starts the simulator with this run's fault only."""
    return McpServerConnection(
        name=SIMULATOR_CONNECTION_NAME,
        transport="stdio",
        command=sys.executable,
        args=("-m", "super_ai.simulator.server"),
        environment=((SIMULATED_FAULT_ENV, fault.to_env_value()),),
        provider="simulator",
        timeout_seconds=15,
        retries=0,
    )


def build_simulator_client(fault: SimulatedFault) -> LocalMcpClient:
    return LocalMcpClient(connections=[simulator_connection(fault)])
