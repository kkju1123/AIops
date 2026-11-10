<script setup lang="ts">
import { CircleDot, FlaskConical, LogIn, LogOut, PanelLeftClose, PanelLeftOpen, Sparkles, TriangleAlert } from "lucide-vue-next";
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import WorkspaceNavigation from "../components/WorkspaceNavigation.vue";
import ChatSessionList from "../components/ChatSessionList.vue";
import { createRuntimeHealthClient } from "../runtimeHealth";
import { useAuthStore } from "../stores/auth";
import { useChatStore } from "../stores/chat";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const chat = useChatStore();
const routeTitle = computed(() => (typeof route.meta.title === "string" ? route.meta.title : "工作台"));
const initials = computed(() => auth.user?.displayName.slice(0, 1).toUpperCase() ?? "用");
const isConnected = ref(true);
const isRailCollapsed = ref(false);

onMounted(() => {
  const savedRailState = window.localStorage.getItem("agent-py.rail-collapsed");
  isRailCollapsed.value = savedRailState === null ? true : savedRailState === "true";
  void createRuntimeHealthClient().health().then(() => {
    isConnected.value = true;
  }).catch(() => {
    isConnected.value = false;
  });
});

function toggleRail(): void {
  isRailCollapsed.value = !isRailCollapsed.value;
  window.localStorage.setItem("agent-py.rail-collapsed", String(isRailCollapsed.value));
}

async function logout(): Promise<void> {
  try {
    await auth.logout();
  } finally {
    await router.replace("/login");
  }
}

async function switchToOwner(): Promise<void> {
  try {
    await auth.logout();
  } finally {
    await router.replace({ path: "/login", query: { redirect: "/chat" } });
  }
}

function runChat(operation: () => Promise<unknown>): void {
  void operation().catch(() => undefined);
}
</script>

<template>
  <div class="workspace-layout" :class="{ 'workspace-layout--rail-collapsed': isRailCollapsed }">
    <aside class="workspace-layout__rail">
      <div class="workspace-layout__rail-header">
        <RouterLink class="workspace-layout__brand" :to="auth.isGuest ? '/drill' : '/chat'" aria-label="Super AI 工作台">
          <Sparkles :size="19" stroke-width="1.8" aria-hidden="true" />
          <span>Super AI</span>
          <small>智能工作台</small>
        </RouterLink>
        <button type="button" class="workspace-layout__rail-toggle" :title="isRailCollapsed ? '展开导航' : '收起导航'" :aria-label="isRailCollapsed ? '展开导航' : '收起导航'" @click="toggleRail">
          <PanelLeftOpen v-if="isRailCollapsed" :size="17" aria-hidden="true" />
          <PanelLeftClose v-else :size="17" aria-hidden="true" />
        </button>
      </div>
      <WorkspaceNavigation :active-path="route.path" :compact="isRailCollapsed">
        <template #chat-history>
          <ChatSessionList
            v-if="!isRailCollapsed"
            :active-session-id="chat.activeSessionId"
            :sessions="chat.sessions"
            variant="rail"
            @create="runChat(chat.newSession)"
            @delete="runChat(() => chat.deleteSession($event))"
            @select="runChat(() => chat.selectSession($event))"
          />
        </template>
      </WorkspaceNavigation>
      <div class="workspace-layout__account">
        <span class="workspace-layout__avatar" aria-hidden="true">{{ initials }}</span>
        <span class="workspace-layout__identity">
          <strong>{{ auth.user?.displayName }}</strong>
          <small>{{ auth.isGuest ? "访客 · 临时账号" : auth.user?.email }}</small>
        </span>
        <button type="button" :title="auth.isGuest ? '退出访客模式' : '退出登录'" :aria-label="auth.isGuest ? '退出访客模式' : '退出登录'" @click="logout">
          <LogOut :size="17" aria-hidden="true" />
        </button>
      </div>
    </aside>
    <section class="workspace-layout__main">
      <header class="workspace-layout__header">
        <div>
          <p>AI 工作台</p>
          <h1>{{ routeTitle }}</h1>
        </div>
        <div v-if="auth.isGuest" class="workspace-layout__guest" role="note" aria-label="访客模式">
          <FlaskConical :size="15" aria-hidden="true" />
          <span><strong>访客模式 · 演练环境</strong><small>演练日志与指标由故障模拟器生成，非生产数据</small></span>
          <button type="button" @click="switchToOwner"><LogIn :size="14" aria-hidden="true" />所有者登录</button>
        </div>
        <span class="workspace-layout__status" :class="{ 'workspace-layout__status--degraded': !isConnected }" role="status" aria-live="polite">
          <CircleDot v-if="isConnected" :size="15" aria-hidden="true" />
          <TriangleAlert v-else :size="15" aria-hidden="true" />
          {{ isConnected ? "服务已连接" : "服务连接异常" }}
        </span>
      </header>
      <main class="workspace-layout__content"><RouterView /></main>
    </section>
    <div class="workspace-layout__mobile-nav"><WorkspaceNavigation :active-path="route.path" /></div>
  </div>
