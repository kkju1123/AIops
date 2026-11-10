import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const workspaceSource = readFileSync(
  fileURLToPath(new URL("../src/layouts/WorkspaceLayout.vue", import.meta.url)),
  "utf8"
);
const chatSource = readFileSync(
  fileURLToPath(new URL("../src/views/ChatView.vue", import.meta.url)),
  "utf8"
);
const knowledgeSource = readFileSync(
  fileURLToPath(new URL("../src/views/KnowledgeView.vue", import.meta.url)),
  "utf8"
);
const aiopsSource = readFileSync(
  fileURLToPath(new URL("../src/views/AiopsView.vue", import.meta.url)),
  "utf8"
);
const mcpSource = readFileSync(
  fileURLToPath(new URL("../src/views/McpView.vue", import.meta.url)),
  "utf8"
);
const stylesSource = readFileSync(
  fileURLToPath(new URL("../src/styles.css", import.meta.url)),
  "utf8"
);
const navigationSource = readFileSync(
  fileURLToPath(new URL("../src/components/WorkspaceNavigation.vue", import.meta.url)),
  "utf8"
);
const chatSessionSource = readFileSync(
  fileURLToPath(new URL("../src/components/ChatSessionList.vue", import.meta.url)),
  "utf8"
);
describe("continuous desktop workspace", () => {
  it("lets routed content fill a single edge-to-edge application shell", () => {
    expect(workspaceSource).toMatch(
      /\.workspace-layout__main\s*\{[^}]*grid-template-rows:\s*auto minmax\(0, 1fr\);[^}]*height:\s*100dvh;/s
    );
    expect(workspaceSource).toMatch(/\.workspace-layout\s*\{[^}]*height:\s*100dvh;[^}]*overflow:\s*hidden;/s);
    expect(workspaceSource).not.toMatch(/\.workspace-layout\s*\{[^}]*(?:gap|padding):/s);
    expect(workspaceSource).toMatch(/\.workspace-layout__rail\s*\{[^}]*border-right:\s*1px solid var\(--line\);/s);
    expect(workspaceSource).toMatch(
      /\.workspace-layout__content\s*\{ height:\s*100%; min-height:\s*0; overflow:\s*hidden; width:\s*100%; \}/
    );
    expect(workspaceSource).not.toMatch(/\.workspace-layout__content\s*\{[^}]*max-width:/s);
  });

  it("lets every workspace page own the full routed surface", () => {
    expect(chatSource).toMatch(/\.chat-view\s*\{[^}]*height:\s*100%;[^}]*overflow:\s*hidden;/s);
    expect(chatSource).not.toMatch(/\.chat-view\s*\{[^}]*border-radius:/s);
    expect(knowledgeSource).toMatch(/\.knowledge-view\s*\{[^}]*height:\s*100%;[^}]*overflow:\s*hidden;/s);
    for (const source of [aiopsSource, mcpSource]) {
      expect(source).toMatch(/\.(?:aiops|mcp)-view\s*\{[^}]*height:\s*100%;[^}]*overflow-y:\s*auto;/s);
    }
    for (const source of [knowledgeSource, aiopsSource, mcpSource]) {
      expect(source).not.toMatch(/\.(?:knowledge|aiops|mcp)-view\s*\{[^}]*(?:gap|padding|border-radius|box-shadow):/s);
    }
  });

  it("uses structural dividers instead of floating page cards", () => {
    expect(knowledgeSource).not.toMatch(/\.knowledge-view__body\s*\{[^}]*(?:border-radius|box-shadow):/s);
    expect(aiopsSource).not.toMatch(/\.aiops-view__hero\s*\{[^}]*(?:border-radius|box-shadow):/s);
    expect(aiopsSource).not.toMatch(/\.aiops-view__left, \.aiops-view__center, \.aiops-view__right\s*\{[^}]*(?:border-radius|box-shadow):/s);
    expect(mcpSource).not.toMatch(/\.mcp-view__(?:header|workspace)\s*\{[^}]*(?:border-radius|box-shadow):/s);
  });

  it("keeps secondary controls collapsible and primary lists searchable", () => {
    expect(workspaceSource).toContain("workspace-layout--rail-collapsed");
    expect(workspaceSource).toContain("agent-py.rail-collapsed");
    expect(chatSource).toContain('aria-controls="chat-settings"');
    expect(chatSource).toContain("chat-view--settings-closed");
    expect(knowledgeSource).toContain('aria-controls="knowledge-upload-panel"');
    expect(knowledgeSource).toContain('aria-label="搜索知识文档"');
    expect(mcpSource).toContain('aria-label="搜索 MCP 连接"');
    expect(mcpSource).toMatch(/\.mcp-view__commands\s*\{[^}]*position:\s*static;/s);
    expect(mcpSource).not.toMatch(/\.mcp-view__commands\s*\{[^}]*position:\s*sticky;/s);
    expect(workspaceSource).toContain('savedRailState === null ? true');
    expect(workspaceSource).toMatch(/\.workspace-layout__status\s*\{[^}]*background:\s*transparent;[^}]*border:\s*0;/s);
  });

  it("stacks diagnostics and MCP management into a top-to-bottom flow", () => {
    expect(aiopsSource).toMatch(/\.aiops-view__console\s*\{[^}]*display:\s*block;/s);
    expect(mcpSource).toMatch(/\.mcp-view__workspace\s*\{[^}]*display:\s*block;/s);
    expect(mcpSource).toMatch(/\.mcp-view__editor\s*\{[^}]*display:\s*block;/s);
  });

  it("keeps MCP editing deliberate and long tool output bounded", () => {
    expect(mcpSource).toContain("当前修改尚未保存，确定要放弃吗？");
    expect(mcpSource).toContain("mcp.isSaving || !isDirty || !isValid");
    expect(mcpSource).toContain("isDirty ? '请先保存' : '检查连接'");
    expect(mcpSource).toMatch(/\.mcp-view__inspection ul\s*\{[^}]*max-height:\s*28rem;[^}]*overflow-y:\s*auto;/s);
    expect(mcpSource).toContain("<details>");
    expect(mcpSource).toContain("mcp-view__field-group-heading");
  });

  it("uses compact global radii and square sidebar navigation", () => {
    expect(stylesSource).toContain("--radius-sm: 0.25rem");
    expect(stylesSource).toContain("--radius-md: 0.375rem");
    expect(stylesSource).toContain("--radius-lg: 0.5rem");
    expect(stylesSource).toMatch(/button\s*\{[^}]*border-radius:\s*var\(--radius-sm\) !important;/s);
    expect(navigationSource).toMatch(/\.workspace-navigation__link\s*\{[^}]*border-radius:\s*0;/s);
    expect(chatSessionSource).toMatch(/\.chat-session-list__select\s*\{[^}]*border-radius:\s*0 !important;/s);
    expect(chatSessionSource).toMatch(/\.chat-session-list--rail \.chat-session-list__select--active\s*\{[^}]*box-shadow:\s*none;/s);
  });

  it("uses softened off-white text instead of luminous pure white", () => {
    expect(stylesSource).toContain("--text-primary: #d7dde0");
    expect(stylesSource).toContain("--text-secondary: #9da8ad");
    expect(stylesSource).toContain("--text-tertiary: #707d83");
    expect(stylesSource).not.toContain("--text-primary: #f4fbff");
    expect(stylesSource).not.toContain("color: #ffffff");
  });
});

describe("guest workspace shell", () => {
  const layoutSource = workspaceSource;

  it("shows the guest banner and fits five entries in the narrow navigation", () => {
    expect(layoutSource).toContain('v-if="auth.isGuest" class="workspace-layout__guest"');
    expect(layoutSource).toContain("故障模拟器生成");
    expect(layoutSource).toMatch(/workspace-navigation\) \{ display: grid; grid-template-columns: repeat\(5, minmax\(0, 1fr\)\); \}/);
  });

  it("hides MCP editing for guests", () => {
    expect(mcpSource).toContain('<main v-if="!auth.isGuest" class="mcp-view__editor">');
    expect(mcpSource).toContain('v-if="!auth.isGuest" type="button" title="新建连接"');
  });
});
