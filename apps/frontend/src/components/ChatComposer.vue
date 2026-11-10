<script setup lang="ts">
import { ArrowUp, BrainCircuit, Check, ChevronUp, LoaderCircle, Wrench } from "lucide-vue-next";
import { computed, ref, watch } from "vue";

import type { ChatMemoryMode, ChatMemoryState } from "@agent-py/api-contracts";

const emit = defineEmits<{
  send: [content: string];
  applyMemory: [mode: ChatMemoryMode];
  compactMemory: [];
}>();
const props = defineProps<{
  readonly disabled: boolean;
  readonly isSending: boolean;
  readonly isUpdatingMemory: boolean;
  readonly memory: ChatMemoryState | null;
}>();
const content = ref("");
const selectedMode = ref<ChatMemoryMode>(props.memory?.mode ?? "every_30_turns");
const isHardLimited = computed(() => (props.memory?.contextUsagePercent ?? 0) >= 95);
const inputDisabled = computed(() => props.disabled || props.isSending || isHardLimited.value);
const memoryModeLabel = computed(() => {
  if (props.memory?.mode === "context_70_percent") return "占用 70% 时自动整理";
  if (props.memory?.mode === "manual") return "手动整理";
  return "每 30 轮自动整理";
});

watch(() => props.memory?.mode, (mode) => {
  if (mode !== undefined) selectedMode.value = mode;
});

function resizeTextarea(event: Event): void {
  const textarea = event.target as HTMLTextAreaElement;
  textarea.style.height = "auto";
  textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
}

function submit(): void {
  const nextContent = content.value.trim();
  if (nextContent.length === 0 || inputDisabled.value) return;
  emit("send", nextContent);
  content.value = "";
}

function handleKeydown(event: KeyboardEvent): void {
  if (event.key !== "Enter" || event.shiftKey || event.isComposing) return;
  event.preventDefault();
  submit();
}
</script>

<template>
  <form class="chat-composer" @submit.prevent="submit">
    <div class="chat-composer__inner">
      <label class="chat-composer__sr-only" for="chat-message">输入问题</label>
      <div class="chat-composer__field">
        <textarea
          id="chat-message"
          v-model="content"
          rows="2"
          placeholder="描述现象、错误信息，或想要完成的任务…"
          :disabled="inputDisabled"
          @input="resizeTextarea"
          @keydown="handleKeydown"
        />
        <button type="submit" title="发送消息" aria-label="发送消息" :disabled="inputDisabled || !content.trim()">
          <LoaderCircle v-if="isSending" class="chat-composer__spin" :size="18" aria-hidden="true" />
          <ArrowUp v-else :size="18" aria-hidden="true" />
        </button>
      </div>

      <div class="chat-composer__meta">
        <span class="chat-composer__capability"><Wrench :size="14" aria-hidden="true" />知识库与工具按需调用</span>
        <details class="chat-composer__memory">
          <summary>
            <BrainCircuit :size="14" aria-hidden="true" />
            上下文 {{ memory?.contextUsagePercent ?? 0 }}% · {{ memoryModeLabel }}
            <ChevronUp :size="14" aria-hidden="true" />
          </summary>
          <div class="chat-composer__memory-panel">
            <header><div><strong>上下文管理</strong><small>较早消息会按所选策略整理，以留出回答空间。</small></div><span>{{ memory?.contextUsagePercent ?? 0 }}%</span></header>
            <progress :value="memory?.contextUsagePercent ?? 0" max="100" aria-label="上下文窗口占用" />
            <label>整理策略
              <select v-model="selectedMode" aria-label="记忆模式" :disabled="!memory || isUpdatingMemory">
                <option value="every_30_turns">每 30 轮自动整理</option>
                <option value="context_70_percent">占用 70% 时自动整理</option>
                <option value="manual">仅手动整理</option>
              </select>
            </label>
            <button
              v-if="memory?.mode === 'manual' && selectedMode === 'manual'"
              type="button"
              :disabled="isUpdatingMemory"
              @click="emit('compactMemory')"
            >{{ isUpdatingMemory ? "整理中" : "立即整理上下文" }}</button>
            <button
              v-else
              type="button"
              :disabled="!memory || isUpdatingMemory || selectedMode === memory?.mode"
              @click="emit('applyMemory', selectedMode)"
            ><Check :size="14" aria-hidden="true" />{{ isUpdatingMemory ? "保存中" : "保存策略" }}</button>
          </div>
        </details>
        <span class="chat-composer__hint">Enter 发送 · Shift+Enter 换行</span>
      </div>
      <span v-if="isSending" class="chat-composer__status" role="status" aria-live="polite">正在生成回答，请稍候</span>
      <span v-else-if="isHardLimited" class="chat-composer__limit" role="alert">上下文已达到 95%，请整理上下文后继续。</span>
    </div>
  </form>
</template>

