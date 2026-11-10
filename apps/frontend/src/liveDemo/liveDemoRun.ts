import type {
  ActiveAlert,
  CreateLiveDemoRunResponse,
  LiveDemoObservability,
  SseEvent
} from "@agent-py/api-contracts";

export type LiveStageId = "alert" | "sop" | "plan" | "execute" | "report";
export type LiveStageStatus = "pending" | "active" | "done" | "failed";
export type LiveRunPhase = "idle" | "starting" | "running" | "succeeded" | "failed";

export interface LiveStage {
  readonly id: LiveStageId;
  readonly title: string;
  readonly caption: string;
  readonly status: LiveStageStatus;
  readonly details: readonly string[];
}

export interface LiveLogQuery {
  readonly tool: string;
  readonly status: "started" | "completed" | "failed";
  readonly logGroups: readonly string[];
  readonly region: string | null;
  readonly rows: readonly Readonly<Record<string, string>>[];
  readonly summary: LiveLogSummary | null;
  readonly error: string | null;
}

export interface LiveLogSummary {
  readonly totalMatched: number;
  readonly errorCount: number;
  readonly firstErrorAt: string | null;
}

export interface LiveMetric {
  readonly name: string;
  readonly unit: string;
  readonly baseline: number;
  readonly latest: number;
  readonly max: number;
  readonly threshold: string | null;
  readonly values: readonly number[];
}

export interface LiveTimelineEntry {
  readonly at: string;
  readonly message: string;
}

export interface LiveRunState {
  readonly phase: LiveRunPhase;
  readonly runId: string | null;
  /** Diagnosis id readable in the workspace; null for anonymous runs. */
  readonly diagnosticId: string | null;
  readonly observability: LiveDemoObservability;
  readonly alert: ActiveAlert | null;
  readonly alertPublished: boolean;
  readonly stages: readonly LiveStage[];
  readonly sopHits: readonly string[];
  readonly logQuery: LiveLogQuery | null;
  readonly metrics: readonly LiveMetric[];
  readonly report: { readonly title: string; readonly content: string } | null;
  /** Report text streamed so far; cleared once the authoritative `report` event arrives. */
  readonly draftReport: string;
  readonly draftSequence: number;
  readonly progress: number;
  readonly timeline: readonly LiveTimelineEntry[];
  readonly errorMessage: string | null;
}

const SIMULATOR_METRIC_TOOL = "query_service_metrics";

const EXECUTE_CAPTIONS: Record<LiveDemoObservability, string> = {
  simulator: "通过 MCP 调用故障模拟器，查询日志与指标",
  "aws-cloudwatch": "通过 MCP 调用 AWS CloudWatch 查询真实日志"
};

const STAGE_DEFINITIONS: readonly Pick<LiveStage, "id" | "title" | "caption">[] = [
  { id: "alert", title: "告警触发", caption: "向 Alertmanager 推送一条真实告警" },
  { id: "sop", title: "检索 SOP", caption: "pgvector + BM25 混合召回，BGE 重排" },
  { id: "plan", title: "制定计划", caption: "LangGraph Planner 调用 DeepSeek 生成排查步骤" },
  { id: "execute", title: "执行排查", caption: "通过 MCP 调用 AWS CloudWatch 查询真实日志" },
  { id: "report", title: "生成报告", caption: "Replanner 判断证据充分后输出根因报告" }
];

const KNOWLEDGE_TOOL = "knowledge_retrieval";

export function initialLiveRunState(observability: LiveDemoObservability = "simulator"): LiveRunState {
  return {
    phase: "idle",
    runId: null,
    diagnosticId: null,
    observability,
    alert: null,
    alertPublished: false,
    stages: STAGE_DEFINITIONS.map((stage) => ({
      ...stage,
      caption: stage.id === "execute" ? EXECUTE_CAPTIONS[observability] : stage.caption,
      status: "pending",
      details: []
    })),
    sopHits: [],
    logQuery: null,
    metrics: [],
    report: null,
    draftReport: "",
    draftSequence: 0,
    progress: 0,
    timeline: [],
    errorMessage: null
  };
}

