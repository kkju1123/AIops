// @vitest-environment jsdom

import type {
  CreateLiveDemoRunResponse,
  LiveDemoOverview,
  SseEvent
} from "@agent-py/api-contracts";
import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

import { ApiClientError } from "../src/api/apiClient";
import { createLiveDemoClient, type LiveDemoClient } from "../src/liveDemo/liveDemoClient";
import {
  applyLiveRunEvent,
  describeStatusMessage,
  draftReportMarkdown,
  extractLogRows,
  formatLogRow,
  startLiveRun
} from "../src/liveDemo/liveDemoRun";
import LiveDemoView from "../src/views/LiveDemoView.vue";

const global = {
  stubs: {
    RouterLink: { props: ["to"], template: '<a :href="typeof to === \'string\' ? to : JSON.stringify(to)"><slot /></a>' }
  }
};

const quota = {
  visitorLimit: 3,
  visitorRemaining: 3,
  dailyLimit: 50,
  dailyRemaining: 50,
  maxConcurrentRuns: 2,
  running: 0
};

const overview: LiveDemoOverview = {
  available: true,
  unavailableReason: null,
  observability: "aws-cloudwatch",
  scenarios: [{
    id: "java-ecom-order-db-pool-exhausted",
    title: "订单库连接池耗尽",
    service: "order-service",
    alertName: "OrderDatabasePoolExhausted",
    severity: "critical",
    symptom: "订单创建请求排队并大量返回 503。"
  }],
  quota,
  latestRun: null
};

const created: CreateLiveDemoRunResponse = {
  run: {
    id: "live_run_1",
    scenarioId: "java-ecom-order-db-pool-exhausted",
    status: "accepted",
    createdAt: "2026-11-07T00:00:00+00:00",
    diagnosticId: "diagnostic_live_1"
  },
  runToken: "run-token",
  alert: {
    id: "live-drill:live_run_1",
    source: "local-alertmanager",
    alertName: "OrderDatabasePoolExhausted",
    service: "order-service",
    severity: "critical",
    status: "firing",
    startsAt: "2026-11-07T00:00:00Z",
    summary: "订单创建请求排队并大量返回 503。",
    labels: {},
    annotations: {},
    context: {}
  },
  alertPublished: true,
  observability: "aws-cloudwatch",
  quota: { ...quota, visitorRemaining: 2, dailyRemaining: 49, running: 1 }
};

const base = { channel: "aiops" as const, timestamp: "2026-11-07T00:00:01+00:00" };
const runEvents: SseEvent[] = [
  { ...base, id: "1", type: "task.status", task: { id: "t", status: "running", message: "Planner: retrieving SOP evidence.", progress: 15 } },
  { ...base, id: "2", type: "tool.call", toolCall: { id: "a", name: "knowledge_retrieval", status: "completed", output: { results: [{}, {}] } } },
  { ...base, id: "3", type: "reference.source", reference: { id: "r", title: "订单库连接池耗尽 SOP", sourceType: "knowledge-base" } },
  { ...base, id: "3b", type: "task.status", task: { id: "t", status: "running", message: "Planner: drafting a bounded plan with the LLM.", progress: 30 } },
  { ...base, id: "4", type: "task.status", task: { id: "t", status: "running", message: "Planner: created a SOP-backed plan with 1 step(s).", progress: 35 } },
  { ...base, id: "5", type: "tool.call", toolCall: { id: "b", name: "execute_cwl_insights_batch", status: "started", input: { log_group_names: ["/super-ai/demo"], regions: ["eu-west-1"] } } },
  {
    ...base,
    id: "6",
    type: "tool.call",
    toolCall: {
      id: "b",
      name: "execute_cwl_insights_batch",
      status: "completed",
      output: [{ type: "text", text: JSON.stringify({ results: [[
        { field: "@timestamp", value: "2026-11-07 00:00:00" },
        { field: "service", value: "order-service" },
        { field: "@message", value: "HikariPool-1 - Connection is not available" },
        { field: "@ptr", value: "ignored" }
      ]] }) }]
    }
  },
  { ...base, id: "7", type: "task.status", task: { id: "t", status: "running", message: "Replanner: moving to Report based on recorded execution evidence.", progress: 80 } },
  { ...base, id: "7a", type: "content.delta", delta: "```markdown\n# 告警分析报告\n\n", sequence: 1 },
  { ...base, id: "7b", type: "content.delta", delta: "## 📊 结论\n\n连接池", sequence: 2 },
  { ...base, id: "8", type: "report", report: { id: "rep", title: "告警分析报告", content: "# 告警分析报告\n\n## 📊 结论\n\n连接池被慢 SQL 占满。", format: "markdown" } },
  { ...base, id: "9", type: "task.status", task: { id: "t", status: "succeeded", message: "Report: diagnostic finished.", progress: 100 } },
  { ...base, id: "10", type: "complete", result: {} }
];

