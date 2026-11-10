<script setup lang="ts">
import type { LiveDemoOverview, LiveDemoScenario } from "@agent-py/api-contracts";
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  CircleDashed,
  FileText,
  ListChecks,
  Loader2,
  Network,
  RotateCcw,
  Search,
  Siren,
  XCircle,
  Zap
} from "lucide-vue-next";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";

import MarkdownContent from "../components/MarkdownContent.vue";
import { createLiveDemoClient, type LiveDemoClient } from "../liveDemo/liveDemoClient";
import {
  applyLiveRunEvent,
  draftReportMarkdown,
  formatLogRow,
  initialLiveRunState,
  startLiveRun,
  startingLiveRunState,
  type LiveRunState,
  type LiveStageId
} from "../liveDemo/liveDemoRun";
import { toUserFacingError } from "../ui/userFacingError";

const props = defineProps<{ readonly client?: LiveDemoClient }>();
const client = props.client ?? createLiveDemoClient();

const overview = ref<LiveDemoOverview | null>(null);
const overviewError = ref<string | null>(null);
const loadingOverview = ref(true);
const selectedScenarioId = ref<string | null>(null);
const run = ref<LiveRunState>(initialLiveRunState());
const triggerError = ref<string | null>(null);
const elapsedSeconds = ref(0);
let timer: ReturnType<typeof setInterval> | null = null;

const stageIcons: Record<LiveStageId, typeof Siren> = {
  alert: Siren,
  sop: BookOpen,
  plan: ListChecks,
  execute: Search,
  report: FileText
};

const selectedScenario = computed<LiveDemoScenario | null>(() => {
  const scenarios = overview.value?.scenarios ?? [];
  return scenarios.find((item) => item.id === selectedScenarioId.value) ?? scenarios[0] ?? null;
});
const busy = computed(() => run.value.phase === "starting" || run.value.phase === "running");
const simulated = computed(() =>
  run.value.phase === "idle" || run.value.phase === "starting"
    ? overview.value?.observability !== "aws-cloudwatch"
    : run.value.observability === "simulator"
);
const quota = computed(() => overview.value?.quota ?? null);
const quotaExhausted = computed(() => {
  const value = quota.value;
  return value !== null && (value.visitorRemaining <= 0 || value.dailyRemaining <= 0);
});
const canTrigger = computed(() =>
  overview.value?.available === true && selectedScenario.value !== null && !busy.value && !quotaExhausted.value
);
const blockedReason = computed(() => {
  if (overviewError.value !== null) {
    return overviewError.value;
  }
  if (overview.value !== null && !overview.value.available) {
    return overview.value.unavailableReason ?? "实时演练暂不可用。";
  }
  if (quota.value !== null && quota.value.visitorRemaining <= 0) {
    return "你在 1 小时内的演练次数已用完，请稍后再试。";
  }
  if (quota.value !== null && quota.value.dailyRemaining <= 0) {
    return "今日演练次数已用完，请明天再试。";
  }
  return triggerError.value;
});
const showFallback = computed(() =>
  overview.value?.latestRun != null &&
  run.value.report === null &&
  !busy.value &&
  (blockedReason.value !== null || run.value.phase === "failed")
);
const triggerLabel = computed(() => {
  if (run.value.phase === "starting") {
    return "正在触发…";
  }
  if (run.value.phase === "running") {
    return "诊断进行中…";
  }
  return run.value.phase === "idle" ? "触发故障" : "再触发一次";
});

onMounted(() => {
  void loadOverview();
});

onBeforeUnmount(stopTimer);

async function loadOverview(): Promise<void> {
  try {
    overview.value = await client.getOverview();
    overviewError.value = null;
    if (run.value.phase === "idle") {
      run.value = initialLiveRunState(overview.value.observability);
    }
    selectedScenarioId.value ??= overview.value.scenarios[0]?.id ?? null;
  } catch (error) {
    overviewError.value = `演练服务暂时无法连接：${toUserFacingError(error)}`;
  } finally {
    loadingOverview.value = false;
  }
}