export function startingLiveRunState(): LiveRunState {
  return { ...initialLiveRunState(), phase: "starting" };
}

export function startLiveRun(created: CreateLiveDemoRunResponse, now = new Date()): LiveRunState {
  const state = initialLiveRunState();
  const publishedDetail = created.alertPublished
    ? "已推送到 Alertmanager，并作为诊断输入"
    : "Alertmanager 未连接，告警直接作为诊断输入";
  return {
    ...state,
    phase: "running",
    runId: created.run.id,
    diagnosticId: created.run.diagnosticId ?? null,
    observability: created.observability,
    alert: created.alert,
    alertPublished: created.alertPublished,
    progress: 5,
    stages: updateStages(
      updateStages(state.stages, "alert", "done", [
        `${created.alert.alertName} · ${created.alert.severity}`,
        publishedDetail
      ]),
      "sop",
      "active"
    ).map((stage) =>
      stage.id === "execute" ? { ...stage, caption: EXECUTE_CAPTIONS[created.observability] } : stage
    ),
    timeline: [{ at: now.toISOString(), message: `告警 ${created.alert.alertName} 已触发` }]
  };
}

export function applyLiveRunEvent(state: LiveRunState, event: SseEvent): LiveRunState {
  switch (event.type) {
    case "task.status":
      return applyTaskStatus(state, event.task.status, event.task.message ?? "", event.task.progress, event.timestamp);
    case "tool.call":
      return applyToolCall(state, event.toolCall);
    case "reference.source":
      if (event.reference.sourceType !== "knowledge-base" || state.sopHits.includes(event.reference.title)) {
        return state;
      }
      return { ...state, sopHits: [...state.sopHits, event.reference.title] };
    case "content.delta":
      if (event.channel !== "aiops" || event.sequence <= state.draftSequence || state.report !== null) {
        return state;
      }
      return { ...state, draftReport: state.draftReport + event.delta, draftSequence: event.sequence };
    case "report":
      return {
        ...state,
        report: { title: event.report.title, content: event.report.content },
        draftReport: "",
        stages: updateStages(state.stages, "report", "done", ["报告已生成"])
      };
    case "complete":
      return state.phase === "failed" ? state : { ...state, phase: "succeeded", progress: 100 };
    case "error":
      return failRun(state, event.error.message);
    default:
      return state;
  }
}

/** Strip an opening Markdown code fence the model may wrap around a streamed report. */
export function draftReportMarkdown(draft: string): string {
  return draft.replace(/^\s*```(?:markdown|md)?[ \t]*\n?/u, "").replace(/\n?```\s*$/u, "");
}

export function describeStatusMessage(message: string): string {
  const planMatch = /^Planner: created a (.+) plan with (\d+) step/u.exec(message);
  if (planMatch !== null) {
    const origin = planMatch[1] === "SOP-backed" ? "基于 SOP" : "通用";
    return `Planner：生成 ${planMatch[2] ?? "?"} 步排查计划（${origin}）`;
  }
  const stepMatch = /^Executor: running step (\d+) with (.+)\.$/u.exec(message);
  if (stepMatch !== null) {
    return `Executor：执行第 ${stepMatch[1] ?? "?"} 步，调用 ${stepMatch[2] ?? "工具"}`;
  }
  const translations: readonly (readonly [string, string])[] = [
    ["Planner: retrieving SOP evidence", "Planner：检索 SOP 知识库"],
    ["Planner: no SOP matched", "Planner：未匹配到 SOP，改用通用排查计划"],
    ["Planner: MCP discovery was unavailable", "Planner：MCP 工具发现失败，将如实报告"],
    ["Planner: discovering MCP tools", "Planner：发现可用的 MCP 工具"],
    ["Planner: drafting a bounded plan", "Planner：DeepSeek 正在制定排查计划"],
    ["Replanner: continuing", "Replanner：继续执行下一步"],
    ["Replanner: moving to Report", "Replanner：证据已收集，进入报告阶段"],
    ["Report: compiling", "Report：基于证据撰写诊断报告"],
    ["Report: diagnostic finished", "诊断完成"]
  ];
  const match = translations.find(([prefix]) => message.startsWith(prefix));
  return match === undefined ? message : match[1];
}

