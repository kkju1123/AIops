<script setup lang="ts">
import { Activity, BellRing, BookOpen, Bot, Search, Sparkles, Wrench } from "lucide-vue-next";
import { computed, ref } from "vue";

import type { ChatMessage, ToolCallAudit } from "@agent-py/api-contracts";
import type { ChatReference, LiveToolCall } from "../stores/chat";
import AppLoadingState from "./AppLoadingState.vue";
import AsyncStatusBadge from "./AsyncStatusBadge.vue";
import ChatCitationDetail from "./ChatCitationDetail.vue";
import MarkdownContent from "./MarkdownContent.vue";
import RetrievalStageTrace from "./RetrievalStageTrace.vue";
import UserFeedbackControl from "./UserFeedbackControl.vue";

const emit = defineEmits<{
  "open-document": [reference: ChatReference];
  suggest: [content: string];
}>();
const props = defineProps<{
  readonly isLoading: boolean;
  readonly liveToolCalls: readonly LiveToolCall[];
  readonly messages: readonly ChatMessage[];
  readonly references: readonly ChatReference[];
  readonly toolAudits: readonly ToolCallAudit[];
}>();

const selectedCitation = ref<ChatReference | null>(null);
const selectedCitationMessageId = ref<string | null>(null);
const latestAssistantMessageId = computed(() =>
  [...props.messages].reverse().find((message) => message.role === "assistant")?.id ?? null
);
const suggestions = [
  { icon: Activity, label: "排查服务异常", content: "帮我排查最近出现的服务异常，并给出可能原因和下一步建议。" },
  { icon: BellRing, label: "查看活跃告警", content: "查看当前活跃告警，按严重程度总结最需要处理的问题。" },
  { icon: BookOpen, label: "查询处理手册", content: "从知识库中查找与当前故障相关的 SOP 和处理步骤。" },
  { icon: Search, label: "分析日志线索", content: "分析最近的错误日志，提取关键异常模式和时间线。" }
] as const;

function selectCitation(reference: ChatReference, messageId: string | null): void {
  selectedCitation.value = reference;
  selectedCitationMessageId.value = messageId;
}

function canCollectFeedback(message: ChatMessage): boolean {
  return message.role === "assistant" && !message.id.startsWith("message_draft_");
}

function sourceLabel(reference: ChatReference): string {
  if (reference.knowledgeType === "sop") return "SOP";
  if (reference.knowledgeType === "diagnostic-case") return "故障案例";
  return reference.knowledgeType === "document" || reference.sourceType === "document"
    ? "知识库"
    : reference.sourceType;
}

function messageAudits(message: ChatMessage): readonly ToolCallAudit[] {
  const ids = new Set(message.metadata.toolCallIds ?? []);
  return props.toolAudits.filter((audit) => ids.has(audit.id));
}
</script>

