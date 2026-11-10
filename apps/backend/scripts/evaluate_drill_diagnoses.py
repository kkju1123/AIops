"""Run real drill diagnoses against the fault simulator and grade them against ground truth.

Explicit developer command; it never runs on application start. Each run uses the
configured DeepSeek model, the live drill service account's knowledge base and a fresh
fault simulator process. No alert is published and no job worker is started.

    uv run python scripts/evaluate_drill_diagnoses.py --repeats 3
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from uuid import uuid4

from super_ai.aiops.fixtures import expected_knowledge_document
from super_ai.api.app import OfflineDiagnosisRuntime, create_app, offline_diagnosis_runtime
from super_ai.evaluation.drill import (
    EvaluationRun,
    JudgeResult,
    judge_report,
    observe_events,
    overall,
    render_markdown,
)
from super_ai.live_demo import LiveDemoScenario, diagnostic_alert_input, enabled_scenarios
from super_ai.llm.provider import ChatModel
from super_ai.simulator import SimulatedFault

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3, help="runs per scenario")
    parser.add_argument(
        "--scenario", action="append", default=[], help="limit to scenario id (repeatable)"
    )
    parser.add_argument("--label", default="drill", help="label used in the output folder")
    parser.add_argument("--output-dir", type=Path, default=BACKEND_ROOT / "var" / "evaluations")
    args = parser.parse_args()
    if args.repeats < 1:
        raise SystemExit("--repeats must be at least 1.")
    asyncio.run(
        _evaluate(
            repeats=args.repeats,
            scenario_ids=tuple(args.scenario),
            label=args.label,
            output_root=args.output_dir,
        )
    )


async def _evaluate(
    *, repeats: int, scenario_ids: tuple[str, ...], label: str, output_root: Path
) -> None:
    runtime = offline_diagnosis_runtime(create_app())
    account = await runtime.live_demo.service_account()
    if account is None:
        raise SystemExit("The live drill service account does not exist; seed it first.")
    scenarios = [
        scenario
        for scenario in enabled_scenarios(runtime.live_demo.settings)
        if not scenario_ids or scenario.id in scenario_ids
    ]
    if not scenarios:
        raise SystemExit("No matching enabled drill scenarios.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = output_root / f"{stamp}-{label}"
    output_dir.mkdir(parents=True, exist_ok=True)
    results_path = output_dir / "results.jsonl"
    judge_model = runtime.llm_provider.create_chat_model(thinking=False)
    runs: list[EvaluationRun] = []
    total = len(scenarios) * repeats
    for scenario in scenarios:
        for attempt in range(1, repeats + 1):
            run = await _run_once(
                runtime=runtime,
                owner_user_id=account.id,
                scenario=scenario,
                attempt=attempt,
                judge_model=judge_model,
            )
            runs.append(run)
            with results_path.open("a", encoding="utf-8") as handle:
                handle.write(run.to_json() + "\n")
            print(
                f"[{len(runs)}/{total}] {scenario.id} #{attempt}: {run.verdict} "
                f"(hit={run.retrieval_hit}, tools={run.tool_calls}, "
                f"{run.duration_seconds:.0f}s)",
                flush=True,
            )
    summary = overall(runs)
    notes = [
        f"运行时间：{stamp}（UTC），每个场景 {repeats} 次，共 {len(runs)} 次诊断。",
        "评审：同一 DeepSeek 配置（关闭深度思考），对照 fixture 标准根因给出 correct / partial / "
        "incorrect，分别计 1 / 0.5 / 0 分；诊断失败或无报告计为 incorrect。",
        "手册命中：检索返回的知识文档中是否包含该场景期望的文档。",
    ]
    (output_dir / "summary.md").write_text(
        render_markdown(runs, title=f"演练诊断评测：{label}", notes=notes), encoding="utf-8"
    )
    print(
        f"\n根因得分 {summary.accuracy:.0%}，手册命中率 {summary.retrieval_hit_rate:.0%}，"
        f"平均耗时 {summary.mean_duration_seconds:.1f}s。结果：{output_dir}"
    )


async def _run_once(
    *,
    runtime: OfflineDiagnosisRuntime,
    owner_user_id: str,
    scenario: LiveDemoScenario,
    attempt: int,
    judge_model: ChatModel,
) -> EvaluationRun:
    run_id = f"eval_run_{uuid4().hex}"
    now = datetime.now(timezone.utc)
    query = scenario.diagnostic_query(simulated=True)
    input_payload: dict[str, object] = {
        "query": query,
        "alert": diagnostic_alert_input(scenario, run_id=run_id, now=now),
        "liveDemo": True,
        "evaluation": {"runId": run_id, "scenarioId": scenario.id, "attempt": attempt},
        "simulatedFault": SimulatedFault(
            run_id=run_id, scenario_id=scenario.id, injected_at=now
        ).payload(),
    }
    diagnostics = runtime.repositories.diagnostics
    task = await diagnostics.create_task(
        owner_user_id=owner_user_id,
        task_id=f"diagnostic_{uuid4().hex}",
        status="accepted",
        query=query,
        input_payload=input_payload,
        result_payload={},
    )
    started = monotonic()
    events = [
        event
        async for event in runtime.runner.stream(
            task=task, accessible_knowledge_base_ids=(f"kb_{owner_user_id}",)
        )
    ]
    duration = monotonic() - started
    observed = observe_events(events)
    final = await diagnostics.get_task(owner_user_id=owner_user_id, task_id=task.id)
    status = final.status if final is not None else "missing"
    evidence = await diagnostics.list_evidence(owner_user_id=owner_user_id, task_id=task.id)
    report = observed.report if status == "succeeded" else ""
    try:
        judged = await judge_report(
            judge_model,
            symptom=scenario.symptom,
            ground_truth=scenario.incident.root_cause,
            report=report,
        )
    except Exception as exc:  # noqa: BLE001 - a judge outage must not abort the whole run
        judged = JudgeResult("incorrect", f"评审调用失败：{exc.__class__.__name__}")
    expected = expected_knowledge_document(scenario.incident)
    return EvaluationRun(
        scenario_id=scenario.id,
        attempt=attempt,
        diagnostic_id=task.id,
        status=status,
        verdict=judged.verdict,
        score=judged.score,
        judge_reason=judged.reason,
        expected_document=expected,
        retrieved_documents=observed.retrieved_documents,
        retrieval_hit=expected in observed.retrieved_documents,
        tool_calls=observed.tool_calls,
        evidence_count=len(evidence),
        duration_seconds=round(duration, 1),
        report_chars=len(observed.report),
        judge_raw=judged.raw,
    )


if __name__ == "__main__":
    main()