export function extractLogRows(output: unknown, limit = 6): Readonly<Record<string, string>>[] {
  const rows: Record<string, string>[] = [];
  const visit = (value: unknown, depth: number): void => {
    if (rows.length >= limit || depth > 8) {
      return;
    }
    if (typeof value === "string") {
      const trimmed = value.trim();
      if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
        try {
          visit(JSON.parse(trimmed) as unknown, depth + 1);
        } catch {
          return;
        }
      }
      return;
    }
    if (Array.isArray(value)) {
      if (value.length > 0 && value.every(isFlatLogRecord)) {
        for (const item of value) {
          if (rows.length >= limit) {
            return;
          }
          rows.push(flatLogRecord(item));
        }
        return;
      }
      if (value.length > 0 && value.every(isFieldRow)) {
        for (const row of value) {
          if (rows.length >= limit) {
            return;
          }
          rows.push(fieldRowToRecord(row));
        }
        return;
      }
      for (const item of value) {
        visit(item, depth + 1);
      }
      return;
    }
    if (value !== null && typeof value === "object") {
      for (const item of Object.values(value)) {
        visit(item, depth + 1);
      }
    }
  };
  visit(output, 0);
  return rows;
}

function applyTaskStatus(
  state: LiveRunState,
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled",
  message: string,
  progress: number | undefined,
  timestamp: string
): LiveRunState {
  let next: LiveRunState = {
    ...state,
    progress: progress ?? state.progress,
    timeline: message.length > 0
      ? [...state.timeline, { at: timestamp, message: describeStatusMessage(message) }]
      : state.timeline
  };
  if (message.startsWith("Planner: no SOP matched")) {
    next = { ...next, stages: updateStages(next.stages, "sop", "done", ["未匹配到 SOP，改用通用计划"]) };
  }
  const planMatch = /^Planner: created a (.+) plan with (\d+) step/u.exec(message);
  if (planMatch !== null) {
    const origin = planMatch[1] === "SOP-backed" ? "基于 SOP" : "通用";
    next = {
      ...next,
      stages: updateStages(
        updateStages(next.stages, "plan", "done", [`${planMatch[2] ?? "?"} 步排查计划（${origin}）`]),
        "execute",
        "active"
      )
    };
  } else if (message.startsWith("Planner: discovering MCP tools")) {
    next = { ...next, stages: updateStages(next.stages, "plan", "active", ["发现可用的 MCP 工具…"]) };
  } else if (message.startsWith("Planner: drafting")) {
    next = { ...next, stages: updateStages(next.stages, "plan", "active", ["DeepSeek 正在制定排查计划…"]) };
  } else if (message.startsWith("Planner: retrieving")) {
    next = { ...next, stages: updateStages(next.stages, "sop", "active") };
  }
  if (message.startsWith("Replanner: moving to Report")) {
    const executeStages = stageStatus(next, "execute") === "active"
      ? updateStages(next.stages, "execute", "done")
      : next.stages;
    next = { ...next, stages: updateStages(executeStages, "report", "active") };
  }
  if (status === "succeeded") {
    return { ...next, phase: "succeeded", progress: 100 };
  }
  if (status === "failed" || status === "cancelled") {
    return failRun(next, "诊断未能完成。");
  }
  return next;
}

