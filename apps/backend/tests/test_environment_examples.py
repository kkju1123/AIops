import json
from pathlib import Path

from super_ai.cloudwatch_config import AWS_CLOUDWATCH_MCP_PACKAGE, load_aws_cloudwatch_settings
from super_ai.project_config import load_project_config

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_local_project_configs_are_ignored_and_templates_are_sanitized() -> None:
    ignore_patterns = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "config/project.json" in ignore_patterns
    assert "config/user.project.json" in ignore_patterns

    base_template = json.loads(
        (REPO_ROOT / "config/project.template.json").read_text(encoding="utf-8")
    )
    user_template = json.loads(
        (REPO_ROOT / "config/user.project.template.json").read_text(encoding="utf-8")
    )

    assert base_template["llm"]["apiKey"] == ""
    assert base_template["clsMcpServer"]["secretId"] == ""
    assert base_template["clsMcpServer"]["secretKey"] == ""
    assert base_template["prometheusAlerts"]["sources"][0]["password"] == ""
    assert base_template["aiopsDemo"]["password"] == ""
    assert "minio" not in base_template
    assert base_template["vectorStore"]["dsn"].endswith("@127.0.0.1:5432/oncall")
    assert user_template["llm"]["apiKey"] == ""
    assert user_template["clsMcpServer"]["secretId"] == ""
    assert user_template["clsMcpServer"]["secretKey"] == ""
    assert base_template["observability"]["awsCloudWatch"]["profile"] == ""
    assert user_template["observability"]["awsCloudWatch"]["profile"] == ""
    serialized_templates = json.dumps([base_template, user_template]).lower()
    assert "aws_access_key_id" not in serialized_templates
    assert "aws_secret_access_key" not in serialized_templates
    assert "aws_session_token" not in serialized_templates


def test_project_config_contains_development_provider_config() -> None:
    base_config = json.loads(Path("../../config/project.json").read_text(encoding="utf-8"))
    user_config = json.loads(Path("../../config/user.project.json").read_text(encoding="utf-8"))
    merged_config = load_project_config(Path("../../config/project.json"))
    llm = merged_config["llm"]

    assert base_config["llm"]["apiKey"] == ""
    assert base_config["llm"]["chatModel"] == ""
    assert base_config["llm"]["provider"] == "deepseek-openai"
    assert base_config["clsMcpServer"]["secretId"] == ""
    assert base_config["clsMcpServer"]["secretKey"] == ""
    assert base_config["clsLogUpload"]["region"] == ""
    assert base_config["clsLogUpload"]["logsetId"] == ""
    assert base_config["clsLogUpload"]["topicId"] == ""
    assert user_config["llm"]["apiKey"].startswith("sk-")
    assert llm["apiKey"].startswith("sk-")
    assert llm["baseUrl"] == "https://api.deepseek.com"
    assert llm["chatModel"] == "deepseek-flash"
    assert merged_config["retrievalModels"]["embedding"]["model"] == "BAAI/bge-m3"
    assert merged_config["retrievalModels"]["embedding"]["dimensions"] == 1024
    assert merged_config["retrievalModels"]["rerank"]["model"] == (
        "BAAI/bge-reranker-v2-m3"
    )
    assert "modelCapabilities" not in base_config["llm"]
    capabilities = user_config["llm"]["modelCapabilities"]
    assert capabilities["deepseek-flash"]["contextWindowTokens"] == 1_000_000
    assert llm["maxRetries"] == 2
    cloudwatch = load_aws_cloudwatch_settings(config_path=Path("../../config/project.json"))
    assert cloudwatch.region == "eu-west-1"
    assert cloudwatch.log_group_names == ("/super-ai/demo",)
    assert cloudwatch.profile == merged_config["observability"]["awsCloudWatch"]["profile"]
    connection = cloudwatch.mcp_connection()
    assert connection is not None
    assert connection.args == (
        "--with", "boto3[crt]>=1.41.0", AWS_CLOUDWATCH_MCP_PACKAGE,
    )


def test_project_config_declares_real_prometheus_and_alertmanager_sources() -> None:
    config = json.loads(Path("../../config/project.json").read_text(encoding="utf-8"))
    sources = config["prometheusAlerts"]["sources"]

    assert sources[0]["type"] == "prometheus-v1"
    assert sources[0]["alertsApi"] == "" or (
        sources[0]["alertsApi"].startswith("https://")
        and sources[0]["alertsApi"].endswith("/api/v1/alerts")
    )
    assert sources[1]["type"] == "alertmanager-v2"
    assert sources[1]["alertsApi"] == "http://127.0.0.1:9093/api/v2/alerts"