function fakeClient(overrides: Partial<LiveDemoClient> = {}): LiveDemoClient {
  return {
    getOverview: vi.fn().mockResolvedValue(overview),
    createRun: vi.fn().mockResolvedValue(created),
    streamRun: vi.fn(async function* () {
      for (const event of runEvents) {
        yield event;
      }
    }),
    listSopDocuments: vi.fn().mockResolvedValue({ items: [] }),
    getSopDocument: vi.fn(),
    ...overrides
  };
}

describe("live incident drill state", () => {
  it("advances all five stages from real diagnostic events", () => {
    let state = startLiveRun(created);
    expect(state.stages.find((stage) => stage.id === "alert")?.status).toBe("done");
    for (const event of runEvents) {
      state = applyLiveRunEvent(state, event);
    }

    expect(state.phase).toBe("succeeded");
    expect(state.stages.map((stage) => stage.status)).toEqual(["done", "done", "done", "done", "done"]);
    expect(state.sopHits).toEqual(["订单库连接池耗尽 SOP"]);
    expect(state.logQuery?.logGroups).toEqual(["/super-ai/demo"]);
    expect(state.logQuery?.rows[0]).toEqual({
      "@timestamp": "2026-11-07 00:00:00",
      service: "order-service",
      "@message": "HikariPool-1 - Connection is not available"
    });
    expect(state.report?.content).toContain("慢 SQL");
  });

  it("shows planning as active while the LLM drafts the plan", () => {
    let state = startLiveRun(created);
    for (const event of runEvents.slice(0, 4)) {
      state = applyLiveRunEvent(state, event);
    }

    expect(state.stages.find((stage) => stage.id === "sop")?.status).toBe("done");
    const plan = state.stages.find((stage) => stage.id === "plan");
    expect(plan?.status).toBe("active");
    expect(plan?.details).toEqual(["DeepSeek 正在制定排查计划…"]);
  });

  it("streams the report draft in sequence and replaces it with the final report", () => {
    let state = startLiveRun(created);
    const reportIndex = runEvents.findIndex((event) => event.type === "report");
    for (const event of runEvents.slice(0, reportIndex)) {
      state = applyLiveRunEvent(state, event);
    }
    const replayed = runEvents.find((event) => event.id === "7a");
    if (replayed !== undefined) {
      state = applyLiveRunEvent(state, replayed);
    }

    expect(state.report).toBeNull();
    expect(state.draftSequence).toBe(2);
    expect(draftReportMarkdown(state.draftReport)).toBe("# 告警分析报告\n\n## 📊 结论\n\n连接池");

    for (const event of runEvents.slice(reportIndex)) {
      state = applyLiveRunEvent(state, event);
    }
    expect(state.draftReport).toBe("");
    expect(state.report?.content).toContain("慢 SQL");
  });

  it("marks the active stage failed on an error event", () => {
    const state = applyLiveRunEvent(startLiveRun(created), {
      ...base,
      id: "e",
      type: "error",
      error: { code: "SYSTEM_UNAVAILABLE", category: "system", httpStatus: 503, message: "服务暂时不可用" }
    });

    expect(state.phase).toBe("failed");
    expect(state.stages.find((stage) => stage.id === "sop")?.status).toBe("failed");
    expect(state.errorMessage).toBe("服务暂时不可用");
  });

  it("translates backend status messages and tolerates unknown log shapes", () => {
    expect(describeStatusMessage("Planner: created a generic plan with 2 step(s).")).toBe(
      "Planner：生成 2 步排查计划（通用）"
    );
    expect(describeStatusMessage("Something else")).toBe("Something else");
    expect(extractLogRows({ unexpected: true })).toEqual([]);
  });

  it("parses CloudWatch batch results with flat records and JSON messages", () => {
    const text = JSON.stringify({
      summary: { total_records_returned: 1 },
      results: [{
        "@timestamp": "2026-11-07 12:47:00.993",
        "@message": JSON.stringify({
          event: "database_connection_pool_exhausted",
          message: "Checkout requests timed out",
          latency_ms: 2200,
          error_rate: 0.18
        }),
        service: "checkout-service",
        severity: "high",
        "@ptr": "hidden",
        _region: "eu-west-1"
      }]
    });
    const rows = extractLogRows([{ type: "text", text }]);

    expect(rows).toHaveLength(1);
    expect(rows[0]?.["@ptr"]).toBeUndefined();
    expect(formatLogRow(rows[0] ?? {})).toBe(
      "2026-11-07 12:47:00.993  checkout-service  high  database_connection_pool_exhausted · " +
        "Checkout requests timed out · latency=2200ms · error_rate=0.18"
    );
  });
});

