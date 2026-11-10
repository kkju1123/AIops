"""Grading and aggregation for offline drill diagnosis evaluation.

The evaluation runs real diagnoses against the fault simulator and asks an LLM judge
to compare each report with the scenario's ground-truth root cause, which is never
shown to the diagnosis itself.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from typing import Literal, cast

from super_ai.llm.provider import ChatModel

Verdict = Literal["correct", "partial", "incorrect"]
VERDICT_SCORES: dict[Verdict, float] = {"correct": 1.0, "partial": 0.5, "incorrect": 0.0}
MAX_REPORT_CHARS = 8_000
MAX_RAW_JUDGE_CHARS = 500


@dataclass(frozen=True, slots=True)
class JudgeResult:
    verdict: Verdict
    reason: str
    raw: str = ""

    @property
    def score(self) -> float:
        return VERDICT_SCORES[self.verdict]


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    """One graded diagnosis; serialised as one JSONL line."""

    scenario_id: str
    attempt: int
    diagnostic_id: str
    status: str
    verdict: Verdict
    score: float
    judge_reason: str
    expected_document: str
    retrieved_documents: tuple[str, ...]
    retrieval_hit: bool
    tool_calls: int
    evidence_count: int
    duration_seconds: float
    report_chars: int
    judge_raw: str = ""

    def to_json(self) -> str:
        payload = asdict(self)
        payload["retrieved_documents"] = list(self.retrieved_documents)
        return json.dumps(payload, ensure_ascii=False)


@dataclass(frozen=True, slots=True)
class ObservedDiagnosis:
    """Facts extracted from a diagnosis event stream."""

    report: str
    retrieved_documents: tuple[str, ...]
    tool_calls: int
    errors: tuple[str, ...] = field(default_factory=tuple)


def observe_events(events: Sequence[Mapping[str, object]]) -> ObservedDiagnosis:
    """Collect the report, retrieved documents, and completed tool calls from SSE payloads."""
    report = ""
    documents: list[str] = []
    tool_ids: set[str] = set()
    errors: list[str] = []
    for event in events:
        kind = event.get("type")
        if kind == "report":
            payload = _mapping(event.get("report"))
            content = payload.get("content")
            if isinstance(content, str):
                report = content
        elif kind == "reference.source":
            reference = _mapping(event.get("reference"))
            if reference.get("sourceType") != "knowledge-base":
                continue
            name = _document_name(reference)
            if name and name not in documents:
                documents.append(name)
        elif kind == "tool.call":
            call = _mapping(event.get("toolCall"))
            if call.get("status") in ("completed", "failed") and call.get("name") not in (
                "knowledge_retrieval",
            ):
                tool_ids.add(str(call.get("id")))
        elif kind == "error":
            error = _mapping(event.get("error"))
            errors.append(str(error.get("code") or "error"))
    return ObservedDiagnosis(
        report=report,
        retrieved_documents=tuple(documents),
        tool_calls=len(tool_ids),
        errors=tuple(errors),
    )


def judge_prompt(*, symptom: str, ground_truth: str, report: str) -> str:
    return f"""你是严格的 AIOps 根因评审。请判断“诊断报告”的根因结论是否与“标准根因”一致。

评分标准：
- correct：报告明确给出的根因与标准根因的核心机制一致
  （同一个故障组件和同一种故障机制），表述可以不同。
- partial：报告定位到了正确的组件或故障类别，但根因机制缺失、过于笼统，
  或把正确根因与其他根因并列而没有选定。
- incorrect：根因错误、只复述症状、写“证据不足”或没有根因结论。

只输出 JSON，不要输出其他内容：{{"verdict": "correct|partial|incorrect", "reason": "一句中文理由"}}

告警症状：{symptom}
标准根因：{ground_truth}