</template>

<style scoped>
.workspace-layout { background: var(--surface-raised); color: var(--text-primary); display: grid; grid-template-columns: 16rem minmax(0, 1fr); height: 100dvh; min-height: 100vh; overflow: hidden; }
.workspace-layout--rail-collapsed { grid-template-columns: 4.75rem minmax(0, 1fr); }
.workspace-layout__rail { background: var(--rail); border-right: 1px solid var(--line); box-shadow: 8px 0 24px rgb(0 255 255 / 4%); display: flex; flex-direction: column; height: 100dvh; min-height: 0; padding: 1.75rem 1rem 1rem; position: relative; z-index: 5; }
.workspace-layout__rail-header { align-items: center; display: grid; gap: 0.35rem; grid-template-columns: minmax(0, 1fr) auto; margin: 0.4rem 0.25rem 2.5rem; }
.workspace-layout__brand { align-items: center; color: var(--rail-text); display: grid; gap: 0 0.65rem; grid-template-columns: auto minmax(0, 1fr); min-width: 0; text-decoration: none; }
.workspace-layout__brand svg { color: var(--accent); filter: drop-shadow(0 0 6px rgb(0 255 255 / 65%)); grid-row: span 2; }
.workspace-layout__brand span { font-size: 1.02rem; font-weight: 800; letter-spacing: 0.11em; line-height: 1.1; text-shadow: 0 0 8px rgb(215 221 224 / 12%); text-transform: uppercase; }
.workspace-layout__brand small { color: var(--accent); font-size: 0.62rem; letter-spacing: 0.14em; margin-top: 0.18rem; text-transform: uppercase; }
.workspace-layout__rail-toggle { align-items: center; border-radius: 0 !important; color: var(--rail-muted); display: inline-flex; height: 2rem; justify-content: center; width: 2rem; }
.workspace-layout__rail-toggle:hover { background: var(--rail-hover); color: var(--rail-text); }
.workspace-layout--rail-collapsed .workspace-layout__rail { padding-left: 0.65rem; padding-right: 0.65rem; }
.workspace-layout--rail-collapsed .workspace-layout__rail-header { grid-template-columns: minmax(0, 1fr); justify-items: center; margin-bottom: 1.5rem; }
.workspace-layout--rail-collapsed .workspace-layout__brand span, .workspace-layout--rail-collapsed .workspace-layout__brand small { display: none; }
.workspace-layout--rail-collapsed .workspace-layout__brand svg { grid-row: auto; }
.workspace-layout--rail-collapsed .workspace-layout__account { grid-template-columns: minmax(0, 1fr); justify-items: center; padding-left: 0; padding-right: 0; }
.workspace-layout--rail-collapsed .workspace-layout__identity { display: none; }
.workspace-layout__account { align-items: center; border-top: 1px solid var(--line); display: grid; gap: 0.65rem; grid-template-columns: auto minmax(0, 1fr) auto; margin: auto 0 0; padding: 1rem 0.55rem 0; }
.workspace-layout__avatar { align-items: center; background: var(--accent-soft); border: 1px solid var(--accent-border); border-radius: 2px; box-shadow: var(--shadow-glow-sm); color: var(--accent); display: inline-flex; font-size: 0.78rem; font-weight: 800; height: 2.25rem; justify-content: center; width: 2.25rem; }
.workspace-layout__identity { display: grid; min-width: 0; }
.workspace-layout__identity strong, .workspace-layout__identity small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.workspace-layout__identity strong { color: var(--rail-text); font-size: 0.8rem; }
.workspace-layout__identity small { color: var(--rail-muted); font-size: 0.68rem; }
.workspace-layout__account button { align-items: center; background: transparent; border-radius: 0 !important; color: var(--rail-muted); display: inline-flex; height: 2.25rem; justify-content: center; width: 2.25rem; }
.workspace-layout__main { background: var(--surface-raised); display: grid; grid-template-rows: auto minmax(0, 1fr); height: 100dvh; min-width: 0; overflow: hidden; }
.workspace-layout__header { align-items: center; background-color: var(--surface-raised); background-image: linear-gradient(90deg, rgb(0 255 255 / 3%), transparent 34%, rgb(255 0 255 / 2%)); border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; min-height: 5rem; padding: 0.9rem clamp(1.25rem, 3vw, 3rem); position: relative; z-index: 4; }
.workspace-layout__header::after { background: linear-gradient(90deg, var(--accent), transparent 28%, transparent 72%, var(--accent-ink)); bottom: -1px; content: ""; height: 1px; left: 0; opacity: 0.58; position: absolute; right: 0; }
.workspace-layout__header p { color: var(--accent-ink); font-size: 0.64rem; font-weight: 750; letter-spacing: 0.16em; margin: 0 0 0.25rem; text-shadow: 0 0 9px rgb(255 0 255 / 45%); text-transform: uppercase; }
.workspace-layout__header h1 { font-size: 1.22rem; font-weight: 800; letter-spacing: 0.08em; margin: 0; text-shadow: 0 0 8px rgb(215 221 224 / 10%); text-transform: uppercase; }
.workspace-layout__status { align-items: center; background: transparent; border: 0; color: var(--status-success-text); display: inline-flex; font-size: 0.68rem; font-weight: 650; gap: 0.35rem; min-height: 2rem; padding: 0 0.25rem; }
.workspace-layout__status--degraded { color: var(--status-danger-text); }
.workspace-layout__guest { align-items: center; border: 1px solid var(--status-waiting-border); color: var(--status-waiting-text); display: flex; gap: 0.6rem; margin: 0 1rem 0 auto; min-height: 2.6rem; padding: 0.3rem 0.4rem 0.3rem 0.7rem; }
.workspace-layout__guest > span { display: grid; min-width: 0; }
.workspace-layout__guest strong { font-size: 0.7rem; letter-spacing: 0.04em; }
.workspace-layout__guest small { color: var(--text-tertiary); font-size: 0.62rem; }
.workspace-layout__guest button { align-items: center; border: 1px solid var(--accent-border); color: var(--accent); display: inline-flex; flex: 0 0 auto; font-size: 0.66rem; font-weight: 700; gap: 0.3rem; min-height: 2rem; padding: 0 0.6rem; }
.workspace-layout__guest button:hover { background: var(--accent-soft); }
.workspace-layout__content { height: 100%; min-height: 0; overflow: hidden; width: 100%; }
.workspace-layout__mobile-nav { display: none; }
@media (max-width: 760px) { .workspace-layout { display: block; height: auto; min-height: 100vh; overflow: visible; padding-bottom: 5.35rem; } .workspace-layout__rail { display: none; } .workspace-layout__main { height: auto; min-height: calc(100dvh - 5.35rem); overflow: visible; } .workspace-layout__header { min-height: 4.5rem; padding: 0.75rem 1rem; } .workspace-layout__header h1 { font-size: 1.05rem; } .workspace-layout__status { font-size: 0.64rem; padding: 0 0.5rem; } .workspace-layout__content { overflow: visible; } .workspace-layout__mobile-nav { backdrop-filter: blur(12px); background: rgb(5 7 11 / 96%); border-top: 1px solid var(--accent-border); bottom: 0; box-shadow: 0 -4px 18px rgb(0 255 255 / 10%); display: block; left: 0; padding: 0.35rem 0.4rem calc(0.35rem + env(safe-area-inset-bottom)); position: fixed; right: 0; z-index: 10; } .workspace-layout__mobile-nav :deep(.workspace-navigation) { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); } .workspace-layout__mobile-nav :deep(.workspace-navigation__badge) { display: none; } .workspace-layout__header { flex-wrap: wrap; gap: 0.5rem; } .workspace-layout__guest { margin: 0; order: 3; width: 100%; } .workspace-layout__guest small { display: none; } .workspace-layout__guest button { margin-left: auto; } .workspace-layout__mobile-nav :deep(.workspace-navigation__link) { flex-direction: column; font-size: 0.66rem; gap: 0.2rem; justify-content: center; min-height: 4rem; padding: 0.3rem; } }
</style>