describe("live incident drill client", () => {
  it("sends the run token header and never a bearer token", async () => {
    window.localStorage.setItem("super-ai.auth-token", "workspace-token");
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response("", { status: 200, headers: { "Content-Type": "text/event-stream" } })
    );
    const client = createLiveDemoClient({ baseUrl: "http://api.test", fetchImpl });

    for await (const event of client.streamRun("live_run_1", "run-token")) {
      expect(event).toBeUndefined();
    }

    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(url).toBe("http://api.test/live-demo/runs/live_run_1:stream");
    expect(headers["x-live-demo-token"]).toBe("run-token");
    expect(headers["authorization"]).toBeUndefined();
  });

  it("links run creation to the signed-in requester with the workspace bearer token", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true, data: created, meta: { requestId: "req_1" } }), {
        status: 202,
        headers: { "Content-Type": "application/json" }
      })
    );
    const client = createLiveDemoClient({
      baseUrl: "http://api.test",
      fetchImpl,
      getAccessToken: () => "guest-token"
    });

    const result = await client.createRun("java-ecom-order-db-pool-exhausted");

    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://api.test/live-demo/runs");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer guest-token");
    expect(result.run.diagnosticId).toBe("diagnostic_live_1");
  });
});

const simulatedCreated: CreateLiveDemoRunResponse = { ...created, observability: "simulator" };
const simulatedLogs = {
  simulated: true,
  source: "fault-simulator",
  service: "order-service",
  summary: { totalMatched: 80, returned: 2, errorCount: 18, warnCount: 3, firstErrorAt: "2026-11-07T00:00:00Z", exceptions: [] },
  records: [
    { "@timestamp": "2026-11-07T00:05:00Z", level: "ERROR", service: "order-service", event: "order_db_pool_exhausted", message: "HikariPool-1 - Connection is not available", latency_ms: 2600, error_rate: 0.21, simulated: true },
    { "@timestamp": "2026-11-07T00:04:30Z", level: "INFO", service: "order-service", event: "request_completed", message: "POST /api/orders completed in 90ms", latency_ms: 90, simulated: true }
  ]
};
const simulatedMetrics = {
  simulated: true,
  metrics: [
    { name: "hikaricp_pending_connections", available: true, unit: "count", threshold: "> 20 for 3m", baseline: 6.3, latest: 120, max: 126, points: [{ timestamp: "t1", value: 6 }, { timestamp: "t2", value: 126 }] },
    { name: "unknown_metric", available: false }
  ]
};
const mcpText = (value: unknown): unknown => [{ type: "text", text: JSON.stringify(value) }];
const simulatedEvents: SseEvent[] = [
  ...runEvents.slice(0, 4),
  { ...base, id: "s4", type: "task.status", task: { id: "t", status: "running", message: "Planner: created a SOP-backed plan with 2 step(s).", progress: 35 } },
  { ...base, id: "s5", type: "tool.call", toolCall: { id: "l", name: "query_service_logs", status: "started", input: { service: "order-service" } } },
  { ...base, id: "s6", type: "tool.call", toolCall: { id: "l", name: "query_service_logs", status: "completed", output: mcpText(simulatedLogs) } },
  { ...base, id: "s7", type: "task.status", task: { id: "t", status: "running", message: "Replanner: continuing with the next bounded step.", progress: 70 } },
  { ...base, id: "s8", type: "tool.call", toolCall: { id: "m", name: "query_service_metrics", status: "started", input: { service: "order-service" } } },
  { ...base, id: "s9", type: "tool.call", toolCall: { id: "m", name: "query_service_metrics", status: "completed", output: mcpText(simulatedMetrics) } },
  ...runEvents.slice(runEvents.findIndex((event) => event.id === "7"))
];

