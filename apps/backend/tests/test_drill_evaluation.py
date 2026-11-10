"""Offline drill evaluation: event observation, judge parsing, and aggregation."""

from __future__ import annotations

import asyncio
import json

from super_ai.evaluation.drill import (
    EvaluationRun,
    judge_report,
    observe_events,
    overall,
    parse_judge_output,
    render_markdown,
    summarize,
)


def _run(scenario: str, verdict: str, score: float, *, hit: bool = True) -> EvaluationRun:
    return EvaluationRun(
        scenario_id=scenario,
        attempt=1,
        diagnostic_id="diagnostic_1",
        status="succeeded",
        verdict=verdict,  # type: ignore[arg-type]
        score=score,
        judge_reason="理由",
        expected_document="runbook.md",
        retrieved_documents=("runbook.md",) if hit else ("other.md",),
        retrieval_hit=hit,
        tool_calls=2,
        evidence_count=3,
        duration_seconds=30.0,
        report_chars=100,
    )


def test_observe_events_collects_report_documents_and_tool_calls() -> None:
    def tool(call_id: str, name: str, status: str) -> dict[str, object]:
        return {"type": "tool.call", "toolCall": {"id": call_id, "name": name, "status": status}}

    def reference(title: str, source_type: str) -> dict[str, object]:
        return {
            "type": "reference.source",
            "reference": {"title": title, "sourceType": source_type},
        }

    events: list[dict[str, object]] = [
        tool("t0", "knowledge_retrieval", "completed"),
        reference("a.md", "knowledge-base"),
        reference("a.md", "knowledge-base"),
        reference("logs result", "log"),
        tool("t1", "query_service_logs", "started"),
        tool("t1", "query_service_logs", "completed"),
        tool("t2", "query_service_metrics", "failed"),
        {"type": "report", "report": {"content": "# 报告"}},
    ]

    observed = observe_events(events)

    assert observed.report == "# 报告"
    assert observed.retrieved_documents == ("a.md",)
    assert observed.tool_calls == 2


def test_parse_judge_output_accepts_fenced_json() -> None:
    result = parse_judge_output('```json\n{"verdict": "partial", "reason": "组件对"}\n```')

    assert result.verdict == "partial"
    assert result.score == 0.5
    assert result.reason == "组件对"


def test_parse_judge_output_treats_garbage_as_incorrect() -> None:
    assert parse_judge_output("I think it is right").verdict == "incorrect"
    assert parse_judge_output('{"verdict": "maybe"}').verdict == "incorrect"
    garbled = parse_judge_output("{not json}")
    assert garbled.verdict == "incorrect"
    assert garbled.raw == "{not json}"


def test_missing_report_is_incorrect_without_calling_the_judge() -> None:
    class ExplodingModel:
        async def ainvoke(self, input: object) -> object:
            raise AssertionError("judge must not be called")

    result = asyncio.run(
        judge_report(ExplodingModel(), symptom="s", ground_truth="g", report="  ")
    )

    assert result.verdict == "incorrect"


def test_judge_prompt_contains_ground_truth_and_report() -> None:
    seen: list[str] = []

    class RecordingModel:
        async def ainvoke(self, input: object) -> object:
            seen.append(str(input))
            return json.dumps({"verdict": "correct", "reason": "一致"})

    result = asyncio.run(
        judge_report(RecordingModel(), symptom="超时", ground_truth="TLS 握手慢", report="报告正文")
    )

    assert result.verdict == "correct"
    assert "TLS 握手慢" in seen[0] and "报告正文" in seen[0]


def test_summaries_and_markdown() -> None:
    runs = [
        _run("a", "correct", 1.0),
        _run("a", "incorrect", 0.0, hit=False),
        _run("b", "partial", 0.5),
    ]

    by_scenario = {item.scenario_id: item for item in summarize(runs)}
    total = overall(runs)

    assert by_scenario["a"].accuracy == 0.5
    assert by_scenario["a"].retrieval_hit_rate == 0.5
    assert total.accuracy == 0.5
    assert (total.correct, total.partial, total.incorrect) == (1, 1, 1)
    markdown = render_markdown(runs, title="评测", notes=["说明"])
    assert "| **全部场景** | 3 | 50% | 1 / 1 / 1 | 67% |" in markdown
    assert "- 说明" in markdown


def test_run_serialises_to_json_line() -> None:
    line = _run("a", "correct", 1.0).to_json()

    assert json.loads(line)["retrieved_documents"] == ["runbook.md"]
