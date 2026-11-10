import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it, vi } from "vitest";

import { createAppRouter } from "../src/router";
import { useFeedbackStore } from "../src/stores/feedback";

describe("application shell router", () => {
  it("keeps the portfolio public and retires the static tour", async () => {
    const initialize = vi.fn().mockResolvedValue(undefined);
    const router = createAppRouter({ initialize, isAuthenticated: () => false });

    await router.push("/");
    await router.isReady();
    expect(router.currentRoute.value.name).toBe("portfolio");

    await router.push("/demo");
    expect(router.currentRoute.value.name).toBe("portfolio");
    expect(initialize).toHaveBeenCalledTimes(1);
  });

  it("creates a guest session when an anonymous visitor opens the drill", async () => {
    let authenticated = false;
    const enterAsGuest = vi.fn(async () => {
      authenticated = true;
    });
    const router = createAppRouter({
      enterAsGuest,
      initialize: vi.fn().mockResolvedValue(undefined),
      isAuthenticated: () => authenticated
    });

    await router.push("/live");
    await router.isReady();

    expect(enterAsGuest).toHaveBeenCalledTimes(1);
    expect(router.currentRoute.value.name).toBe("drill");
    expect(router.currentRoute.value.meta.title).toBe("故障演练");

    await router.push("/aiops");
    expect(router.currentRoute.value.name).toBe("aiops");
    expect(enterAsGuest).toHaveBeenCalledTimes(1);
  });

  it("falls back to sign-in when guest entry is unavailable", async () => {
    const router = createAppRouter({
      enterAsGuest: vi.fn().mockRejectedValue(new Error("访客模式当前未开启。")),
      initialize: vi.fn().mockResolvedValue(undefined),
      isAuthenticated: () => false
    });

    await router.push("/drill");
    await router.isReady();

    expect(router.currentRoute.value.path).toBe("/login");
    expect(router.currentRoute.value.query.redirect).toBe("/drill");
  });

  it("only auto-creates guests for drill routes", async () => {
    const enterAsGuest = vi.fn().mockResolvedValue(undefined);
    const router = createAppRouter({
      enterAsGuest,
      initialize: vi.fn().mockResolvedValue(undefined),
      isAuthenticated: () => false
    });

    await router.push("/mcp");
    await router.isReady();

    expect(enterAsGuest).not.toHaveBeenCalled();
    expect(router.currentRoute.value.path).toBe("/login");
  });

  it("redirects anonymous visitors to sign in and preserves the target route", async () => {
    const router = createAppRouter({
      initialize: vi.fn().mockResolvedValue(undefined),
      isAuthenticated: () => false
    });

    await router.push("/knowledge");
    await router.isReady();

    expect(router.currentRoute.value.path).toBe("/login");
    expect(router.currentRoute.value.query.redirect).toBe("/knowledge");
  });

  it("redirects authenticated visitors away from public auth routes", async () => {
    const router = createAppRouter({
      initialize: vi.fn().mockResolvedValue(undefined),
      isAuthenticated: () => true
    });

    await router.push("/register");
    await router.isReady();

    expect(router.currentRoute.value.path).toBe("/chat");
  });

  it("holds dismissible normalized feedback in application state", () => {
    setActivePinia(createPinia());
    const feedback = useFeedbackStore();

    feedback.showError("The system is temporarily unavailable.");
    expect(feedback.current?.message).toBe("The system is temporarily unavailable.");

    feedback.dismiss();
    expect(feedback.current).toBeNull();
  });
});