async function trigger(): Promise<void> {
  const scenario = selectedScenario.value;
  if (scenario === null || !canTrigger.value) {
    return;
  }
  triggerError.value = null;
  run.value = startingLiveRunState();
  startTimer();
  try {
    const created = await client.createRun(scenario.id);
    run.value = startLiveRun(created);
    if (overview.value !== null) {
      overview.value = { ...overview.value, quota: created.quota };
    }
    for await (const event of client.streamRun(created.run.id, created.runToken)) {
      run.value = applyLiveRunEvent(run.value, event);
    }
    if (run.value.phase === "running") {
      run.value = applyLiveRunEvent(run.value, {
        id: "local-stream-closed",
        type: "error",
        channel: "aiops",
        timestamp: new Date().toISOString(),
        error: {
          code: "SYSTEM_UNAVAILABLE",
          category: "system",
          httpStatus: 503,
          message: "事件流意外结束，请稍后重试。"
        }
      });
    }
  } catch (error) {
    triggerError.value = toUserFacingError(error);
    run.value = run.value.phase === "starting"
      ? initialLiveRunState(overview.value?.observability)
      : { ...run.value, phase: "failed", errorMessage: triggerError.value };
  } finally {
    stopTimer();
    void loadOverview();
  }
}

function startTimer(): void {
  stopTimer();
  elapsedSeconds.value = 0;
  const startedAt = Date.now();
  timer = setInterval(() => {
    elapsedSeconds.value = Math.round((Date.now() - startedAt) / 1000);
  }, 1000);
}

function stopTimer(): void {
  if (timer !== null) {
    clearInterval(timer);
    timer = null;
  }
}

function sparkline(values: readonly number[]): string {
  if (values.length < 2) {
    return "";
  }
  const max = Math.max(...values);
  const min = Math.min(...values);
  const span = max - min || 1;
  return values
    .map((value, index) => `${((index / (values.length - 1)) * 100).toFixed(1)},${(22 - ((value - min) / span) * 20).toFixed(1)}`)
    .join(" ");
}

function formatMetric(value: number, unit: string): string {
  const rounded = Math.abs(value) >= 100 ? Math.round(value) : Math.round(value * 10) / 10;
  if (unit === "count" || unit === "") {
    return String(rounded);
  }
  return `${rounded}${unit}`;
}

function formatTime(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("zh-CN", { hour12: false });
}

</script>

