<script setup lang="ts">
import { BellRing, FileText, FlaskConical, History, Square, Zap } from "lucide-vue-next";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import ActiveAlertList from "../components/ActiveAlertList.vue";
import AiopsCaseLibrary from "../components/AiopsCaseLibrary.vue";
import AiopsEvidenceChain from "../components/AiopsEvidenceChain.vue";
import AiopsHistory from "../components/AiopsHistory.vue";
import AiopsRunForm from "../components/AiopsRunForm.vue";
import AiopsReportPanel, { type AiopsReportDisplay } from "../components/AiopsReportPanel.vue";
import AiopsTimeline from "../components/AiopsTimeline.vue";
import AppErrorState from "../components/AppErrorState.vue";
import AppLoadingState from "../components/AppLoadingState.vue";
import AsyncStatusBadge from "../components/AsyncStatusBadge.vue";
import { useAiopsStore } from "../stores/aiops";
import { useAuthStore } from "../stores/auth";

type EntryMode = "describe" | "alerts" | "history";

const aiops = useAiopsStore();
const auth = useAuthStore();
const route = useRoute();
const router = useRouter();
const isGuest = computed(() => auth.isGuest);
const entryMode = ref<EntryMode>(auth.isGuest ? "history" : "describe");
const isDrillTask = computed(() => aiops.activeTask?.origin === "live-drill");
const drillLabel = computed(() => (aiops.activeTask?.simulated === true ? "故障演练 · 模拟数据" : "故障演练"));
const hasActiveTask = computed(() => aiops.activeTask !== null);
const activeStatus = computed(() => (aiops.isRunning ? "running" : aiops.activeTask?.status ?? "ready"));
const evidenceCount = computed(() => aiops.evidenceChain?.evidence.length ?? 0);
const toolCallCount = computed(() => aiops.evidenceChain?.toolCalls.length ?? 0);
const isEffectivelyRunning = computed(() => aiops.isRunning || aiops.activeTask?.status === "running");
const activeReport = computed<AiopsReportDisplay | null>(() => {
  const reports = aiops.evidenceChain?.reports ?? [];
  const persisted = reports[reports.length - 1];
  if (persisted) return persisted;
  for (let index = aiops.liveEvents.length - 1; index >= 0; index -= 1) {
    const event = aiops.liveEvents[index];
    if (event?.type === "report") return { ...event.report, createdAt: event.timestamp };
  }
  return null;
});
const lifecycleText = computed(() => {
  if (isEffectivelyRunning.value) return "执行中";
  if (aiops.activeTask?.status === "accepted") return "等待开始";
  if (aiops.activeTask?.status === "failed") return "诊断失败";
  if (aiops.activeTask?.status === "succeeded") return "诊断完成";
  return "尚未开始";
});

onMounted(() => { void openWorkspace().catch(() => undefined); });

async function openWorkspace(): Promise<void> {
  await aiops.initialize({ includeAlerts: !isGuest.value });
  const diagnosticId = route.query.diagnosticId;
  if (typeof diagnosticId === "string" && diagnosticId.length > 0) {
    await aiops.selectDiagnostic(diagnosticId);
  }
}
onBeforeUnmount(() => { aiops.reset(); });

function run(operation: () => Promise<unknown>): void {
  void operation().catch(() => undefined);
}
function selectDiagnostic(id: string): void {
  run(() => aiops.selectDiagnostic(id));
}
function startDiagnostic(query: string, alert: Record<string, unknown> | undefined): void {
  run(() => aiops.runDiagnostic(query, alert));
}
function diagnoseAlert(alert: Parameters<typeof aiops.diagnoseAlert>[0]): void {
  run(() => aiops.diagnoseAlert(alert));
}
function openCaseDocument(documentId: string): void {
  void router.push({ name: "knowledge", query: { documentId } });
}
</script>