诊断报告：
{report[:MAX_REPORT_CHARS]}
"""


def parse_judge_output(text: str) -> JudgeResult:
    """Parse the judge's JSON; anything unparseable counts as incorrect."""
    raw = text.strip()[:MAX_RAW_JUDGE_CHARS]
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match is None:
        return JudgeResult("incorrect", "评审输出无法解析。", raw)
    try:
        decoded: object = json.loads(match.group(0))
    except json.JSONDecodeError:
        return JudgeResult("incorrect", "评审输出无法解析。", raw)
    payload = _mapping(decoded)
    verdict = payload.get("verdict")
    if verdict not in VERDICT_SCORES:
        return JudgeResult("incorrect", "评审输出缺少有效结论。", raw)
    reason = payload.get("reason")
    return JudgeResult(
        verdict, reason if isinstance(reason, str) else "", raw
    )


async def judge_report(
    model: ChatModel, *, symptom: str, ground_truth: str, report: str
) -> JudgeResult:
    if not report.strip():
        return JudgeResult("incorrect", "诊断没有生成报告。")
    response = await model.ainvoke(
        judge_prompt(symptom=symptom, ground_truth=ground_truth, report=report)
    )
    return parse_judge_output(_text(response))


@dataclass(frozen=True, slots=True)
class ScenarioSummary:
    scenario_id: str
    runs: int
    accuracy: float
    correct: int
    partial: int
    incorrect: int
    retrieval_hit_rate: float
    mean_tool_calls: float
    mean_duration_seconds: float


def summarize(runs: Sequence[EvaluationRun]) -> list[ScenarioSummary]:
    grouped: dict[str, list[EvaluationRun]] = {}
    for run in runs:
        grouped.setdefault(run.scenario_id, []).append(run)
    return [_summary(scenario_id, items) for scenario_id, items in grouped.items()]


def overall(runs: Sequence[EvaluationRun]) -> ScenarioSummary:
    return _summary("全部场景", list(runs))


def render_markdown(
    runs: Sequence[EvaluationRun], *, title: str, notes: Sequence[str] = ()
) -> str:
    lines = [f"# {title}", ""]
    lines.extend(f"- {note}" for note in notes)
    if notes:
        lines.append("")
    header = (
        "| 场景 | 次数 | 根因得分 | 正确 / 部分 / 错误 | 手册命中率 | 平均工具调用 | 平均耗时 (s) |"
    )
    lines.extend([header, "|---|---|---|---|---|---|---|"])
    for item in [*summarize(runs), overall(runs)]:
        name = f"**{item.scenario_id}**" if item.scenario_id == "全部场景" else item.scenario_id
        lines.append(
            f"| {name} | {item.runs} | {item.accuracy:.0%} | "
            f"{item.correct} / {item.partial} / {item.incorrect} | "
            f"{item.retrieval_hit_rate:.0%} | {item.mean_tool_calls:.1f} | "
            f"{item.mean_duration_seconds:.1f} |"
        )
    lines.extend(["", "## 评审理由", ""])
    for run in runs:
        lines.append(f"- `{run.scenario_id}` #{run.attempt} {run.verdict}：{run.judge_reason}")
    return "\n".join(lines) + "\n"


def _summary(scenario_id: str, runs: Sequence[EvaluationRun]) -> ScenarioSummary:
    count = len(runs)
    if count == 0:
        return ScenarioSummary(scenario_id, 0, 0.0, 0, 0, 0, 0.0, 0.0, 0.0)
    return ScenarioSummary(
        scenario_id=scenario_id,
        runs=count,
        accuracy=sum(run.score for run in runs) / count,
        correct=sum(run.verdict == "correct" for run in runs),
        partial=sum(run.verdict == "partial" for run in runs),
        incorrect=sum(run.verdict == "incorrect" for run in runs),
        retrieval_hit_rate=sum(run.retrieval_hit for run in runs) / count,
        mean_tool_calls=sum(run.tool_calls for run in runs) / count,
        mean_duration_seconds=sum(run.duration_seconds for run in runs) / count,
    )


def _document_name(reference: Mapping[str, object]) -> str:
    for value in (reference.get("title"), reference.get("source")):
        if isinstance(value, str) and value:
            return value
    return ""


def _mapping(value: object) -> Mapping[str, object]:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else {}


def _text(response: object) -> str:
    content = getattr(response, "content", response)
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            str(cast(Mapping[str, object], item).get("text", ""))
            if isinstance(item, Mapping)
            else str(item)
            for item in cast(list[object], content)
        )
    return str(content)