describe("live drill with the fault simulator", () => {
  it("keeps execution active until every step finishes and parses logs and metrics", () => {
    let state = startLiveRun(simulatedCreated);
    expect(state.stages.find((stage) => stage.id === "execute")?.caption).toContain("故障模拟器");
    const afterLogs = simulatedEvents.findIndex((event) => event.id === "s7");
    for (const event of simulatedEvents.slice(0, afterLogs + 1)) {
      state = applyLiveRunEvent(state, event);
    }
    expect(state.stages.find((stage) => stage.id === "execute")?.status).toBe("active");
    expect(state.logQuery?.summary).toEqual({ totalMatched: 80, errorCount: 18, firstErrorAt: "2026-11-07T00:00:00Z" });
    expect(formatLogRow(state.logQuery?.rows[0] ?? {})).toBe(
      "2026-11-07T00:05:00Z  order-service  ERROR  order_db_pool_exhausted · HikariPool-1 - Connection is not available · latency=2600ms · error_rate=0.21"
    );

    for (const event of simulatedEvents.slice(afterLogs + 1)) {
      state = applyLiveRunEvent(state, event);
    }
    expect(state.metrics).toEqual([
      { name: "hikaricp_pending_connections", unit: "count", baseline: 6.3, latest: 120, max: 126, threshold: "> 20 for 3m", values: [6, 126] }
    ]);
    const execute = state.stages.find((stage) => stage.id === "execute");
    expect(execute?.status).toBe("done");
    expect(execute?.details).toEqual([
      "调用 query_service_logs",
      "匹配 80 条日志，其中 ERROR 18 条",
      "调用 query_service_metrics",
      "取回 1 项指标，其中 1 项明显偏离基线"
    ]);
    expect(state.phase).toBe("succeeded");
  });

  it("labels simulator data on the page", async () => {
    const client = fakeClient({
      getOverview: vi.fn().mockResolvedValue({ ...overview, observability: "simulator" }),
      createRun: vi.fn().mockResolvedValue(simulatedCreated),
      streamRun: vi.fn(async function* () {
        for (const event of simulatedEvents) {
          yield event;
        }
      })
    });
    const wrapper = mount(LiveDemoView, { global, props: { client } });
    await flushPromises();
    expect(wrapper.get(".live-view__lead").text()).toContain("故障模拟器");
    expect(wrapper.text()).toContain("通过 MCP 调用故障模拟器，查询日志与指标");
    expect(wrapper.text()).not.toContain("AWS CloudWatch 查询真实日志");

    await wrapper.get(".live-view__trigger").trigger("click");
    await flushPromises();

    expect(wrapper.get(".live-view__sim-badge").text()).toContain("故障模拟器生成");
    expect(wrapper.get(".live-view__metrics").text()).toContain("hikaricp_pending_connections");
    expect(wrapper.get(".live-view__metrics").text()).toContain("峰值 126");
    expect(wrapper.text()).toContain("匹配 80 条 · ERROR 18 条");
  });
});