<template>
  <section class="chat-transcript" aria-label="当前对话">
    <AppLoadingState v-if="isLoading" label="正在加载对话" />
    <section v-else-if="messages.length === 0" class="chat-transcript__welcome" aria-labelledby="chat-welcome-title">
      <span class="chat-transcript__welcome-mark"><Sparkles :size="20" aria-hidden="true" /></span>
      <h2 id="chat-welcome-title">今天想排查什么问题？</h2>
      <p>描述现象或选择一个常用任务。Super AI 会按需检索知识库并调用已连接的工具。</p>
      <div class="chat-transcript__suggestions" aria-label="常用问题">
        <button v-for="suggestion in suggestions" :key="suggestion.label" type="button" @click="emit('suggest', suggestion.content)">
          <component :is="suggestion.icon" :size="16" aria-hidden="true" />
          <span><strong>{{ suggestion.label }}</strong><small>{{ suggestion.content }}</small></span>
        </button>
      </div>
    </section>
    <ol v-else-if="messages.length > 0" class="chat-transcript__messages">
      <li v-for="message in messages" :key="message.id" :class="`chat-transcript__message--${message.role}`">
        <article class="chat-transcript__message">
          <span class="chat-transcript__role"><Bot v-if="message.role === 'assistant'" :size="15" aria-hidden="true" />{{ message.role === "assistant" ? "助手" : "你" }}</span>
          <MarkdownContent v-if="message.role === 'assistant'" :content="message.content" />
          <p v-else>{{ message.content }}</p>
          <ul v-if="message.metadata.citations?.length" class="chat-transcript__message-sources" aria-label="回答引用来源">
            <li v-for="reference in message.metadata.citations" :key="reference.id"><button type="button" :aria-label="`查看 ${reference.title} 的来源详情`" @click="selectCitation(reference, message.id)"><BookOpen :size="13" aria-hidden="true" />{{ reference.title }}</button><RetrievalStageTrace :reference="reference" compact /><UserFeedbackControl v-if="canCollectFeedback(message)" target-type="citation" :target-id="message.id" :subject-id="reference.id" compact /></li>
          </ul>
          <UserFeedbackControl v-if="canCollectFeedback(message)" target-type="chat_message" :target-id="message.id" compact />
          <details v-if="message.role === 'assistant' && messageAudits(message).length" class="chat-transcript__details"><summary><Wrench :size="14" aria-hidden="true" />工具调用（{{ messageAudits(message).length }}）</summary><ul><li v-for="audit in messageAudits(message)" :key="audit.id"><span>{{ audit.toolName }}</span><AsyncStatusBadge :status="audit.status" compact /><small v-if="audit.resultSummary || audit.errorMessage">{{ audit.resultSummary ?? audit.errorMessage }}</small></li></ul></details>
          <details v-if="message.role === 'assistant' && message.metadata.reasoning?.length" class="chat-transcript__details"><summary>深度思考</summary><p>{{ message.metadata.reasoning.join('') }}</p></details>
        </article>
      </li>
    </ol>
    <aside v-if="liveToolCalls.length > 0" class="chat-transcript__context" aria-label="正在进行的工具调用">
      <h2><Wrench :size="15" aria-hidden="true" />工具调用</h2>
      <ul>
        <li v-for="tool in liveToolCalls" :key="tool.id"><span>{{ tool.name }}</span><AsyncStatusBadge :status="tool.status" compact /></li>
      </ul>
    </aside>
    <aside v-if="references.length > 0" class="chat-transcript__context" aria-label="本次回答引用的来源">
      <h2><BookOpen :size="15" aria-hidden="true" />本次回答引用</h2>
      <ul><li v-for="reference in references" :key="reference.id"><div class="chat-transcript__reference-heading"><span>{{ sourceLabel(reference) }}</span><button type="button" :aria-label="`查看 ${reference.title} 的来源详情`" @click="selectCitation(reference, latestAssistantMessageId)">{{ reference.title }}</button></div><RetrievalStageTrace :reference="reference" compact /><UserFeedbackControl v-if="latestAssistantMessageId" target-type="citation" :target-id="latestAssistantMessageId" :subject-id="reference.id" compact /></li></ul>
    </aside>
    <ChatCitationDetail v-if="selectedCitation && selectedCitationMessageId" :message-id="selectedCitationMessageId" :reference="selectedCitation" @close="selectedCitation = null; selectedCitationMessageId = null" @open-document="emit('open-document', $event)" />
  </section>
</template>

