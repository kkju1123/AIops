<script setup lang="ts">
import { Play, Square } from "lucide-vue-next";
import { ref } from "vue";

const emit = defineEmits<{ cancel: []; run: [query: string, alert: Record<string, unknown> | undefined] }>();
defineProps<{ readonly disabled: boolean; readonly isRunning: boolean }>();

const query = ref("");
const alertText = ref("");
const service = ref("");
const severity = ref("");
const environment = ref("");
const validationMessage = ref<string | null>(null);

function submit(): void {
  const trimmedQuery = query.value.trim();
  if (trimmedQuery.length === 0) {
    validationMessage.value = "请描述需要排查的运行信号。";
    return;
  }
  let alert: Record<string, unknown> | undefined;
  if (alertText.value.trim().length > 0) {
    try {
      const parsed: unknown = JSON.parse(alertText.value);
      if (parsed === null || Array.isArray(parsed) || typeof parsed !== "object") {
        throw new Error();
      }
      alert = parsed as Record<string, unknown>;
    } catch {
      validationMessage.value = "告警上下文必须是有效的 JSON 对象。";
      return;
    }
  }
  const structuredContext: Record<string, unknown> = {};
  if (service.value.trim()) structuredContext.service = service.value.trim();
  if (severity.value) structuredContext.severity = severity.value;
  if (environment.value.trim()) structuredContext.environment = environment.value.trim();
  if (Object.keys(structuredContext).length > 0) alert = { ...(alert ?? {}), ...structuredContext };
  validationMessage.value = null;
  emit("run", trimmedQuery, alert);
}
</script>

<template>
  <form class="aiops-run-form" @submit.prevent="submit">
    <div class="aiops-run-form__header"><div><p>问题描述</p><h2>告诉系统发生了什么</h2></div><span v-if="isRunning" role="status">诊断执行中</span></div>
    <label>运行现象<textarea v-model="query" :disabled="disabled || isRunning" aria-label="诊断问题" placeholder="例如：生产环境 checkout API 从 14:20 开始 P95 延迟升至 3 秒，刚完成版本发布。" rows="3" /></label>
    <div class="aiops-run-form__context" aria-label="补充上下文">
      <label>服务名称 <span>可选</span><input v-model="service" :disabled="disabled || isRunning" placeholder="checkout" /></label>
      <label>严重程度 <span>可选</span><select v-model="severity" :disabled="disabled || isRunning"><option value="">未指定</option><option value="critical">严重</option><option value="high">高</option><option value="warning">警告</option><option value="info">信息</option></select></label>
      <label>运行环境 <span>可选</span><input v-model="environment" :disabled="disabled || isRunning" placeholder="production" /></label>
    </div>
    <details class="aiops-run-form__advanced">
      <summary>高级：添加 JSON 上下文</summary>
      <label><span>用于补充自定义字段，必须是有效的 JSON 对象。</span><textarea v-model="alertText" :disabled="disabled || isRunning" aria-label="告警上下文" placeholder='{"region":"ap-guangzhou","traceId":"..."}' rows="3" /></label>
    </details>
    <p v-if="validationMessage" class="aiops-run-form__error" role="alert">{{ validationMessage }}</p>
    <div class="aiops-run-form__commands"><button :disabled="disabled || isRunning" type="submit"><Play :size="16" aria-hidden="true" />{{ isRunning ? "诊断执行中" : "开始诊断" }}</button><button v-if="isRunning" class="aiops-run-form__cancel" type="button" @click="emit('cancel')"><Square :size="14" aria-hidden="true" />取消任务</button></div>
  </form>
</template>

<style scoped>
.aiops-run-form { background: var(--surface-raised); display: grid; gap: 0.9rem; padding: 1.2rem; }
.aiops-run-form__header { align-items: center; display: flex; gap: 1rem; justify-content: space-between; }
.aiops-run-form__header p { color: var(--text-tertiary); font-size: 0.7rem; font-weight: 700; margin: 0 0 0.3rem; }
h2 { font-size: 1rem; font-weight: 680; margin: 0; }
.aiops-run-form__header span { color: var(--accent-strong); font-size: 0.76rem; font-weight: 650; }
label { color: var(--text-secondary); display: grid; font-size: 0.74rem; font-weight: 650; gap: 0.4rem; }
label > span { color: var(--text-tertiary); font-weight: 500; }
textarea, input, select { background: var(--surface); border: 1px solid var(--line-strong); color: var(--text-primary); line-height: 1.5; min-height: 2.4rem; padding: 0.55rem 0.6rem; }
textarea { resize: vertical; }textarea:focus, input:focus, select:focus { border-color: var(--accent); outline: 2px solid var(--accent-focus); }
.aiops-run-form__context { display: grid; gap: 0.75rem; grid-template-columns: repeat(3, minmax(0, 1fr)); }.aiops-run-form__context label > span { font-size: 0.64rem; margin-left: 0.25rem; }
.aiops-run-form__advanced { border-top: 1px solid var(--line); padding-top: 0.75rem; }.aiops-run-form__advanced summary { color: var(--text-tertiary); cursor: pointer; font-size: 0.7rem; list-style: none; }.aiops-run-form__advanced summary::-webkit-details-marker { display: none; }.aiops-run-form__advanced label { margin-top: 0.7rem; }
button { align-items: center; background: var(--accent); color: var(--on-accent); display: inline-flex; font-size: 0.78rem; font-weight: 800; gap: 0.4rem; justify-self: start; min-height: 2.5rem; padding: 0 0.8rem; }
button:hover:not(:disabled) { background: var(--accent-strong); }
button:disabled { cursor: not-allowed; opacity: 0.6; }
.aiops-run-form__commands { display: flex; gap: 0.5rem; }.aiops-run-form__cancel { background: transparent; border: 1px solid var(--line-strong); color: var(--status-danger-text); }.aiops-run-form__cancel:hover:not(:disabled) { background: var(--status-danger-bg); }
.aiops-run-form__error { color: var(--danger); font-size: 0.8rem; margin: 0; }
@media (max-width: 640px) { .aiops-run-form__context { grid-template-columns: minmax(0, 1fr); } }
</style>