<template>
  <section class="live-view" aria-label="故障演练">
    <div class="live-view__layout">
      <section class="live-view__control" aria-labelledby="live-title">
        <p class="live-view__eyebrow">LIVE INCIDENT DRILL · 实时故障演练</p>
        <h2 id="live-title">点一下，<br />看 AI 自动排查线上故障</h2>
        <p v-if="simulated" class="live-view__lead">
          点击按钮后，故障模拟器会向所选服务<strong>注入</strong>这次故障并实时产生日志与指标，同时发出一条告警。
          AIOps Agent 随即检索 SOP、让 DeepSeek 制定排查计划、通过 MCP 查询日志与指标，最后给出根因报告。
          全程约半分钟，每一步都会实时显示在「诊断过程」面板中。
        </p>
        <p v-else class="live-view__lead">
          点击按钮后，系统会<strong>真的</strong>发出一条线上告警，AIOps Agent 随即检索 SOP、制定排查计划、
          通过 MCP 查询 AWS CloudWatch 中的真实日志，最后给出根因报告。每一步都会实时显示在「诊断过程」面板中。
        </p>

        <div v-if="loadingOverview" class="live-view__card live-view__card--muted" role="status">
          <Loader2 class="live-view__spin" :size="18" aria-hidden="true" />正在连接演练服务…
        </div>

        <div v-else-if="selectedScenario !== null" class="live-view__card">
          <label v-if="(overview?.scenarios.length ?? 0) > 1" class="live-view__select">
            <span>故障场景</span>
            <select v-model="selectedScenarioId" :disabled="busy">
              <option v-for="item in overview?.scenarios ?? []" :key="item.id" :value="item.id">{{ item.title }}</option>
            </select>
          </label>
          <p class="live-view__card-label">本次模拟的故障</p>
          <h2>{{ selectedScenario.title }}</h2>
          <dl>
            <div><dt>服务</dt><dd>{{ selectedScenario.service }}</dd></div>
            <div><dt>告警</dt><dd>{{ selectedScenario.alertName }}</dd></div>
            <div><dt>级别</dt><dd class="live-view__severity">{{ selectedScenario.severity }}</dd></div>
          </dl>
          <p class="live-view__symptom">{{ selectedScenario.symptom }}</p>
          <button
            class="live-view__trigger"
            type="button"
            :disabled="!canTrigger"
            :aria-busy="busy"
            @click="trigger"
          >
            <Loader2 v-if="busy" class="live-view__spin" :size="20" aria-hidden="true" />
            <RotateCcw v-else-if="run.phase !== 'idle'" :size="20" aria-hidden="true" />
            <Zap v-else :size="20" aria-hidden="true" />
            {{ triggerLabel }}
          </button>
          <p v-if="quota !== null" class="live-view__quota">
            本小时还可触发 {{ quota.visitorRemaining }} / {{ quota.visitorLimit }} 次 · 全站今日剩余 {{ quota.dailyRemaining }} 次
          </p>
        </div>

        <p v-if="blockedReason !== null" class="live-view__notice" role="alert">
          <AlertTriangle :size="16" aria-hidden="true" />{{ blockedReason }}
        </p>

        <section class="live-view__how" aria-label="技术实现">
          <h3>背后发生了什么</h3>
          <ol>
            <li><strong>Alertmanager</strong> 接收告警，后端以专用服务账号创建诊断任务</li>
            <li><strong>LangGraph</strong> 编排 Planner → Executor → Replanner → Report</li>
            <li><strong>RAG</strong>：pgvector 向量 + BM25 关键词召回，RRF 融合，BGE 重排</li>
            <li v-if="simulated"><strong>MCP</strong>：仓库内的故障模拟器 MCP Server 按注入的故障实时生成日志与指标（标注 simulated）；所有者账号的智能诊断则接入官方 AWS CloudWatch MCP Server</li>
            <li v-else><strong>MCP</strong>：官方 AWS CloudWatch MCP Server 查询真实日志</li>
            <li><strong>SSE</strong>：后台任务事件持久化，页面实时订阅</li>
          </ol>
          <p>为控制费用，每位访客每小时限 {{ quota?.visitorLimit ?? 3 }} 次。</p>
        </section>
      </section>

      <section class="live-view__run" aria-labelledby="run-title">
        <header class="live-view__run-header">
          <h2 id="run-title">诊断过程</h2>
          <span v-if="busy" class="live-view__elapsed" aria-live="off">已用时 {{ elapsedSeconds }}s</span>
          <span v-else-if="run.phase === 'succeeded'" class="live-view__elapsed live-view__elapsed--ok">用时 {{ elapsedSeconds }}s · 完成</span>
        </header>

        <div v-if="run.phase !== 'idle'" class="live-view__progress" role="progressbar" :aria-valuenow="run.progress" aria-valuemin="0" aria-valuemax="100">
          <span :style="{ width: `${run.progress}%` }"></span>
        </div>

        <ol class="live-view__stages" aria-live="polite">
          <li v-for="stage in run.stages" :key="stage.id" :class="`is-${stage.status}`">
            <span class="live-view__stage-icon" aria-hidden="true">
              <Loader2 v-if="stage.status === 'active'" class="live-view__spin" :size="18" />
              <CheckCircle2 v-else-if="stage.status === 'done'" :size="18" />
              <XCircle v-else-if="stage.status === 'failed'" :size="18" />
              <component :is="stageIcons[stage.id]" v-else :size="18" />
            </span>
            <div>
              <strong>{{ stage.title }}</strong>
              <small>{{ stage.caption }}</small>
              <ul v-if="stage.details.length > 0">
                <li v-for="detail in stage.details" :key="detail">{{ detail }}</li>
              </ul>
              <ul v-if="stage.id === 'sop' && run.sopHits.length > 0" class="live-view__hits">
                <li v-for="hit in run.sopHits" :key="hit">📄 {{ hit }}</li>
              </ul>
              <p
                v-if="stage.id === 'execute' && simulated && (run.logQuery !== null || run.metrics.length > 0)"
                class="live-view__sim-badge"
              >故障模拟器生成 · 非生产数据</p>
              <ul v-if="stage.id === 'execute' && run.metrics.length > 0" class="live-view__metrics" aria-label="指标">
                <li v-for="metric in run.metrics" :key="metric.name">
                  <svg viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true">
                    <polyline :points="sparkline(metric.values)" />
                  </svg>
                  <span class="live-view__metric-name">{{ metric.name }}</span>
                  <span>基线 {{ formatMetric(metric.baseline, metric.unit) }} → 峰值 <strong>{{ formatMetric(metric.max, metric.unit) }}</strong></span>
                  <small v-if="metric.threshold !== null">告警阈值 {{ metric.threshold }}</small>
                </li>
              </ul>
              <div v-if="stage.id === 'execute' && run.logQuery !== null" class="live-view__logs">
                <p v-if="run.logQuery.summary !== null">
                  匹配 {{ run.logQuery.summary.totalMatched }} 条 · ERROR {{ run.logQuery.summary.errorCount }} 条<template v-if="run.logQuery.summary.firstErrorAt !== null"> · 首次报错 {{ formatTime(run.logQuery.summary.firstErrorAt) }}</template>
                </p>
                <p v-else>
                  {{ run.logQuery.region ?? "" }} {{ run.logQuery.logGroups.join(", ") }}
                </p>
                <pre v-if="run.logQuery.rows.length > 0"><code><template v-for="(row, index) in run.logQuery.rows" :key="index">{{ formatLogRow(row) }}
