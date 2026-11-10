"""Validated project configuration for AWS CloudWatch observability."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from super_ai.mcp_client import McpServerConnection
from super_ai.project_config import (
    ProjectConfigurationError,
    project_config_section,
    required_int,
    required_str,
)

AWS_CLOUDWATCH_MCP_PACKAGE = "awslabs.cloudwatch-mcp-server@0.3.1"


@dataclass(frozen=True, slots=True)
class AwsCloudWatchSettings:
    enabled: bool
    region: str
    profile: str
    log_group_names: tuple[str, ...]
    timeout_seconds: int
    retries: int

    def mcp_connection(self) -> McpServerConnection | None:
        if not self.enabled:
            return None
        environment = [
            ("AWS_REGION", self.region),
            ("AWS_DEFAULT_REGION", self.region),
            ("FASTMCP_LOG_LEVEL", "ERROR"),
        ]
        if self.profile:
            environment.append(("AWS_PROFILE", self.profile))
        return McpServerConnection(
            name="aws-cloudwatch",
            transport="stdio",
            timeout_seconds=self.timeout_seconds,
            retries=self.retries,
            command="uvx",
            args=("--with", "boto3[crt]>=1.41.0", AWS_CLOUDWATCH_MCP_PACKAGE),
            environment=tuple(environment),
            provider="aws-cloudwatch",
        )


def load_aws_cloudwatch_settings(
    *, config_path: Path | str | None = None
) -> AwsCloudWatchSettings:
    observability = project_config_section("observability", config_path=config_path)
    provider = required_str(observability, "provider")
    if provider != "aws-cloudwatch":
        raise ProjectConfigurationError("Unsupported observability provider.")
    raw_settings = observability.get("awsCloudWatch")
    if not isinstance(raw_settings, dict):
        raise ProjectConfigurationError("awsCloudWatch configuration must be an object.")
    settings = cast(Mapping[str, Any], raw_settings)
    enabled = settings.get("enabled")
    profile = settings.get("profile")
    raw_log_groups = settings.get("logGroupNames")
    if not isinstance(enabled, bool):
        raise ProjectConfigurationError("awsCloudWatch.enabled must be a boolean.")
    if not isinstance(profile, str):
        raise ProjectConfigurationError("awsCloudWatch.profile must be a string.")
    log_groups = _non_empty_strings(raw_log_groups, field="logGroupNames")
    timeout_seconds = required_int(settings, "timeoutSeconds")
    retries = required_int(settings, "retries")
    if not 1 <= timeout_seconds <= 300 or not 0 <= retries <= 5:
        raise ProjectConfigurationError("CloudWatch MCP timeout or retries are invalid.")
    return AwsCloudWatchSettings(
        enabled=enabled,
        region=required_str(settings, "region"),
        profile=profile.strip(),
        log_group_names=log_groups,
        timeout_seconds=timeout_seconds,
        retries=retries,
    )


def _non_empty_strings(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str | bytes):
        raise ProjectConfigurationError(f"{field} must be an array of strings.")
    items = cast(Sequence[object], value)
    normalized = tuple(item.strip() for item in items if isinstance(item, str) and item.strip())
    if len(normalized) != len(items) or not normalized:
        raise ProjectConfigurationError(f"{field} must contain non-empty strings.")
    return normalized