<template>
  <section class="aiops-view" aria-label="智能诊断工作区">
    <AppLoadingState v-if="aiops.isLoading && aiops.history.length === 0" label="正在加载诊断工作区" />
    <AppErrorState v-else-if="aiops.errorMessage && aiops.history.length === 0" :can-retry="true" :message="aiops.errorMessage" @retry="run(openWorkspace)" />
    <div v-else class="aiops-view__console">
      <details class="aiops-view__entry" :open="hasActiveTask ? undefined : true">
        <summary v-show="hasActiveTask" class="aiops-view__entry-summary"><span>{{ isGuest ? '切换演练诊断' : '发起新诊断或切换任务' }}</span><small>{{ isGuest ? '打开你触发过的故障演练' : '描述问题、选择告警或打开历史诊断' }}</small></summary>
        <div class="aiops-view__entry-content">
        <header class="aiops-view__entry-heading">
          <div>
            <p>{{ isGuest ? '演练诊断' : hasActiveTask ? '新的诊断' : '开始诊断' }}</p>
            <h2 id="aiops-entry-title">{{ isGuest ? '回看你触发的故障演练' : hasActiveTask ? '补充问题或切换诊断来源' : '从一个运行信号开始' }}</h2>
            <span>{{ isGuest ? '每次演练都是一条真实的诊断任务：时间线、工具调用、证据与报告都会保留。' : hasActiveTask ? '当前任务会保留在下方，发起新任务后自动切换。' : '描述现象、选择活跃告警，或重新打开历史诊断。' }}</span>
          </div>
        </header>

        <p v-if="isGuest" class="aiops-view__guest-note" role="note">
          <FlaskConical :size="15" aria-hidden="true" />
          <span>访客可以查看自己触发的故障演练诊断。发起工作台诊断会查询真实 AWS CloudWatch，需要所有者账号。</span>
          <RouterLink to="/drill"><Zap :size="14" aria-hidden="true" />去触发一次演练</RouterLink>
        </p>
        <nav class="aiops-view__entry-tabs" aria-label="诊断来源" role="tablist">
          <button v-if="!isGuest" type="button" role="tab" :aria-selected="entryMode === 'describe'" :class="{ 'is-active': entryMode === 'describe' }" @click="entryMode = 'describe'"><FileText :size="15" aria-hidden="true" />描述问题</button>
          <button v-if="!isGuest" type="button" role="tab" :aria-selected="entryMode === 'alerts'" :class="{ 'is-active': entryMode === 'alerts' }" @click="entryMode = 'alerts'"><BellRing :size="15" aria-hidden="true" />选择告警<span v-if="aiops.activeAlerts.length">{{ aiops.activeAlerts.length }}</span></button>
          <button type="button" role="tab" :aria-selected="entryMode === 'history'" :class="{ 'is-active': entryMode === 'history' }" @click="entryMode = 'history'"><History :size="15" aria-hidden="true" />历史诊断<span v-if="aiops.history.length">{{ aiops.history.length }}</span></button>
        </nav>

        <div class="aiops-view__entry-panel" role="tabpanel">
          <AiopsRunForm v-if="entryMode === 'describe'" :disabled="aiops.isLoading" :is-running="aiops.isRunning" @cancel="run(aiops.cancelActive)" @run="startDiagnostic" />
          <ActiveAlertList v-else-if="entryMode === 'alerts'" :alerts="aiops.activeAlerts" :error-message="aiops.alertsErrorMessage" :is-loading="aiops.alertsLoading" @diagnose="diagnoseAlert" @refresh="run(aiops.refreshActiveAlerts)" />
          <AiopsHistory v-else :active-diagnostic-id="aiops.activeDiagnosticId" :tasks="aiops.history" @select="selectDiagnostic" />
        </div>
        </div>
      </details>

      <main v-if="hasActiveTask" class="aiops-view__task" aria-label="当前诊断">
        <header class="aiops-view__task-heading">
          <div><p>当前诊断<span v-if="isDrillTask" class="aiops-view__drill-badge" title="日志与指标由故障模拟器生成，不进入知识库">{{ drillLabel }}</span></p><h2>{{ aiops.activeTask?.query }}</h2></div>
          <div class="aiops-view__task-actions"><AsyncStatusBadge :status="activeStatus" :detail="lifecycleText" /><button v-if="isEffectivelyRunning && !isDrillTask" type="button" @click="run(aiops.cancelActive)"><Square :size="13" aria-hidden="true" />取消诊断</button></div>
        </header>

        <section class="aiops-view__status-strip" aria-label="诊断状态概览">
          <strong>{{ lifecycleText }}</strong>
          <span>{{ aiops.liveEvents.length }} 个事件</span>
          <span>{{ evidenceCount }} 条证据</span>
          <span>{{ toolCallCount }} 次工具调用</span>
        </section>

        <AiopsTimeline :events="aiops.liveEvents" :is-running="isEffectivelyRunning" />
        <AiopsReportPanel :has-task="true" :is-running="isEffectivelyRunning" :report="activeReport" :task-failed="aiops.activeTask?.status === 'failed'" />

        <details v-if="aiops.evidenceChain" class="aiops-view__details">
          <summary>查看执行链与工具结果</summary>
          <AiopsEvidenceChain :chain="aiops.evidenceChain" />
        </details>
        <details v-if="aiops.diagnosticCases.length" class="aiops-view__details">
          <summary>相关历史案例（{{ aiops.diagnosticCases.length }}）</summary>
          <AiopsCaseLibrary :cases="aiops.diagnosticCases" @open-document="openCaseDocument" @select="selectDiagnostic" />
        </details>
      </main>

      <section v-else class="aiops-view__start-note" aria-label="诊断说明">
        <strong>诊断开始后会发生什么？</strong>
        <ol><li>规划需要验证的问题</li><li>检索知识并调用真实工具</li><li>汇总证据、标记不确定性</li><li>生成诊断报告和处理建议</li></ol>
      </section>
    </div>
  </section>
