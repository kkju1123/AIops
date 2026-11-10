from __future__ import annotations

import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import pytest

from super_ai.cloudwatch_config import AwsCloudWatchSettings
from super_ai.mcp_client import (
    LocalMcpClient,
    McpServerConnection,
    langchain_connection_config,
)


@dataclass(frozen=True, slots=True)
class FakeMcpContent:
    type: str
    text: str


def test_cloudwatch_login_profile_has_required_crt_dependency() -> None:
    settings = AwsCloudWatchSettings(
        enabled=True, region="eu-west-1", profile="demo",
        log_group_names=("/super-ai/demo",), timeout_seconds=60, retries=0,
    )
    connection = settings.mcp_connection()
    assert connection is not None
    assert connection.args == (
        "--with", "boto3[crt]>=1.41.0", "awslabs.cloudwatch-mcp-server@0.3.1",
    )
    assert dict(connection.environment)["AWS_PROFILE"] == "demo"
    assert dict(connection.environment)["AWS_DEFAULT_REGION"] == "eu-west-1"


@dataclass(frozen=True, slots=True)
class FakeMcpResult:
    isError: bool
    content: list[FakeMcpContent]


class FakeLocalMcpClient(LocalMcpClient):
    async def _run(self, operation: Callable[[Any], Awaitable[Any]]) -> Any:
        del operation
        return FakeMcpResult(
            isError=False,
            content=[FakeMcpContent(type="text", text="mcp-output-secret")],
        )


@pytest.mark.asyncio
async def test_mcp_tool_logs_lifecycle_without_argument_values_or_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    logging.getLogger("super_ai.mcp_client").disabled = False
    caplog.set_level(logging.INFO, logger="super_ai.mcp_client")
    client = FakeLocalMcpClient("http://mcp.test/sse")

    result = await client.call_tool(
        "SearchLog",
        {"query": "query-secret", "topicId": "topic-secret"},
    )

    assert result == [{"type": "text", "text": "mcp-output-secret"}]
    events = [
        json.loads(record.message) for record in caplog.records if record.message.startswith("{")
    ]
    assert [event["event"] for event in events] == [
        "mcp.tool.started",
        "mcp.tool.completed",
    ]
    assert events[0]["argumentKeys"] == ["query", "topicId"]
    emitted = "\n".join(record.message for record in caplog.records)
    assert "query-secret" not in emitted
    assert "topic-secret" not in emitted
    assert "mcp-output-secret" not in emitted


def test_stdio_connection_uses_only_explicit_project_environment() -> None:
    connection = McpServerConnection(
        name="aws-cloudwatch",
        transport="stdio",
        command="uvx",
        args=("awslabs.cloudwatch-mcp-server@0.3.1",),
        environment=(("AWS_REGION", "eu-west-1"), ("FASTMCP_LOG_LEVEL", "ERROR")),
        provider="aws-cloudwatch",
    )

    payload = langchain_connection_config(connection)

    assert payload == {
        "transport": "stdio",
        "command": "uvx",
        "args": ["awslabs.cloudwatch-mcp-server@0.3.1"],
        "env": {"AWS_REGION": "eu-west-1", "FASTMCP_LOG_LEVEL": "ERROR"},
    }
    assert connection.endpoint_label == "stdio:uvx"