function applyToolCall(
  state: LiveRunState,
  toolCall: { readonly name: string; readonly status: string; readonly input?: unknown; readonly output?: unknown }
): LiveRunState {
  const isSop = toolCall.name === KNOWLEDGE_TOOL && stageStatus(state, "sop") !== "done";
  if (isSop) {
    if (toolCall.status === "completed") {
      const count = countResults(toolCall.output);
      return {
        ...state,
        stages: updateStages(
          updateStages(state.stages, "sop", "done", [count > 0 ? `命中 ${count} 篇 SOP` : "未命中 SOP"]),
          "plan",
          "active"
        )
      };
    }
    if (toolCall.status === "failed") {
      return {
        ...state,
        stages: updateStages(
          updateStages(state.stages, "sop", "failed", ["知识检索暂不可用"]),
          "plan",
          "active"
        )
      };
    }
    return { ...state, stages: updateStages(state.stages, "sop", "active") };
  }

  const input = asRecord(toolCall.input);
  const executeDetails = stageDetails(state, "execute");
  if (toolCall.status === "started") {
    const details = [...executeDetails, `调用 ${toolCall.name}`];
    if (toolCall.name === SIMULATOR_METRIC_TOOL) {
      return { ...state, stages: updateStages(state.stages, "execute", "active", details) };
    }
    return {
      ...state,
      logQuery: {
        tool: toolCall.name,
        status: "started",
        logGroups: stringList(input?.["log_group_names"]),
        region: firstString(input?.["regions"]),
        rows: [],
        summary: null,
        error: null
      },
      stages: updateStages(state.stages, "execute", "active", details)
    };
  }
  if (toolCall.status === "completed" && toolCall.name === SIMULATOR_METRIC_TOOL) {
    const metrics = extractMetrics(toolCall.output);
    const breached = metrics.filter((metric) => metric.max >= metric.baseline * 3 && metric.max > 0).length;
    return {
      ...state,
      metrics,
      stages: updateStages(state.stages, "execute", "active", [
        ...executeDetails,
        `取回 ${metrics.length} 项指标，其中 ${breached} 项明显偏离基线`
      ])
    };
  }
  const previous = state.logQuery ?? {
    tool: toolCall.name,
    status: "started" as const,
    logGroups: [],
    region: null,
    rows: [],
    summary: null,
    error: null
  };
  if (toolCall.status === "completed") {
    const rows = extractLogRows(toolCall.output);
    const summary = extractLogSummary(toolCall.output);
    const counted = summary === null
      ? (rows.length > 0 ? `取回 ${rows.length} 条日志` : "查询完成，未返回日志记录")
      : `匹配 ${summary.totalMatched} 条日志，其中 ERROR ${summary.errorCount} 条`;
    return {
      ...state,
      logQuery: { ...previous, status: "completed", rows, summary },
      stages: updateStages(state.stages, "execute", "active", [...executeDetails, counted])
    };
  }
  if (toolCall.status === "failed") {
    const output = asRecord(toolCall.output);
    const error = typeof output?.["error"] === "string" ? output["error"] : "工具调用失败";
    return {
      ...state,
      logQuery: toolCall.name === SIMULATOR_METRIC_TOOL ? state.logQuery : { ...previous, status: "failed", error },
      stages: updateStages(state.stages, "execute", "failed", [...executeDetails, `调用 ${toolCall.name} 失败`])
    };
  }
  return state;
}

/** Decode MCP text content (`[{ type: "text", text: "{...}" }]`) into its JSON payload. */
export function decodeToolOutput(output: unknown): unknown {
  if (Array.isArray(output) && output.length === 1) {
    const text = asRecord(output[0])?.["text"];
    if (typeof text === "string") {
      try {
        return JSON.parse(text) as unknown;
      } catch {
        return text;
      }
    }
  }
  return output;
}

export function extractLogSummary(output: unknown): LiveLogSummary | null {
  const summary = asRecord(asRecord(decodeToolOutput(output))?.["summary"]);
  if (summary === null || typeof summary["totalMatched"] !== "number" || typeof summary["errorCount"] !== "number") {
    return null;
  }
  return {
    totalMatched: summary["totalMatched"],
    errorCount: summary["errorCount"],
    firstErrorAt: typeof summary["firstErrorAt"] === "string" ? summary["firstErrorAt"] : null
  };
}

export function extractMetrics(output: unknown): LiveMetric[] {
  const metrics = asRecord(decodeToolOutput(output))?.["metrics"];
  if (!Array.isArray(metrics)) {
    return [];
  }
  const parsed: LiveMetric[] = [];
  for (const item of metrics) {
    const metric = asRecord(item);
    if (metric === null || metric["available"] !== true || typeof metric["name"] !== "string") {
      continue;
    }
    const points = Array.isArray(metric["points"]) ? metric["points"] : [];
    const values = points
      .map((point) => asRecord(point)?.["value"])
      .filter((value): value is number => typeof value === "number");
    parsed.push({
      name: metric["name"],
      unit: typeof metric["unit"] === "string" ? metric["unit"] : "",
      baseline: numberOr(metric["baseline"], 0),
      latest: numberOr(metric["latest"], values.at(-1) ?? 0),
      max: numberOr(metric["max"], Math.max(0, ...values)),
      threshold: typeof metric["threshold"] === "string" ? metric["threshold"] : null,
      values
    });
  }
  return parsed;
}

