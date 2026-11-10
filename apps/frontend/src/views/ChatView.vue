<script setup lang="ts">
import { PanelRightClose, PanelRightOpen } from "lucide-vue-next";
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import type { ReferenceSourceSseEvent } from "@agent-py/api-contracts";

import ChatComposer from "../components/ChatComposer.vue";
import ChatPromptSidebar from "../components/ChatPromptSidebar.vue";
import ChatSkillSidebar from "../components/ChatSkillSidebar.vue";
import ChatTranscript from "../components/ChatTranscript.vue";
import { useChatStore } from "../stores/chat";

const chat = useChatStore();
const router = useRouter();
const isSettingsOpen = ref(false);
const activeTitle = computed(() => {
  const title = chat.sessions.find((session) => session.id === chat.activeSessionId)?.title;
  return title === undefined || title === "New chat" ? "新对话" : title;
});
const activeSkillCount = computed(() => chat.configuration?.selection.skillIds.length ?? 0);

onMounted(() => {
  isSettingsOpen.value = window.localStorage.getItem("agent-py.chat-settings-open") === "true";
  void chat.initialize().catch(() => undefined);
});

function toggleSettings(): void {
  isSettingsOpen.value = !isSettingsOpen.value;
  window.localStorage.setItem("agent-py.chat-settings-open", String(isSettingsOpen.value));
}

function run(operation: () => Promise<unknown>): void {
  void operation().catch(() => undefined);
}

function openCitationDocument(reference: ReferenceSourceSseEvent["reference"]): void {
  if (reference.documentId === undefined || reference.knowledgeBaseId === undefined) return;
  void router.push({
    name: "knowledge",
    query: { documentId: reference.documentId, knowledgeBaseId: reference.knowledgeBaseId }
  });
}

function saveChatConfiguration(systemPromptId: string, skillIds: readonly string[]): void {
  run(() => chat.saveConfiguration(systemPromptId, skillIds));
}

</script>

<template>
  <section class="chat-view" :class="{ 'chat-view--settings-closed': !isSettingsOpen }" aria-label="对话工作区">
    <div class="chat-view__conversation">
      <header><div><h2>{{ activeTitle }}</h2><span>{{ activeSkillCount > 0 ? `${activeSkillCount} 个 Skill 已启用` : '知识库与工具按需使用' }}</span></div><button type="button" :aria-expanded="isSettingsOpen" aria-controls="chat-settings" :title="isSettingsOpen ? '隐藏对话配置' : '显示对话配置'" @click="toggleSettings"><PanelRightClose v-if="isSettingsOpen" :size="17" aria-hidden="true" /><PanelRightOpen v-else :size="17" aria-hidden="true" /><span>{{ isSettingsOpen ? '关闭配置' : '配置' }}</span></button></header>
      <ChatTranscript
        :is-loading="chat.isLoading"
        :live-tool-calls="chat.liveToolCalls"
        :messages="chat.messages"
        :references="chat.references"
        :tool-audits="chat.toolAudits"
        @open-document="openCitationDocument"
        @suggest="run(() => chat.send($event))"
      />
      <ChatComposer
        :disabled="chat.isLoading"
        :is-sending="chat.isSending"
        :is-updating-memory="chat.isUpdatingMemory"
        :memory="chat.activeSession?.memory ?? null"
        @apply-memory="run(() => chat.updateMemoryMode($event))"
        @compact-memory="run(() => chat.compactMemory())"
        @send="run(() => chat.send($event))"
      />
    </div>
    <div v-if="isSettingsOpen" id="chat-settings" class="chat-view__settings">
      <ChatPromptSidebar
        :configuration="chat.configuration"
        :is-saving="chat.isSavingConfiguration"
        @create-prompt="(label, content) => run(() => chat.createPrompt(label, content))"
        @delete-prompt="run(() => chat.deletePrompt($event))"
        @save="saveChatConfiguration"
        @update-prompt="(promptId, label, content) => run(() => chat.updatePrompt(promptId, label, content))"
      />
      <ChatSkillSidebar
        :configuration="chat.configuration"
        :is-saving="chat.isSavingConfiguration"
        @delete-skill="run(() => chat.deleteSkill($event))"
        @save="saveChatConfiguration"
        @upload-skill="run(() => chat.uploadSkill($event))"
      />
    </div>
  </section>
</template>

<style scoped>
.chat-view { background: var(--surface-raised); display: grid; grid-template-columns: minmax(0, 1fr) minmax(18rem, 22rem); height: 100%; overflow: hidden; }
.chat-view--settings-closed { grid-template-columns: minmax(0, 1fr); }
.chat-view__conversation { background: var(--surface-raised); display: grid; grid-template-rows: auto minmax(0, 1fr) auto; min-height: 0; min-width: 0; overflow: hidden; }
.chat-view__conversation > header { align-items: center; border-bottom: 1px solid var(--line); display: flex; gap: 1rem; justify-content: space-between; min-height: 4.25rem; padding: 0.9rem clamp(1rem, 3vw, 2rem); }
.chat-view__conversation > header h2 { font-size: 0.9rem; font-weight: 700; margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.chat-view__conversation > header > div > span { color: var(--text-tertiary); display: block; font-size: 0.66rem; margin-top: 0.18rem; }
.chat-view__conversation > header > div { min-width: 0; }
.chat-view__conversation > header > button { align-items: center; border: 1px solid var(--line-strong); display: inline-flex; flex: 0 0 auto; font-size: 0.74rem; gap: 0.35rem; min-height: 2.15rem; padding: 0 0.65rem; }
.chat-view__settings { border-left: 1px solid var(--line); display: flex; flex-direction: column; min-height: 0; min-width: 0; overflow-y: auto; }
.chat-view__settings :deep(.chat-prompt-sidebar), .chat-view__settings :deep(.chat-skill-sidebar) { background: var(--surface-raised); border: 0; border-radius: 0; box-shadow: none; flex: 0 0 auto; overflow: visible; padding: 1.35rem 1.25rem; }
.chat-view__settings :deep(.chat-skill-sidebar) { border-top: 1px solid var(--line); }
.chat-view :deep(button:focus-visible), .chat-view :deep(a:focus-visible), .chat-view :deep(input:focus-visible), .chat-view :deep(select:focus-visible), .chat-view :deep(textarea:focus-visible) { outline: 1px solid var(--focus-ring); outline-offset: 2px; }
@media (max-width: 1120px) { .chat-view { grid-template-columns: minmax(0, 1fr); height: auto; overflow: visible; } .chat-view__conversation { min-height: calc(100dvh - 4.5rem); } .chat-view__settings { border-left: 0; border-top: 1px solid var(--line); display: grid; grid-column: 1; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); overflow: visible; } .chat-view__settings :deep(.chat-skill-sidebar) { border-left: 1px solid var(--line); border-top: 0; } }
@media (max-width: 760px) { .chat-view__conversation { min-height: calc(100dvh - 9.85rem); } }
@media (max-width: 720px) { .chat-view__settings { grid-template-columns: minmax(0, 1fr); } .chat-view__settings :deep(.chat-skill-sidebar) { border-left: 0; border-top: 1px solid var(--line); } }
</style>