</template></code></pre>
                <p v-if="run.logQuery.error !== null" class="live-view__log-error">{{ run.logQuery.error }}</p>
              </div>
            </div>
          </li>
        </ol>

        <p v-if="run.phase === 'idle'" class="live-view__placeholder">
          <CircleDashed :size="16" aria-hidden="true" />点击左侧「触发故障」开始，五个阶段会依次亮起。
        </p>

        <p v-if="run.phase === 'failed' && run.errorMessage !== null" class="live-view__notice" role="alert">
          <AlertTriangle :size="16" aria-hidden="true" />{{ run.errorMessage }}
        </p>

        <article v-if="run.report !== null" class="live-view__report" aria-label="诊断报告">
          <MarkdownContent :content="run.report.content" mode="report" />
        </article>
        <article
          v-else-if="run.draftReport.length > 0"
          class="live-view__report live-view__report--draft"
          aria-label="正在生成的诊断报告"
          aria-busy="true"
        >
          <p class="live-view__draft-label"><Loader2 :size="14" class="live-view__spin" aria-hidden="true" />DeepSeek 正在逐字撰写报告…</p>
          <MarkdownContent :content="draftReportMarkdown(run.draftReport)" mode="report" />
        </article>

        <div v-if="run.diagnosticId !== null && (run.phase === 'succeeded' || run.phase === 'failed')" class="live-view__next">
          <RouterLink :to="{ name: 'aiops', query: { diagnosticId: run.diagnosticId } }">
            <Network :size="16" aria-hidden="true" />在智能诊断中查看完整证据链<ArrowRight :size="15" aria-hidden="true" />
          </RouterLink>
          <small>这次诊断已进入你的诊断历史，可回看时间线、工具调用、证据与报告。</small>
        </div>

        <article v-if="showFallback && overview?.latestRun" class="live-view__report live-view__report--fallback" aria-label="最近一次真实运行">
          <p class="live-view__fallback-label">
            当前无法实时运行，下面是最近一次<strong>真实运行</strong>的报告：{{ overview.latestRun.scenarioTitle }} ·
            {{ formatTime(overview.latestRun.completedAt) }} 完成 · 用时 {{ overview.latestRun.durationSeconds }}s
          </p>
          <MarkdownContent :content="overview.latestRun.report.content" mode="report" />
        </article>

        <details v-if="run.timeline.length > 0" class="live-view__timeline">
          <summary>查看原始事件流（{{ run.timeline.length }} 条）</summary>
          <ol>
            <li v-for="(entry, index) in run.timeline" :key="index">
              <time>{{ formatTime(entry.at) }}</time><span>{{ entry.message }}</span>
            </li>
          </ol>
        </details>
      </section>
    </div>
  </section>