<style scoped>
.chat-composer { background: var(--surface-raised); border-top: 1px solid var(--line); padding: 0.8rem clamp(1rem, 3vw, 2rem) 1rem; }
.chat-composer__inner { display: grid; gap: 0.45rem; isolation: isolate; margin: 0 auto; max-width: 52rem; position: relative; }
.chat-composer__sr-only { clip: rect(0, 0, 0, 0); clip-path: inset(50%); height: 1px; overflow: hidden; position: absolute; white-space: nowrap; width: 1px; }
.chat-composer__field { background: var(--surface); border: 1px solid var(--line-strong); display: grid; grid-template-columns: minmax(0, 1fr) auto; padding: 0.4rem; }
.chat-composer__field:focus-within { border-color: var(--accent-border); box-shadow: 0 0 0 2px var(--accent-soft); }
textarea { background: transparent !important; border: 0 !important; border-radius: 0 !important; box-shadow: none !important; color: var(--text-primary); line-height: 1.55; max-height: 10rem; min-height: 3.65rem; outline: 0; overflow-y: auto; padding: 0.55rem 0.65rem; resize: none; width: 100%; }
textarea::placeholder { color: var(--text-tertiary); }
.chat-composer__field > button { align-items: center; align-self: end; background: var(--accent-strong); color: var(--on-accent); display: inline-flex; height: 2.4rem; justify-content: center; width: 2.4rem; }
.chat-composer__field > button:hover:not(:disabled) { filter: brightness(0.92); }.chat-composer__field > button:disabled { background: var(--surface-inset); color: var(--text-tertiary); cursor: not-allowed; }
.chat-composer__meta { align-items: center; color: var(--text-tertiary); display: flex; flex-wrap: wrap; font-size: 0.66rem; gap: 0.45rem 0.8rem; min-height: 1.65rem; padding: 0 0.2rem; }
.chat-composer__capability { align-items: center; display: inline-flex; gap: 0.3rem; }.chat-composer__hint { margin-left: auto; }
.chat-composer__memory { position: relative; }.chat-composer__memory summary { align-items: center; cursor: pointer; display: inline-flex; gap: 0.3rem; list-style: none; }.chat-composer__memory summary::-webkit-details-marker { display: none; }.chat-composer__memory summary svg:last-child { transition: transform 160ms ease; }.chat-composer__memory[open] summary svg:last-child { transform: rotate(180deg); }
.chat-composer__memory-panel { background: var(--surface-raised); border: 1px solid var(--line-strong); bottom: calc(100% + 0.65rem); box-shadow: var(--shadow-raised-sm); display: grid; gap: 0.75rem; left: 0; min-width: 20rem; padding: 0.9rem; position: absolute; z-index: 8; }.chat-composer__memory-panel header { align-items: start; display: flex; justify-content: space-between; }.chat-composer__memory-panel header strong, .chat-composer__memory-panel header small { display: block; }.chat-composer__memory-panel header strong { color: var(--text-primary); font-size: 0.78rem; }.chat-composer__memory-panel header small { color: var(--text-tertiary); font-size: 0.66rem; line-height: 1.45; margin-top: 0.18rem; max-width: 15rem; }.chat-composer__memory-panel header > span { color: var(--text-primary); font-size: 0.75rem; font-weight: 700; }
.chat-composer__memory-panel progress { accent-color: var(--accent-strong); height: 0.35rem; width: 100%; }.chat-composer__memory-panel label { color: var(--text-secondary); display: grid; font-size: 0.68rem; font-weight: 650; gap: 0.35rem; }.chat-composer__memory-panel select { background: var(--surface); border: 1px solid var(--line-strong); color: var(--text-primary); min-height: 2.25rem; padding: 0 0.5rem; width: 100%; }.chat-composer__memory-panel > button { align-items: center; background: var(--accent-strong); color: var(--on-accent); display: inline-flex; font-size: 0.7rem; gap: 0.3rem; justify-content: center; min-height: 2.25rem; padding: 0 0.65rem; }.chat-composer__memory-panel > button:disabled { cursor: not-allowed; opacity: 0.45; }
.chat-composer__status, .chat-composer__limit { font-size: 0.7rem; padding-left: 0.2rem; }.chat-composer__status { color: var(--status-running-text); }.chat-composer__limit { color: var(--status-error-text); }
.chat-composer__spin { animation: chat-composer-spin 0.8s linear infinite; } @keyframes chat-composer-spin { to { transform: rotate(360deg); } }
@media (max-width: 640px) { .chat-composer { padding: 0.7rem 0.75rem 0.85rem; }.chat-composer__capability { display: none; }.chat-composer__hint { display: none; }.chat-composer__memory-panel { left: auto; min-width: min(20rem, calc(100vw - 2rem)); right: -4rem; } }
@media (prefers-reduced-motion: reduce) { .chat-composer__memory summary svg:last-child { transition: none; } }
</style>