function numberOr(value: unknown, fallback: number): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function stageDetails(state: LiveRunState, id: LiveStageId): readonly string[] {
  return state.stages.find((stage) => stage.id === id)?.details ?? [];
}

function failRun(state: LiveRunState, message: string): LiveRunState {
  const stages = state.stages.map((stage) =>
    stage.status === "active" ? { ...stage, status: "failed" as const } : stage
  );
  return { ...state, phase: "failed", stages, errorMessage: state.errorMessage ?? message };
}

function updateStages(
  stages: readonly LiveStage[],
  id: LiveStageId,
  status: LiveStageStatus,
  details?: readonly string[]
): readonly LiveStage[] {
  return stages.map((stage) =>
    stage.id === id ? { ...stage, status, details: details ?? stage.details } : stage
  );
}

function stageStatus(state: LiveRunState, id: LiveStageId): LiveStageStatus | undefined {
  return state.stages.find((stage) => stage.id === id)?.status;
}

function countResults(output: unknown): number {
  const record = asRecord(output);
  const results = record?.["results"];
  return Array.isArray(results) ? results.length : 0;
}

function isFieldRow(value: unknown): value is readonly { field: string; value: unknown }[] {
  return Array.isArray(value) && value.length > 0 && value.every((cell) => {
    const record = asRecord(cell);
    return record !== null && typeof record["field"] === "string" && "value" in record;
  });
}

const HIDDEN_LOG_FIELDS = new Set(["@ptr", "_region", "_logGroups"]);

function isFlatLogRecord(value: unknown): value is Record<string, unknown> {
  const record = asRecord(value);
  return record !== null && (typeof record["@message"] === "string" || typeof record["@timestamp"] === "string");
}

function flatLogRecord(value: Record<string, unknown>): Record<string, string> {
  const record: Record<string, string> = {};
  for (const [key, item] of Object.entries(value)) {
    if (HIDDEN_LOG_FIELDS.has(key) || item === null || item === undefined) {
      continue;
    }
    record[key] = typeof item === "string" ? item : JSON.stringify(item);
  }
  return record;
}

/** Render one log row; CloudWatch JSON `@message` bodies and flat simulator records both work. */
export function formatLogRow(row: Readonly<Record<string, string>>): string {
  const raw = row["@message"] ?? "";
  let body: Record<string, unknown> | null = null;
  if (raw.length > 0) {
    try {
      body = asRecord(JSON.parse(raw) as unknown);
    } catch {
      body = null;
    }
  }
  const field = (key: string): string | null => {
    const value = body !== null ? body[key] : row[key];
    if (typeof value === "string" && value.length > 0) {
      return value;
    }
    return typeof value === "number" ? String(value) : null;
  };
  const text = body === null && raw.length > 0 ? raw : field("message");
  const latency = field("latency_ms");
  const errorRate = field("error_rate");
  const message = [
    field("event"),
    text,
    latency === null ? null : `latency=${latency}ms`,
    errorRate === null ? null : `error_rate=${errorRate}`
  ].filter((part): part is string => part !== null).join(" · ");
  const parts = [row["@timestamp"], row["service"], row["level"] ?? row["severity"], message]
    .filter((part): part is string => typeof part === "string" && part.length > 0);
  return parts.length > 0 ? parts.join("  ") : JSON.stringify(row);
}

function fieldRowToRecord(row: readonly { field: string; value: unknown }[]): Record<string, string> {
  const record: Record<string, string> = {};
  for (const cell of row) {
    if (cell.field === "@ptr") {
      continue;
    }
    record[cell.field] = typeof cell.value === "string" ? cell.value : JSON.stringify(cell.value);
  }
  return record;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function firstString(value: unknown): string | null {
  return stringList(value)[0] ?? null;
}