</template>

<style scoped>
.live-view { background: var(--surface-raised); color: var(--text-primary); display: block; height: 100%; min-height: 0; overflow-x: hidden; overflow-y: auto; }
.live-view__layout { display: grid; gap: clamp(1.25rem, 3vw, 2.5rem); grid-template-columns: minmax(0, 25rem) minmax(0, 1fr); margin: 0 auto; max-width: 84rem; padding: clamp(1.25rem, 3vw, 2.5rem) clamp(1rem, 4vw, 3rem) 4rem; }
.live-view__control { align-self: start; display: grid; gap: 1rem; position: sticky; top: 1.25rem; }
.live-view__eyebrow { color: var(--accent-ink); font-size: 0.72rem; letter-spacing: 0.16em; margin: 0; }
.live-view__control h2#live-title { font-size: clamp(1.5rem, 2.2vw, 1.9rem); line-height: 1.25; margin: 0; }
.live-view__lead { color: var(--text-secondary); font-size: 0.9rem; line-height: 1.8; margin: 0; }
.live-view__lead strong { color: var(--accent); }
.live-view__card { background: var(--surface-raised); border: 1px solid var(--line-strong); border-radius: 6px; display: grid; gap: 0.7rem; padding: 1.1rem; }
.live-view__card--muted { align-items: center; color: var(--text-secondary); display: flex; gap: 0.5rem; }
.live-view__card-label { color: var(--text-tertiary); font-size: 0.72rem; margin: 0; }
.live-view__card h2 { font-size: 1.25rem; margin: 0; }
.live-view__card dl { display: grid; gap: 0.35rem; margin: 0; }
.live-view__card dl div { display: flex; font-size: 0.8rem; gap: 0.8rem; }
.live-view__card dt { color: var(--text-tertiary); min-width: 2.5rem; }
.live-view__card dd { margin: 0; overflow-wrap: anywhere; }
.live-view__severity { color: var(--danger); text-transform: uppercase; }
.live-view__symptom { border-left: 2px solid var(--danger); color: var(--text-secondary); font-size: 0.82rem; line-height: 1.7; margin: 0; padding-left: 0.7rem; }
.live-view__select { display: grid; font-size: 0.75rem; gap: 0.3rem; }
.live-view__select select { background: var(--surface-inset); border: 1px solid var(--line-strong); color: var(--text-primary); padding: 0.45rem; }
.live-view__trigger { align-items: center; background: var(--accent); border: 0; border-radius: 4px; color: var(--on-accent); cursor: pointer; display: inline-flex; font: inherit; font-size: 1.05rem; font-weight: 800; gap: 0.6rem; justify-content: center; min-height: 3.4rem; padding: 0 1rem; transition: box-shadow 160ms ease, transform 160ms ease; }
.live-view__trigger:hover:not(:disabled) { box-shadow: 0 0 24px rgb(0 255 255 / 45%); transform: translateY(-1px); }
.live-view__trigger:focus-visible { outline: 2px solid var(--accent-ink); outline-offset: 3px; }
.live-view__trigger:disabled { cursor: not-allowed; opacity: 0.55; }
.live-view__quota { color: var(--text-tertiary); font-size: 0.72rem; margin: 0; text-align: center; }
.live-view__notice { align-items: flex-start; background: var(--status-waiting-bg); border: 1px solid var(--status-waiting-border); color: var(--status-waiting-text); display: flex; font-size: 0.8rem; gap: 0.5rem; line-height: 1.6; margin: 0; padding: 0.7rem 0.8rem; }
.live-view__how { border-top: 1px solid var(--line); padding-top: 1rem; }
.live-view__how h3 { color: var(--text-secondary); font-size: 0.8rem; margin: 0 0 0.6rem; }
.live-view__how ol { color: var(--text-secondary); display: grid; font-size: 0.76rem; gap: 0.45rem; line-height: 1.6; margin: 0; padding-left: 1.1rem; }
.live-view__how strong { color: var(--text-primary); }
.live-view__how p { color: var(--text-tertiary); font-size: 0.72rem; margin: 0.8rem 0 0; }
.live-view__run { align-content: start; align-self: start; background: var(--surface); border: 1px solid var(--line); border-radius: 6px; display: grid; gap: 1rem; min-width: 0; padding: clamp(1rem, 2.5vw, 1.6rem); }
.live-view__run-header { align-items: baseline; display: flex; justify-content: space-between; }
.live-view__run-header h2 { font-size: 1.05rem; margin: 0; }
.live-view__elapsed { color: var(--status-running-text); font-size: 0.78rem; }
.live-view__elapsed--ok { color: var(--success); }
.live-view__progress { background: var(--surface-inset); height: 4px; overflow: hidden; }
.live-view__progress span { background: var(--accent); display: block; height: 100%; transition: width 400ms ease; }
.live-view__stages { display: grid; gap: 0; list-style: none; margin: 0; padding: 0; }
.live-view__stages > li { border-left: 2px solid var(--line); display: grid; gap: 0.8rem; grid-template-columns: 2rem minmax(0, 1fr); margin-left: 0.95rem; padding: 0 0 1.2rem 0; position: relative; }
.live-view__stages > li:last-child { border-left-color: transparent; }
.live-view__stage-icon { align-items: center; background: var(--surface); border: 1px solid var(--line-strong); border-radius: 50%; color: var(--text-tertiary); display: inline-flex; height: 2rem; justify-content: center; margin-left: -1.05rem; width: 2rem; }
.live-view__stages > li.is-active .live-view__stage-icon { border-color: var(--accent); box-shadow: 0 0 14px rgb(0 255 255 / 35%); color: var(--accent); }
.live-view__stages > li.is-done { border-left-color: var(--status-success-border); }
.live-view__stages > li.is-done .live-view__stage-icon { border-color: var(--success); color: var(--success); }
.live-view__stages > li.is-failed .live-view__stage-icon { border-color: var(--danger); color: var(--danger); }
.live-view__stages strong { display: block; font-size: 0.92rem; }
.live-view__stages > li.is-pending strong { color: var(--text-tertiary); }
.live-view__stages small { color: var(--text-tertiary); display: block; font-size: 0.72rem; margin-top: 0.2rem; }
.live-view__stages ul { color: var(--text-secondary); display: grid; font-size: 0.8rem; gap: 0.25rem; list-style: none; margin: 0.5rem 0 0; padding: 0; }
.live-view__hits li { color: var(--accent); }
.live-view__logs { margin-top: 0.5rem; }
.live-view__logs p { color: var(--text-tertiary); font-size: 0.72rem; margin: 0 0 0.35rem; overflow-wrap: anywhere; }
.live-view__logs pre { background: var(--surface-inset); border: 1px solid var(--line); color: var(--status-success-text); font-size: 0.7rem; line-height: 1.6; margin: 0; max-height: 12rem; overflow: auto; padding: 0.6rem 0.7rem; white-space: pre; }
.live-view__log-error { color: var(--danger) !important; }
.live-view__placeholder { align-items: center; color: var(--text-tertiary); display: flex; font-size: 0.8rem; gap: 0.5rem; margin: 0; }
.live-view__report { background: var(--surface-raised); border: 1px solid var(--status-success-border); border-radius: 6px; min-width: 0; overflow-wrap: anywhere; padding: 1rem 1.2rem; }
.live-view__report--fallback { border-color: var(--status-waiting-border); }
.live-view__sim-badge { background: var(--status-waiting-bg); border: 1px solid var(--status-waiting-border); border-radius: 4px; color: var(--status-waiting-text); display: inline-block; font-size: 0.75rem; margin: 0.4rem 0 0; padding: 0.1rem 0.45rem; }
.live-view__metrics { display: grid; gap: 0.35rem; list-style: none; margin: 0.5rem 0 0; padding: 0; }
.live-view__metrics li { align-items: center; display: grid; font-size: 0.82rem; gap: 0.15rem 0.6rem; grid-template-columns: 88px minmax(0, 1fr); }
.live-view__metrics svg { grid-row: span 3; height: 28px; width: 88px; }
.live-view__metrics polyline { fill: none; stroke: var(--danger); stroke-width: 1.5; vector-effect: non-scaling-stroke; }
.live-view__metrics small { color: var(--text-tertiary); }
.live-view__metric-name { font-family: var(--font-mono, ui-monospace, monospace); overflow-wrap: anywhere; }
.live-view__report--draft { border-color: var(--status-running-border); }
.live-view__draft-label { align-items: center; color: var(--text-tertiary); display: flex; font-size: 0.85rem; gap: 0.4rem; margin: 0 0 0.6rem; }
.live-view__fallback-label { color: var(--status-waiting-text); font-size: 0.78rem; line-height: 1.6; margin: 0 0 0.8rem; }
.live-view__next { align-items: center; border: 1px solid var(--accent-border); display: flex; flex-wrap: wrap; gap: 0.4rem 1rem; padding: 0.8rem 1rem; }
.live-view__next a { align-items: center; color: var(--accent); display: inline-flex; font-size: 0.85rem; font-weight: 750; gap: 0.45rem; text-decoration: none; }
.live-view__next a:hover { text-shadow: 0 0 8px rgb(0 255 255 / 40%); }
.live-view__next small { color: var(--text-tertiary); font-size: 0.72rem; }
.live-view__timeline summary { color: var(--text-tertiary); cursor: pointer; font-size: 0.76rem; }
.live-view__timeline ol { display: grid; font-size: 0.72rem; gap: 0.3rem; list-style: none; margin: 0.6rem 0 0; padding: 0; }
.live-view__timeline li { color: var(--text-secondary); display: grid; gap: 0.7rem; grid-template-columns: 9.5rem minmax(0, 1fr); }
.live-view__timeline time { color: var(--text-tertiary); }
.live-view__spin { animation: live-spin 1s linear infinite; }
@keyframes live-spin { to { transform: rotate(360deg); } }
@media (max-width: 900px) {
  .live-view__layout { grid-template-columns: minmax(0, 1fr); }
  .live-view__control { position: static; }
  .live-view__timeline li { grid-template-columns: minmax(0, 1fr); gap: 0; }
}
@media (max-width: 760px) {
  .live-view { height: auto; overflow: visible; }
}
@media (prefers-reduced-motion: reduce) {
  .live-view__spin { animation: none; }
  .live-view__trigger, .live-view__progress span { transition: none; }
}
</style>
