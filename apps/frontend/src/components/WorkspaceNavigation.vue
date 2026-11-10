<script setup lang="ts">
import { Activity, BookOpen, Cable, MessageSquare, Zap } from "lucide-vue-next";

withDefaults(defineProps<{ readonly activePath: string; readonly compact?: boolean }>(), { compact: false });

const entries = [
  { icon: Zap, label: "故障演练", to: "/drill", badge: "模拟" },
  { icon: MessageSquare, label: "对话", to: "/chat", badge: null },
  { icon: BookOpen, label: "知识库", to: "/knowledge", badge: null },
  { icon: Activity, label: "智能诊断", to: "/aiops", badge: null },
  { icon: Cable, label: "MCP 连接", to: "/mcp", badge: null }
] as const;
</script>

<template>
  <nav class="workspace-navigation" aria-label="工作区导航">
    <template v-for="entry in entries" :key="entry.to">
      <RouterLink
        :to="entry.to"
        class="workspace-navigation__link"
        :class="{ 'workspace-navigation__link--active': activePath === entry.to, 'workspace-navigation__link--compact': compact }"
        :aria-current="activePath === entry.to ? 'page' : undefined"
        :title="compact ? entry.label : undefined"
      >
        <component :is="entry.icon" :size="18" stroke-width="1.8" aria-hidden="true" />
        <span>{{ entry.label }}</span>
        <em v-if="entry.badge !== null && !compact" class="workspace-navigation__badge" title="演练数据由故障模拟器生成">{{ entry.badge }}</em>
      </RouterLink>
      <slot v-if="entry.to === '/chat' && activePath === '/chat'" name="chat-history" />
    </template>
  </nav>
</template>

<style scoped>
.workspace-navigation { display: grid; gap: 0.35rem; }
.workspace-navigation__link { align-items: center; border: 1px solid transparent; border-radius: 0; color: var(--rail-muted); display: flex; font-size: 0.76rem; font-weight: 600; gap: 0.72rem; letter-spacing: 0.07em; min-height: 2.75rem; padding: 0 0.75rem; text-decoration: none; text-transform: uppercase; transition: background 120ms ease-out, border-color 120ms ease-out, box-shadow 120ms ease-out, color 120ms ease-out, transform 120ms ease-out; }
.workspace-navigation__link:hover { background: var(--rail-hover); border-color: var(--accent-border); box-shadow: inset 0 0 12px rgb(0 255 255 / 8%); color: var(--accent); }
.workspace-navigation__link:active { color: var(--accent-ink); transform: translate(2px, -1px); }
.workspace-navigation__link--active { background: var(--accent-soft); border-color: var(--accent-border); box-shadow: inset 0 0 16px rgb(0 255 255 / 10%), 0 0 10px rgb(0 255 255 / 12%); color: var(--accent-strong); font-weight: 750; text-shadow: 0 0 8px rgb(0 255 255 / 42%); }
.workspace-navigation__link--active:focus-visible { outline: 1px solid var(--focus-ring); outline-offset: -1px; }
.workspace-navigation__link--active svg { color: var(--accent-strong); }
.workspace-navigation__link--compact { justify-content: center; padding: 0; }
.workspace-navigation__badge { border: 1px solid var(--status-waiting-border); color: var(--status-waiting-text); font-size: 0.58rem; font-style: normal; letter-spacing: 0.04em; line-height: 1; margin-left: auto; padding: 0.15rem 0.3rem; text-transform: none; }
.workspace-navigation__link--compact span { clip: rect(0, 0, 0, 0); clip-path: inset(50%); height: 1px; overflow: hidden; position: absolute; white-space: nowrap; width: 1px; }
</style>
