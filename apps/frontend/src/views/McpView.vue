<script setup lang="ts">
import {
  Cable, CheckCircle2, MoreHorizontal, Plus, RefreshCw, Save, Search,
  Server, Trash2, TriangleAlert, Wrench
} from "lucide-vue-next";
import { computed, onMounted, reactive, ref, watch } from "vue";

import type { McpConnectionMutationRequest } from "@agent-py/api-contracts";

import AppLoadingState from "../components/AppLoadingState.vue";
import { useAuthStore } from "../stores/auth";
import { useMcpStore } from "../stores/mcp";

const mcp = useMcpStore();
const auth = useAuthStore();
const defaultDraft = (): McpConnectionMutationRequest => ({
  name: "", transport: "sse", url: "http://127.0.0.1:3100/sse",
  enabled: true, timeoutSeconds: 15, retries: 1
});
const draft = reactive<McpConnectionMutationRequest>(defaultDraft());
const baseline = ref("");
const connectionQuery = ref("");
const toolQuery = ref("");

const isNew = computed(() => mcp.selected === null);
const serializedDraft = computed(() => JSON.stringify(draft));
const isDirty = computed(() => serializedDraft.value !== baseline.value);
const isValid = computed(() => {
  if (draft.name.trim().length === 0 || draft.timeoutSeconds < 1 || draft.retries < 0) return false;
  try {
    const url = new URL(draft.url);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
});
const filteredConnections = computed(() => {
  const query = connectionQuery.value.trim().toLocaleLowerCase();
  if (query.length === 0) return mcp.connections;
  return mcp.connections.filter((connection) =>
    connection.name.toLocaleLowerCase().includes(query) || connection.url.toLocaleLowerCase().includes(query)
  );
});
const filteredTools = computed(() => {
  const tools = mcp.selected?.lastCheck?.tools ?? [];
  const query = toolQuery.value.trim().toLocaleLowerCase();
  if (query.length === 0) return tools;
  return tools.filter((tool) =>
    tool.name.toLocaleLowerCase().includes(query) || tool.description.toLocaleLowerCase().includes(query)
  );
});

watch(() => mcp.selected, (connection) => {
  if (connection === null) return;
  Object.assign(draft, {
    name: connection.name, transport: connection.transport, url: connection.url,
    enabled: connection.enabled, timeoutSeconds: connection.timeoutSeconds, retries: connection.retries
  });
  baseline.value = JSON.stringify(draft);
  toolQuery.value = "";
}, { immediate: true });

onMounted(() => { void mcp.initialize().catch(() => undefined); });

function confirmDiscard(): boolean {
  return !isDirty.value || window.confirm("当前修改尚未保存，确定要放弃吗？");
}
function newConnection(): void {
  if (!confirmDiscard()) return;
  mcp.select("");
  Object.assign(draft, defaultDraft());
  baseline.value = JSON.stringify(draft);
  toolQuery.value = "";
}
function selectConnection(connectionId: string): void {
  if (connectionId === mcp.selectedId || !confirmDiscard()) return;
  mcp.select(connectionId);
}
async function saveConnection(): Promise<void> {
  if (!isValid.value || !isDirty.value) return;
  if (isNew.value) await mcp.create(draft);
  else await mcp.update(draft);
  baseline.value = JSON.stringify(draft);
}
async function deleteConnection(): Promise<void> {
  const selected = mcp.selected;
  if (selected === null || !window.confirm(`确定删除“${selected.name}”吗？此操作无法撤销。`)) return;
  await mcp.remove(selected.id);
}
function run(operation: () => Promise<void>): void {
  void operation().catch(() => undefined);
}
</script>

<template>
  <section class="mcp-view" aria-label="MCP 连接管理">
    <AppLoadingState v-if="mcp.isLoading" label="正在加载 MCP 连接" />
    <div v-else class="mcp-view__workspace">
      <header class="mcp-view__header">
        <div>
          <p>Agent 工具来源</p>
          <h2>连接与工具</h2>
          <span>查看项目默认工具来源，并管理你自己的远程 MCP Server。</span>
        </div>
        <button v-if="!auth.isGuest" type="button" title="新建连接" @click="newConnection"><Plus :size="16" aria-hidden="true" />新建连接</button>
      </header>

      <section class="mcp-view__project-source" aria-label="项目默认工具来源">
        <span class="mcp-view__connection-icon"><Server :size="16" aria-hidden="true" /></span>
        <div><p>项目默认 · 只读</p><strong>AWS CloudWatch</strong><small>官方 AWS Labs MCP · stdio · eu-west-1 · /super-ai/demo</small></div>
        <span class="mcp-view__managed"><CheckCircle2 :size="14" aria-hidden="true" />后端托管</span>
      </section>

      <section class="mcp-view__project-source" aria-label="故障演练工具来源">
        <span class="mcp-view__connection-icon"><Server :size="16" aria-hidden="true" /></span>
        <div><p>故障演练专用 · 只读</p><strong>故障模拟器</strong><small>仓库内 FastMCP Server · stdio · query_service_logs / query_service_metrics · 数据按注入的故障实时生成</small></div>
        <span class="mcp-view__managed"><CheckCircle2 :size="14" aria-hidden="true" />后端托管</span>
      </section>

      <p v-if="auth.isGuest" class="mcp-view__guest-note" role="note">访客只读：两个项目来源由后端托管；新建、检查或修改自定义 MCP 连接需要所有者账号。</p>

      <section class="mcp-view__connections" aria-labelledby="mcp-connections-title">
        <header class="mcp-view__section-heading">
          <div><h3 id="mcp-connections-title">自定义远程连接</h3><span>{{ mcp.connections.length }} 个 Server</span></div>
          <label v-if="mcp.connections.length > 1" class="mcp-view__search">
            <Search :size="15" aria-hidden="true" />
            <input v-model="connectionQuery" type="search" placeholder="搜索名称或 URL" aria-label="搜索 MCP 连接" />
          </label>
        </header>
        <div class="mcp-view__list" aria-label="MCP 连接列表">
          <button v-for="connection in filteredConnections" :key="connection.id" type="button" :class="{ 'mcp-view__connection--active': mcp.selectedId === connection.id }" @click="selectConnection(connection.id)">
            <span class="mcp-view__connection-icon"><Server :size="16" aria-hidden="true" /></span>
            <span class="mcp-view__connection-copy"><strong>{{ connection.name }}</strong><small>{{ connection.transport === 'sse' ? 'SSE' : 'Streamable HTTP' }} · {{ connection.enabled ? '已启用' : '已停用' }}</small></span>
            <span v-if="connection.lastCheck?.ok" class="mcp-view__connection-status mcp-view__ok"><CheckCircle2 :size="14" aria-hidden="true" />正常</span>
            <span v-else-if="connection.lastCheck" class="mcp-view__connection-status mcp-view__bad"><TriangleAlert :size="14" aria-hidden="true" />异常</span>
            <span v-else class="mcp-view__connection-status">未检查</span>
          </button>
          <div v-if="mcp.connections.length === 0" class="mcp-view__list-empty"><Server :size="20" aria-hidden="true" /><span><strong>没有自定义连接</strong><small>AWS CloudWatch 项目来源仍会由后端加载。</small></span></div>
          <p v-else-if="filteredConnections.length === 0" class="mcp-view__no-results">没有匹配的连接。</p>
        </div>
      </section>

      <main v-if="!auth.isGuest" class="mcp-view__editor">
        <form @submit.prevent="run(saveConnection)">
          <header class="mcp-view__editor-heading">
            <div><p>{{ isNew ? '新建连接' : '连接配置' }}</p><h3>{{ draft.name || '未命名 MCP Server' }}</h3><span v-if="isDirty" class="mcp-view__unsaved">有未保存修改</span></div>
            <label class="mcp-view__toggle"><input v-model="draft.enabled" type="checkbox" /><span aria-hidden="true"></span><strong>{{ draft.enabled ? '已启用' : '已停用' }}</strong></label>
          </header>

          <section class="mcp-view__field-group" aria-labelledby="mcp-basic-title">
            <div class="mcp-view__field-group-heading"><h4 id="mcp-basic-title">基本信息</h4><p>用于识别 Server 并建立连接。</p></div>
            <div class="mcp-view__fields">
              <label><span>连接名称</span><input v-model.trim="draft.name" required maxlength="120" placeholder="例如：内部告警工具" /></label>
              <label><span>传输协议</span><select v-model="draft.transport"><option value="sse">SSE</option><option value="streamable_http">Streamable HTTP</option></select></label>
              <label class="mcp-view__url"><span>Server URL</span><input v-model.trim="draft.url" type="url" required maxlength="2048" placeholder="https://example.com/mcp" /></label>
            </div>
          </section>

          <section class="mcp-view__field-group" aria-labelledby="mcp-runtime-title">
            <div class="mcp-view__field-group-heading"><h4 id="mcp-runtime-title">运行策略</h4><p>控制单次工具调用的等待与失败重试。</p></div>
            <div class="mcp-view__fields mcp-view__fields--runtime">
              <label><span>超时时间</span><input v-model.number="draft.timeoutSeconds" type="number" min="1" max="300" required /><small>1–300 秒，建议 15 秒</small></label>
              <label><span>失败重试</span><input v-model.number="draft.retries" type="number" min="0" max="5" required /><small>0–5 次，避免放大慢请求</small></label>
            </div>
          </section>

          <section v-if="mcp.selected" class="mcp-view__health" aria-labelledby="mcp-health-title">
            <div><p>连接状态</p><h4 id="mcp-health-title"><template v-if="mcp.selected.lastCheck">{{ mcp.selected.lastCheck.ok ? '连接正常' : '连接异常' }}</template><template v-else>尚未检查</template></h4><span v-if="mcp.selected.lastCheck?.ok">最近检查发现 {{ mcp.selected.lastCheck.toolCount }} 个工具</span><span v-else-if="mcp.selected.lastCheck">{{ mcp.selected.lastCheck.error }}</span><span v-else>保存配置后检查 Server 是否可达并读取工具。</span></div>
            <button type="button" :disabled="mcp.checkingId === mcp.selected.id || isDirty" @click="run(() => mcp.check(mcp.selected!.id))"><RefreshCw :size="15" :class="{ spin: mcp.checkingId === mcp.selected.id }" aria-hidden="true" />{{ mcp.checkingId === mcp.selected.id ? '检查中' : isDirty ? '请先保存' : '检查连接' }}</button>
          </section>

          <div class="mcp-view__commands">
            <details v-if="mcp.selected" class="mcp-view__more"><summary aria-label="更多连接操作"><MoreHorizontal :size="18" aria-hidden="true" /></summary><button type="button" class="mcp-view__delete" :disabled="mcp.isSaving" @click="run(deleteConnection)"><Trash2 :size="15" aria-hidden="true" />删除连接</button></details>
            <span class="mcp-view__save-hint">{{ isDirty ? '修改尚未保存' : '所有修改已保存' }}</span>
            <button type="submit" class="mcp-view__save" :disabled="mcp.isSaving || !isDirty || !isValid"><Save :size="15" aria-hidden="true" />{{ mcp.isSaving ? '保存中' : '保存连接' }}</button>
          </div>
        </form>

        <section class="mcp-view__inspection" aria-labelledby="mcp-tools-title">
          <header class="mcp-view__inspection-heading">
            <div><p>工具发现</p><h3 id="mcp-tools-title">Server 能力</h3><span>{{ mcp.selected?.lastCheck?.ok ? `最近一次检查返回 ${mcp.selected.lastCheck.toolCount} 个工具。` : '检查连接后，这里会展示 Server 真实返回的工具。' }}</span></div>
            <label v-if="(mcp.selected?.lastCheck?.tools.length ?? 0) > 5" class="mcp-view__search"><Search :size="15" aria-hidden="true" /><input v-model="toolQuery" type="search" placeholder="搜索工具" aria-label="搜索 MCP 工具" /></label>
          </header>
          <ul v-if="filteredTools.length">
            <li v-for="tool in filteredTools" :key="tool.name">
              <Wrench :size="15" aria-hidden="true" />
              <details>
                <summary><strong>{{ tool.name }}</strong><small>{{ tool.description || '无工具说明' }}</small></summary>
                <p v-if="tool.description">{{ tool.description }}</p>
              </details>
            </li>
          </ul>
          <div v-else class="mcp-view__tools-empty"><Cable :size="20" aria-hidden="true" /><span><strong>{{ toolQuery ? '没有匹配的工具' : '等待工具发现' }}</strong><small>{{ toolQuery ? '尝试其他关键词。' : '选择并检查一个已保存的连接。' }}</small></span></div>
        </section>
      </main>
    </div>
  </section>
</template>

<style scoped>
.mcp-view__guest-note { border: 1px solid var(--status-waiting-border); box-sizing: border-box; color: var(--status-waiting-text); font-size: 0.74rem; line-height: 1.6; margin: 0.75rem auto; max-width: 68rem; padding: 0.6rem clamp(1rem, 3vw, 2rem); width: 100%; }
.mcp-view { background: var(--surface-raised); display: block; height: 100%; min-height: 0; overflow-x: hidden; overflow-y: auto; }
.mcp-view__workspace { background: var(--surface-raised); display: block; min-height: 100%; overflow: visible; }
.mcp-view__header, .mcp-view__project-source, .mcp-view__connections, .mcp-view__editor > form, .mcp-view__inspection { margin-inline: auto; max-width: 68rem; width: 100%; }
.mcp-view__header { align-items: end; display: flex; justify-content: space-between; padding: 1.5rem clamp(1rem, 3vw, 2rem) 1.25rem; }
.mcp-view__header p, .mcp-view__editor-heading p, .mcp-view__health p, .mcp-view__inspection-heading p { color: var(--text-tertiary); font-size: 0.7rem; font-weight: 700; letter-spacing: 0.04em; margin: 0 0 0.25rem; text-transform: uppercase; }
.mcp-view__header h2 { font-size: 1.25rem; margin: 0; }.mcp-view__header span, .mcp-view__inspection-heading span { color: var(--text-secondary); display: block; font-size: 0.78rem; margin-top: 0.35rem; }
.mcp-view__project-source { align-items: center; border-block: 1px solid var(--line); display: grid; gap: 0.7rem; grid-template-columns: auto minmax(0, 1fr) auto; padding: 0.9rem clamp(1rem, 3vw, 2rem); }.mcp-view__project-source p { color: var(--text-tertiary); font-size: 0.66rem; font-weight: 700; margin: 0 0 0.18rem; text-transform: uppercase; }.mcp-view__project-source strong, .mcp-view__project-source small { display: block; }.mcp-view__project-source strong { font-size: 0.82rem; }.mcp-view__project-source small { color: var(--text-tertiary); font-size: 0.68rem; margin-top: 0.16rem; }.mcp-view__managed { align-items: center; color: var(--status-success-text); display: inline-flex; font-size: 0.68rem; gap: 0.28rem; }
.mcp-view__header > button, .mcp-view__commands button, .mcp-view__health button { align-items: center; border: 1px solid var(--line-strong); display: inline-flex; font-size: 0.76rem; font-weight: 650; gap: 0.35rem; min-height: 2.25rem; padding: 0 0.75rem; }
.mcp-view__connections { border-block: 1px solid var(--line); padding: 1rem clamp(1rem, 3vw, 2rem); }
.mcp-view__section-heading, .mcp-view__inspection-heading { align-items: center; display: flex; gap: 1rem; justify-content: space-between; }.mcp-view__section-heading > div { align-items: baseline; display: flex; gap: 0.55rem; }.mcp-view__section-heading h3, .mcp-view__inspection-heading h3 { font-size: 0.9rem; margin: 0; }.mcp-view__section-heading span { color: var(--text-tertiary); font-size: 0.7rem; }
.mcp-view__search { align-items: center; background: var(--surface); border: 1px solid var(--line-strong); display: flex; gap: 0.4rem; min-height: 2.2rem; padding: 0 0.55rem; width: min(18rem, 100%); }.mcp-view__search:focus-within { border-color: var(--accent-border); box-shadow: 0 0 0 2px var(--accent-soft); }.mcp-view__search input { background: transparent; border: 0; color: var(--text-primary); min-width: 0; outline: 0; padding: 0; width: 100%; }
.mcp-view__list { display: grid; gap: 0.45rem; margin-top: 0.75rem; }.mcp-view__list > button { align-items: center; border: 1px solid var(--line); display: grid; gap: 0.65rem; grid-template-columns: auto minmax(0, 1fr) auto; min-height: 3.5rem; padding: 0.55rem 0.7rem; text-align: left; }.mcp-view__list > button:hover { background: var(--surface); border-color: var(--line-strong); }.mcp-view__connection--active { background: var(--accent-soft) !important; border-color: var(--accent-border) !important; color: var(--accent-strong); }
.mcp-view__connection-icon { align-items: center; background: var(--surface); border: 1px solid var(--line); display: inline-flex; height: 2rem; justify-content: center; width: 2rem; }.mcp-view__connection-copy { min-width: 0; }.mcp-view__connection-copy strong, .mcp-view__connection-copy small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.mcp-view__connection-copy strong { font-size: 0.8rem; }.mcp-view__connection-copy small { color: var(--text-tertiary); font-size: 0.68rem; margin-top: 0.15rem; }
.mcp-view__connection-status { align-items: center; color: var(--text-tertiary); display: inline-flex; font-size: 0.68rem; gap: 0.25rem; }.mcp-view__ok { color: var(--status-success-text); }.mcp-view__bad { color: var(--status-danger-text); }
.mcp-view__list-empty, .mcp-view__tools-empty { align-items: center; color: var(--text-tertiary); display: flex; gap: 0.65rem; min-height: 5rem; }.mcp-view__list-empty strong, .mcp-view__list-empty small, .mcp-view__tools-empty strong, .mcp-view__tools-empty small { display: block; }.mcp-view__list-empty strong, .mcp-view__tools-empty strong { color: var(--text-secondary); font-size: 0.78rem; }.mcp-view__list-empty small, .mcp-view__tools-empty small { font-size: 0.7rem; margin-top: 0.15rem; }.mcp-view__no-results { color: var(--text-tertiary); font-size: 0.75rem; }
.mcp-view__editor { border-bottom: 1px solid var(--line); display: block; min-height: 0; overflow: visible; }.mcp-view__editor > form { padding: 1.5rem clamp(1rem, 3vw, 2rem) 0; }
.mcp-view__editor-heading { align-items: center; display: flex; justify-content: space-between; }.mcp-view__editor-heading h3 { display: inline; font-size: 1.05rem; margin: 0; }.mcp-view__unsaved { color: var(--text-tertiary); font-size: 0.68rem; margin-left: 0.55rem; }
.mcp-view__toggle { align-items: center; cursor: pointer; display: grid; gap: 0.45rem; grid-template-columns: auto auto; }.mcp-view__toggle input { height: 1px; opacity: 0; position: absolute; width: 1px; }.mcp-view__toggle > span { background: var(--surface-inset); border: 1px solid var(--line-strong); border-radius: 2px; height: 1.25rem; position: relative; transition: background 120ms ease, border-color 120ms ease, box-shadow 120ms ease; width: 2.2rem; }.mcp-view__toggle > span::after { background: var(--text-tertiary); border-radius: 1px; content: ""; height: 0.82rem; left: 0.18rem; position: absolute; top: 0.16rem; transition: background 120ms ease, box-shadow 120ms ease, transform 120ms ease; width: 0.82rem; }.mcp-view__toggle input:checked + span { border-color: var(--success); box-shadow: 0 0 10px rgb(0 255 157 / 28%); }.mcp-view__toggle input:checked + span::after { background: var(--success); box-shadow: 0 0 8px rgb(0 255 157 / 55%); transform: translateX(0.95rem); }.mcp-view__toggle input:focus-visible + span { outline: 1px solid var(--accent); outline-offset: 2px; }.mcp-view__toggle strong { color: var(--text-secondary); font-size: 0.72rem; }
.mcp-view__field-group { border-top: 1px solid var(--line); margin-top: 1.4rem; padding-top: 1.25rem; }.mcp-view__field-group-heading h4 { color: var(--text-primary); font-size: 0.82rem; margin: 0; }.mcp-view__field-group-heading p { color: var(--text-tertiary); font-size: 0.7rem; margin: 0.35rem 0 0; }
.mcp-view__fields { display: grid; gap: 0.9rem; grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 1rem; }.mcp-view__fields--runtime { max-width: 34rem; }.mcp-view__fields label { color: var(--text-secondary); display: grid; font-size: 0.72rem; font-weight: 650; gap: 0.4rem; }.mcp-view__fields label small { color: var(--text-tertiary); font-size: 0.66rem; font-weight: 400; }.mcp-view__url { grid-column: 1 / -1; }
.mcp-view__fields input, .mcp-view__fields select { background: var(--surface); border: 1px solid var(--line-strong); color: var(--text-primary); font: inherit; min-height: 2.45rem; padding: 0 0.65rem; width: 100%; }.mcp-view__fields input:focus, .mcp-view__fields select:focus { border-color: var(--accent-border); outline: 2px solid var(--accent-soft); }
.mcp-view__health { align-items: center; background: var(--surface); border: 1px solid var(--line); display: flex; justify-content: space-between; margin-top: 1.4rem; padding: 0.9rem; }.mcp-view__health h4 { font-size: 0.82rem; margin: 0; }.mcp-view__health span { color: var(--text-tertiary); display: block; font-size: 0.68rem; margin-top: 0.2rem; }.mcp-view__health button:disabled { cursor: not-allowed; opacity: 0.55; }
.mcp-view__commands { align-items: center; background: var(--surface-raised); border-top: 1px solid var(--line); display: flex; gap: 0.6rem; justify-content: flex-end; margin-top: 1.5rem; min-height: 4.2rem; padding: 0.75rem 0; position: static; }.mcp-view__save-hint { color: var(--text-tertiary); font-size: 0.68rem; }.mcp-view__save { background: var(--accent-strong); border-color: var(--accent-strong) !important; color: var(--on-accent); }.mcp-view__save:disabled { cursor: not-allowed; opacity: 0.45; }
.mcp-view__more { margin-right: auto; position: relative; }.mcp-view__more summary { align-items: center; border: 1px solid var(--line-strong); cursor: pointer; display: flex; height: 2.25rem; justify-content: center; list-style: none; width: 2.25rem; }.mcp-view__more summary::-webkit-details-marker { display: none; }.mcp-view__more button { background: var(--surface-raised); box-shadow: var(--shadow-raised-sm); color: var(--status-danger-text); left: 0; min-width: 8rem; position: absolute; top: calc(100% + 0.35rem); z-index: 5; }
.mcp-view__inspection { padding: 1.5rem clamp(1rem, 3vw, 2rem) 2.5rem; }.mcp-view__inspection ul { display: grid; gap: 0; list-style: none; margin: 1rem 0 0; max-height: 28rem; overflow-y: auto; padding: 0; }.mcp-view__inspection li { align-items: start; border-bottom: 1px solid var(--line); display: grid; gap: 0.55rem; grid-template-columns: auto minmax(0, 1fr); padding: 0.75rem 0; }.mcp-view__inspection li details { min-width: 0; }.mcp-view__inspection li summary { cursor: pointer; list-style: none; }.mcp-view__inspection li summary::-webkit-details-marker { display: none; }.mcp-view__inspection li strong, .mcp-view__inspection li small { display: block; overflow-wrap: anywhere; }.mcp-view__inspection li strong { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.76rem; }.mcp-view__inspection li small { -webkit-box-orient: vertical; -webkit-line-clamp: 2; color: var(--text-tertiary); display: -webkit-box; font-size: 0.7rem; line-height: 1.5; margin-top: 0.2rem; overflow: hidden; }.mcp-view__inspection li details[open] small { display: none; }.mcp-view__inspection li details > p { color: var(--text-secondary); font-size: 0.7rem; line-height: 1.6; margin: 0.65rem 0 0; overflow-wrap: anywhere; white-space: pre-wrap; }
.spin { animation: spin 0.8s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }
@media (max-width: 760px) { .mcp-view { height: auto; overflow: visible; }.mcp-view__header, .mcp-view__section-heading, .mcp-view__inspection-heading, .mcp-view__health { align-items: stretch; flex-direction: column; }.mcp-view__header { gap: 1rem; }.mcp-view__header > button { align-self: flex-start; }.mcp-view__search { width: 100%; }.mcp-view__fields { grid-template-columns: minmax(0, 1fr); }.mcp-view__url { grid-column: auto; }.mcp-view__connection-status { font-size: 0; }.mcp-view__save-hint { display: none; } }
@media (prefers-reduced-motion: reduce) { .mcp-view__toggle > span, .mcp-view__toggle > span::after { transition: none; } }
</style>