</template>

<style scoped>
.aiops-view { background: var(--surface-raised); display: block; height: 100%; min-height: 0; overflow-x: hidden; overflow-y: auto; }
.aiops-view__console { display: block; margin: 0 auto; max-width: 70rem; min-height: 0; overflow: visible; width: 100%; }
.aiops-view__entry { padding: 0 clamp(1rem, 3vw, 2rem); }.aiops-view__entry-content { padding: 1.5rem 0; }.aiops-view__entry-summary { align-items: center; cursor: pointer; display: flex; gap: 0.6rem; justify-content: space-between; list-style: none; min-height: 3.5rem; }.aiops-view__entry-summary::-webkit-details-marker { display: none; }.aiops-view__entry-summary span { color: var(--text-secondary); font-size: 0.75rem; font-weight: 700; }.aiops-view__entry-summary small { color: var(--text-tertiary); font-size: 0.66rem; }.aiops-view__entry[open] .aiops-view__entry-summary { border-bottom: 1px solid var(--line); }.aiops-view__entry-heading { align-items: end; display: flex; justify-content: space-between; }.aiops-view__entry-heading p, .aiops-view__task-heading p { color: var(--text-tertiary); font-size: 0.68rem; font-weight: 700; letter-spacing: 0.04em; margin: 0 0 0.3rem; text-transform: uppercase; }.aiops-view__entry-heading h2, .aiops-view__task-heading h2 { color: var(--text-primary); font-size: 1.15rem; margin: 0; }.aiops-view__entry-heading span { color: var(--text-secondary); display: block; font-size: 0.76rem; margin-top: 0.35rem; }
.aiops-view__guest-note { align-items: center; border: 1px solid var(--status-waiting-border); color: var(--status-waiting-text); display: flex; flex-wrap: wrap; font-size: 0.74rem; gap: 0.5rem 0.75rem; line-height: 1.6; margin: 1rem 0 0; padding: 0.65rem 0.8rem; }.aiops-view__guest-note span { flex: 1 1 18rem; }.aiops-view__guest-note a { align-items: center; color: var(--accent); display: inline-flex; font-weight: 700; gap: 0.3rem; text-decoration: none; }
.aiops-view__drill-badge { border: 1px solid var(--status-waiting-border); color: var(--status-waiting-text); font-size: 0.62rem; letter-spacing: 0; margin-left: 0.5rem; padding: 0.05rem 0.35rem; text-transform: none; }
.aiops-view__entry-tabs { border-bottom: 1px solid var(--line); display: flex; gap: 0.2rem; margin-top: 1.4rem; }.aiops-view__entry-tabs button { align-items: center; border-bottom: 2px solid transparent; color: var(--text-tertiary); display: inline-flex; font-size: 0.74rem; gap: 0.35rem; min-height: 2.5rem; padding: 0 0.65rem; }.aiops-view__entry-tabs button:hover { color: var(--text-primary); }.aiops-view__entry-tabs button.is-active { border-bottom-color: var(--accent-strong); color: var(--accent-strong); font-weight: 700; }.aiops-view__entry-tabs button > span { align-items: center; background: var(--surface-inset); border-radius: 999px; display: inline-flex; font-size: 0.62rem; height: 1rem; justify-content: center; min-width: 1rem; padding: 0 0.25rem; }
.aiops-view__entry-panel { max-width: 55rem; }.aiops-view__entry-panel :deep(.aiops-run-form) { padding: 1.25rem 0 0; }.aiops-view__entry-panel :deep(.active-alert-list), .aiops-view__entry-panel :deep(.aiops-history) { border: 0; }.aiops-view__entry-panel :deep(.active-alert-list > header), .aiops-view__entry-panel :deep(.aiops-history > header) { padding-inline: 0; }.aiops-view__entry-panel :deep(.active-alert-list__empty), .aiops-view__entry-panel :deep(.aiops-history__empty) { margin-inline: 0; }
.aiops-view__task { border-top: 1px solid var(--line); padding: 1.5rem clamp(1rem, 3vw, 2rem) 2.5rem; }.aiops-view__task-heading { align-items: center; display: flex; gap: 1rem; justify-content: space-between; }.aiops-view__task-heading h2 { max-width: 44rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.aiops-view__task-actions { align-items: center; display: flex; gap: 0.55rem; }.aiops-view__task-actions button { align-items: center; border: 1px solid var(--line-strong); color: var(--status-danger-text); display: inline-flex; font-size: 0.68rem; gap: 0.3rem; min-height: 2rem; padding: 0 0.55rem; }
.aiops-view__status-strip { align-items: center; background: var(--surface); border: 1px solid var(--line); display: flex; flex-wrap: wrap; gap: 0.35rem 1.1rem; margin-top: 1rem; min-height: 3rem; padding: 0.65rem 0.8rem; }.aiops-view__status-strip strong { font-size: 0.75rem; }.aiops-view__status-strip span { color: var(--text-tertiary); font-size: 0.68rem; }
.aiops-view__task :deep(.aiops-timeline), .aiops-view__task :deep(.aiops-report) { border-bottom: 0; padding-inline: 0; }.aiops-view__task :deep(.aiops-timeline) { border-bottom: 1px solid var(--line); overflow: visible; }.aiops-view__task :deep(.aiops-report__document) { max-height: 44rem; min-height: 20rem; }.aiops-view__details { border-top: 1px solid var(--line); padding: 0.9rem 0; }.aiops-view__details > summary { color: var(--text-secondary); cursor: pointer; font-size: 0.76rem; font-weight: 700; list-style: none; }.aiops-view__details > summary::-webkit-details-marker { display: none; }.aiops-view__details :deep(.aiops-execution), .aiops-view__details :deep(.aiops-case-library) { padding-inline: 0; }
.aiops-view__start-note { border-top: 1px solid var(--line); color: var(--text-tertiary); margin: 0 clamp(1rem, 3vw, 2rem); padding: 1.2rem 0 2.5rem; }.aiops-view__start-note strong { color: var(--text-secondary); font-size: 0.75rem; }.aiops-view__start-note ol { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; list-style-position: inside; margin: 0.65rem 0 0; padding: 0; }.aiops-view__start-note li { font-size: 0.7rem; }
@media (max-width: 700px) { .aiops-view { height: auto; min-height: 100%; overflow: visible; }.aiops-view__entry, .aiops-view__task { padding-inline: 1rem; }.aiops-view__entry-summary { align-items: flex-start; flex-direction: column; gap: 0.2rem; justify-content: center; }.aiops-view__entry-tabs { overflow-x: auto; }.aiops-view__entry-tabs button { flex: 0 0 auto; }.aiops-view__task-heading { align-items: flex-start; flex-direction: column; }.aiops-view__task-heading h2 { max-width: 100%; white-space: normal; }.aiops-view__start-note ol { display: grid; }.aiops-view__task :deep(.aiops-report__document) { max-height: none; min-height: 0; } }
</style>
