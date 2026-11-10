// @vitest-environment jsdom

import type {
  AiopsDiagnosticEvidenceChain,
  AiopsDiagnosticSummary,
  AuthUser
} from "@agent-py/api-contracts";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { afterEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";

import type { AiopsClient } from "../src/aiops/aiopsClient";
import DrillSopLibrary from "../src/components/DrillSopLibrary.vue";
import type { LiveDemoClient } from "../src/liveDemo/liveDemoClient";
import { setAiopsClientFactoryForTests, useAiopsStore } from "../src/stores/aiops";
import { useAuthStore } from "../src/stores/auth";
import AiopsView from "../src/views/AiopsView.vue";

const guestUser: AuthUser = {
  id: "user_guest",
  email: "guest_1@guest.agent-py.local",
  displayName: "访客 1A2B",
  createdAt: "2026-11-10T00:00:00.000Z",
  accountKind: "guest"
};

const drillTask: AiopsDiagnosticSummary = {
  id: "diagnostic_drill",
  ownerUserId: "user_drill_account",
  status: "succeeded",
  query: "order-service 触发告警 OrderDatabasePoolExhausted",
  inputPayload: { liveDemo: true, simulatedFault: { scenarioId: "java-ecom-order-db-pool-exhausted" } },
  resultPayload: {},
  createdAt: "2026-11-10T00:00:00.000Z",
  updatedAt: "2026-11-10T00:00:30.000Z",
  completedAt: "2026-11-10T00:00:30.000Z",
  reports: [],
  origin: "live-drill",
  simulated: true
};

const drillChain: AiopsDiagnosticEvidenceChain = {
  task: drillTask,
  steps: [],
  toolCalls: [],
  evidence: [],
  reports: [{
    id: "report_drill",
    title: "告警分析报告",
    content: "## 📊 结论\n\n连接池被慢 SQL 占满。",
    payload: {},
    evidenceIds: [],
    createdAt: "2026-11-10T00:00:30.000Z"
  }],
  reportEvidenceLinks: [],
  checkpoints: []
};

function fakeAiopsClient(): AiopsClient {
  return {
    createDiagnostic: vi.fn(),
    getEvidenceChain: vi.fn().mockResolvedValue(drillChain),
    listActiveAlerts: vi.fn().mockResolvedValue({ items: [] }),
    listDiagnosticCases: vi.fn().mockResolvedValue({ items: [] }),
    listDiagnostics: vi.fn().mockResolvedValue({ items: [drillTask] }),
    saveDiagnosticCase: vi.fn(),
    streamDiagnostic: vi.fn(async function* () {})
  };
}

afterEach(() => setAiopsClientFactoryForTests(null));

describe("guest diagnosis workspace", () => {
  it("skips the owner's real alerts when initializing for a guest", async () => {
    setActivePinia(createPinia());
    const client = fakeAiopsClient();
    setAiopsClientFactoryForTests(() => client);

    await useAiopsStore().initialize({ includeAlerts: false });

    expect(client.listDiagnostics).toHaveBeenCalledTimes(1);
    expect(client.listActiveAlerts).not.toHaveBeenCalled();
  });

  it("opens the drill diagnosis from the query and labels it as simulated", async () => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const client = fakeAiopsClient();
    setAiopsClientFactoryForTests(() => client);
    useAuthStore().user = guestUser;
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: "/aiops", name: "aiops", component: AiopsView },
        { path: "/drill", name: "drill", component: { template: "<div />" } },
        { path: "/knowledge", name: "knowledge", component: { template: "<div />" } }
      ]
    });
    await router.push({ name: "aiops", query: { diagnosticId: "diagnostic_drill" } });
    await router.isReady();

    const wrapper = mount(AiopsView, { global: { plugins: [pinia, router] } });
    await flushPromises();

    expect(client.listActiveAlerts).not.toHaveBeenCalled();
    expect(client.getEvidenceChain).toHaveBeenCalledWith("diagnostic_drill");
    expect(wrapper.findAll('[role="tab"]').map((tab) => tab.text())).toEqual(["历史诊断1"]);
    expect(wrapper.text()).not.toContain("描述问题");
    expect(wrapper.get(".aiops-view__guest-note").text()).toContain("需要所有者账号");
    expect(wrapper.get(".aiops-view__drill-badge").text()).toBe("故障演练 · 模拟数据");
    expect(wrapper.get(".aiops-history__drill").text()).toBe("演练 · 模拟");
    expect(wrapper.text()).toContain("连接池被慢 SQL 占满");
  });
});

describe("drill SOP library", () => {
  it("lists SOP documents read-only and shows the selected document text", async () => {
    const client: LiveDemoClient = {
      getOverview: vi.fn(),
      createRun: vi.fn(),
      streamRun: vi.fn(),
      listSopDocuments: vi.fn().mockResolvedValue({
        items: [{
          id: "doc_sop_1",
          filename: "order-db-pool.md",
          sizeBytes: 2048,
          mimeType: "text/markdown",
          status: "active",
          indexStatus: "indexed",
          updatedAt: "2026-11-10T00:00:00.000Z"
        }]
      }),
      getSopDocument: vi.fn().mockResolvedValue({
        id: "doc_sop_1",
        filename: "order-db-pool.md",
        sizeBytes: 2048,
        mimeType: "text/markdown",
        status: "active",
        indexStatus: "indexed",
        updatedAt: "2026-11-10T00:00:00.000Z",
        content: "# 订单库连接池耗尽 SOP\n\n1. 检查慢 SQL"
      })
    };

    const wrapper = mount(DrillSopLibrary, { props: { client } });
    await flushPromises();

    expect(client.getSopDocument).toHaveBeenCalledWith("doc_sop_1");
    expect(wrapper.get(".sop-library__readonly").text()).toContain("访客只读");
    expect(wrapper.text()).toContain("order-db-pool.md");
    expect(wrapper.get(".sop-library__document").text()).toContain("检查慢 SQL");
    expect(wrapper.find("input[type=file]").exists()).toBe(false);
  });
});