<style scoped>
.chat-transcript { display: grid; gap: 1.35rem; min-height: 0; overflow-y: auto; overscroll-behavior: contain; padding: 1.75rem clamp(1rem, 4vw, 4.5rem); scrollbar-color: var(--line-strong) transparent; }
.chat-transcript__welcome { align-self: center; justify-self: center; max-width: 46rem; padding: 2rem 0; text-align: center; width: 100%; }
.chat-transcript__welcome-mark { align-items: center; color: var(--accent-strong); display: inline-flex; justify-content: center; margin-bottom: 0.75rem; }
.chat-transcript__welcome h2 { color: var(--text-primary); display: block; font-size: clamp(1.25rem, 2vw, 1.65rem); margin: 0; }
.chat-transcript__welcome > p { color: var(--text-secondary); font-size: 0.82rem; line-height: 1.65; margin: 0.55rem auto 1.4rem; max-width: 34rem; }
.chat-transcript__suggestions { display: grid; gap: 0.6rem; grid-template-columns: repeat(2, minmax(0, 1fr)); text-align: left; }
.chat-transcript__suggestions button { align-items: start; background: var(--surface); border: 1px solid var(--line); display: grid; gap: 0.65rem; grid-template-columns: auto minmax(0, 1fr); min-height: 4.7rem; padding: 0.8rem; text-align: left; }
.chat-transcript__suggestions button:hover { background: var(--surface-hover); border-color: var(--line-strong); }
.chat-transcript__suggestions button svg { color: var(--accent-strong); margin-top: 0.1rem; }
.chat-transcript__suggestions button strong, .chat-transcript__suggestions button small { display: block; }
.chat-transcript__suggestions button strong { color: var(--text-primary); font-size: 0.76rem; }
.chat-transcript__suggestions button small { color: var(--text-tertiary); display: -webkit-box; font-size: 0.68rem; line-height: 1.45; margin-top: 0.22rem; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.chat-transcript__messages { display: grid; gap: 1.4rem; list-style: none; margin: 0; padding: 0; }
.chat-transcript__message--user { display: flex; justify-content: flex-end; }
.chat-transcript__message { max-width: min(46rem, 90%); min-width: 0; }
.chat-transcript__role { align-items: center; color: var(--text-tertiary); display: inline-flex; font-size: 0.72rem; font-weight: 680; gap: 0.35rem; margin-bottom: 0.48rem; }
.chat-transcript__message p { line-height: 1.7; margin: 0; overflow-wrap: anywhere; white-space: pre-wrap; word-break: break-word; }
.chat-transcript__message-sources { display: grid; gap: 0.6rem; list-style: none; margin: 0.85rem 0 0; padding: 0; }
.chat-transcript__message-sources li { display: grid; gap: 0.35rem; justify-items: start; }
.chat-transcript__message-sources li button { align-items: center; background: var(--accent-soft); border: 1px solid var(--accent-border); border-radius: var(--radius-sm); color: var(--accent-strong); display: inline-flex; font-size: 0.74rem; font-weight: 600; gap: 0.3rem; padding: 0.28rem 0.48rem; }
.chat-transcript__message-sources li button:hover { background: var(--accent-soft); box-shadow: var(--shadow-glow-sm); }
.chat-transcript__details { border-top: 1px solid var(--line); color: var(--text-secondary); font-size: 0.78rem; margin-top: 0.8rem; padding-top: 0.65rem; }
.chat-transcript__details summary { align-items: center; cursor: pointer; display: flex; font-weight: 700; gap: 0.35rem; }
.chat-transcript__details ul { display: grid; gap: 0.4rem; list-style: none; margin: 0.65rem 0 0; padding: 0; }
.chat-transcript__details li { align-items: center; display: grid; gap: 0.45rem; grid-template-columns: minmax(0, 1fr) auto; }
.chat-transcript__details li small { color: var(--text-tertiary); grid-column: 1 / -1; overflow-wrap: anywhere; }
.chat-transcript__details p { color: var(--text-secondary); font-size: 0.78rem; line-height: 1.6; margin: 0.65rem 0 0; white-space: pre-wrap; }
.chat-transcript__context { background: var(--surface); border-radius: var(--radius-md); box-shadow: var(--shadow-inset-soft); max-width: 46rem; padding: 0.9rem 1rem; }
.chat-transcript__context h2 { align-items: center; color: var(--text-secondary); display: flex; font-size: 0.78rem; font-weight: 700; gap: 0.42rem; margin: 0 0 0.7rem; }
.chat-transcript__context ul { display: grid; gap: 0.42rem; list-style: none; margin: 0; padding: 0; }
.chat-transcript__context li { display: grid; gap: 0.45rem; }
.chat-transcript__reference-heading { align-items: center; display: grid; gap: 0.5rem; grid-template-columns: auto minmax(0, 1fr); }
.chat-transcript__reference-heading > span { color: var(--text-tertiary); font-size: 0.7rem; }
.chat-transcript__reference-heading > button { font-size: 0.81rem; font-weight: 650; overflow: hidden; text-align: left; text-overflow: ellipsis; white-space: nowrap; }
.chat-transcript__reference-heading > button:hover { color: var(--accent-strong); text-decoration: underline; }
.chat-transcript__context li > span { align-items: center; display: grid; font-size: 0.81rem; gap: 0.25rem; grid-template-columns: auto minmax(0, 1fr); }
.chat-transcript__context li > span small { color: var(--text-secondary); font-size: 0.74rem; grid-column: 1 / -1; overflow-wrap: anywhere; }
.chat-transcript__context li > span svg { color: var(--accent-strong); }
.chat-transcript__context li > span svg + * { min-width: 0; }
@media (max-width: 860px) { .chat-transcript { overflow-y: visible; } }
@media (max-width: 640px) { .chat-transcript { padding: 1.15rem 0; }.chat-transcript__welcome { padding-inline: 0.2rem; }.chat-transcript__suggestions { grid-template-columns: minmax(0, 1fr); }.chat-transcript__message { max-width: 94%; } }
</style>