describe("LiveDemoView", () => {
  it("lets a visitor trigger a drill and watch it finish with a report", async () => {
    const client = fakeClient();
    const wrapper = mount(LiveDemoView, { global, props: { client } });
    await flushPromises();

    expect(wrapper.get("#live-title").text()).toContain("自动排查线上故障");
    expect(wrapper.find(".live-view__nav").exists()).toBe(false);
    expect(wrapper.text()).toContain("订单库连接池耗尽");
    expect(wrapper.text()).toContain("本小时还可触发 3 / 3 次");

    await wrapper.get(".live-view__trigger").trigger("click");
    await flushPromises();

    expect(client.createRun).toHaveBeenCalledWith("java-ecom-order-db-pool-exhausted");
    expect(client.streamRun).toHaveBeenCalledWith("live_run_1", "run-token");
    expect(wrapper.findAll(".live-view__stages > li.is-done")).toHaveLength(5);
    expect(wrapper.text()).toContain("HikariPool-1 - Connection is not available");
    expect(wrapper.get(".live-view__report").text()).toContain("连接池被慢 SQL 占满");
    expect(wrapper.get(".live-view__trigger").text()).toContain("再触发一次");
    const next = wrapper.get(".live-view__next a");
    expect(next.text()).toContain("在智能诊断中查看完整证据链");
    expect(JSON.parse(next.attributes("href") ?? "{}")).toEqual({
      name: "aiops",
      query: { diagnosticId: "diagnostic_live_1" }
    });
  });

  it("omits the evidence-chain link for anonymous runs", async () => {
    const client = fakeClient({
      createRun: vi.fn().mockResolvedValue({ ...created, run: { ...created.run, diagnosticId: null } })
    });
    const wrapper = mount(LiveDemoView, { global, props: { client } });
    await flushPromises();
    await wrapper.get(".live-view__trigger").trigger("click");
    await flushPromises();

    expect(wrapper.find(".live-view__next").exists()).toBe(false);
  });

  it("explains rate limits and shows the latest real run as a labelled fallback", async () => {
    const limited: LiveDemoOverview = {
      ...overview,
      quota: { ...quota, visitorRemaining: 0 },
      latestRun: {
        runId: "live_run_0",
        scenarioId: "java-ecom-order-db-pool-exhausted",
        scenarioTitle: "订单库连接池耗尽",
        startedAt: "2026-11-07T00:00:00+00:00",
        completedAt: "2026-11-07T00:01:20+00:00",
        durationSeconds: 80,
        report: { id: "rep0", title: "告警分析报告", content: "## 📊 结论\n\n上一次的真实结论。", format: "markdown" }
      }
    };
    const client = fakeClient({ getOverview: vi.fn().mockResolvedValue(limited) });
    const wrapper = mount(LiveDemoView, { global, props: { client } });
    await flushPromises();

    expect(wrapper.get(".live-view__trigger").attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("1 小时内的演练次数已用完");
    expect(wrapper.get(".live-view__report--fallback").text()).toContain("真实运行");
    expect(wrapper.get(".live-view__report--fallback").text()).toContain("上一次的真实结论");
  });

  it("surfaces a server-side rate limit returned when triggering", async () => {
    const client = fakeClient({
      createRun: vi.fn().mockRejectedValue(new ApiClientError({
        code: "BUSINESS_RATE_LIMITED",
        category: "business",
        httpStatus: 429,
        message: "今日演练次数已用完，请明天再试。"
      }))
    });
    const wrapper = mount(LiveDemoView, { global, props: { client } });
    await flushPromises();
    await wrapper.get(".live-view__trigger").trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("今日演练次数已用完");
    expect(client.streamRun).not.toHaveBeenCalled();
  });
});
