import {
  createMemoryHistory,
  createRouter,
  createWebHistory,
  type Router
} from "vue-router";

import WorkspaceLayout from "../layouts/WorkspaceLayout.vue";
import AuthView from "../views/AuthView.vue";
import AiopsView from "../views/AiopsView.vue";
import ChatView from "../views/ChatView.vue";
import KnowledgeView from "../views/KnowledgeView.vue";
import LiveDemoView from "../views/LiveDemoView.vue";
import McpView from "../views/McpView.vue";
import PublicLandingView from "../views/PublicLandingView.vue";

export interface AuthRouteAccess {
  /** Create a guest session for routes marked `guestEntry`; absent means guests are unsupported. */
  enterAsGuest?(): Promise<void>;
  initialize(): Promise<void>;
  isAuthenticated(): boolean;
}

export function createAppRouter(auth: AuthRouteAccess): Router {
  const router = createRouter({
    history: typeof window === "undefined" ? createMemoryHistory() : createWebHistory(),
    routes: [
      { path: "/", name: "portfolio", component: PublicLandingView },
      { path: "/demo", redirect: "/" },
      { path: "/live", redirect: "/drill" },
      {
        path: "/login",
        name: "login",
        component: AuthView,
        props: { mode: "login" },
        meta: { publicOnly: true }
      },
      {
        path: "/register",
        name: "register",
        component: AuthView,
        props: { mode: "register" },
        meta: { publicOnly: true }
      },
      {
        path: "/",
        component: WorkspaceLayout,
        meta: { requiresAuth: true },
        children: [
          {
            path: "drill",
            name: "drill",
            component: LiveDemoView,
            meta: { title: "故障演练", guestEntry: true }
          },
          {
            path: "chat",
            name: "chat",
            component: ChatView,
            meta: { title: "对话" }
          },
          {
            path: "knowledge",
            name: "knowledge",
            component: KnowledgeView,
            meta: { title: "知识库" }
          },
          {
            path: "aiops",
            name: "aiops",
            component: AiopsView,
            meta: { title: "智能诊断" }
          },
          {
            path: "mcp",
            name: "mcp",
            component: McpView,
            meta: { title: "MCP 连接" }
          }
        ]
      },
      { path: "/:pathMatch(.*)*", redirect: "/chat" }
    ]
  });

  let initialization: Promise<void> | null = null;
  router.beforeEach(async (to) => {
    initialization ??= auth.initialize();
    await initialization;
    const requiresAuth = to.matched.some((record) => record.meta.requiresAuth === true);
    const publicOnly = to.matched.some((record) => record.meta.publicOnly === true);
    if (requiresAuth && !auth.isAuthenticated()) {
      const guestEntry = to.matched.some((record) => record.meta.guestEntry === true);
      if (guestEntry && auth.enterAsGuest !== undefined) {
        try {
          await auth.enterAsGuest();
          return true;
        } catch {
          return { path: "/login", query: { redirect: to.fullPath } };
        }
      }
      return { path: "/login", query: { redirect: to.fullPath } };
    }
    if (publicOnly && auth.isAuthenticated()) {
      return { path: "/chat" };
    }
    return true;
  });

  return router;
}
