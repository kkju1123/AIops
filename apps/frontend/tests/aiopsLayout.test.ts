import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const aiopsViewSource = readFileSync(
  fileURLToPath(new URL("../src/views/AiopsView.vue", import.meta.url)),
  "utf8"
);
const reportPanelSource = readFileSync(
  fileURLToPath(new URL("../src/components/AiopsReportPanel.vue", import.meta.url)),
  "utf8"
);
describe("AIOps vertical workspace layout", () => {
  it("uses one page scroll and renders downstream surfaces only for an active task", () => {
    expect(aiopsViewSource).toMatch(
      /\.aiops-view\s*\{[^}]*display:\s*block;[^}]*overflow-y:\s*auto;/s
    );
    expect(aiopsViewSource).toMatch(/\.aiops-view__console\s*\{[^}]*display:\s*block;[^}]*overflow:\s*visible;/s);
    expect(aiopsViewSource).toContain('v-if="hasActiveTask"');
    expect(aiopsViewSource).toContain('v-else class="aiops-view__start-note"');
    expect(aiopsViewSource).toContain('entryMode === \'describe\'');
    expect(aiopsViewSource).toContain('entryMode === \'alerts\'');
    expect(aiopsViewSource).toContain("AiopsHistory v-else");
  });

  it("keeps long reports bounded on desktop without creating horizontal columns", () => {
    expect(aiopsViewSource).toMatch(/\.aiops-view__task :deep\(\.aiops-report__document\)\s*\{[^}]*max-height:\s*44rem;[^}]*min-height:\s*20rem;/s);
    expect(aiopsViewSource).not.toContain("@media (max-width: 1600px)");
  });

  it("keeps advanced JSON optional and uses structured context fields", () => {
    expect(aiopsViewSource).toContain("描述问题");
    const runFormSource = readFileSync(
      fileURLToPath(new URL("../src/components/AiopsRunForm.vue", import.meta.url)),
      "utf8"
    );
    expect(runFormSource).toContain("服务名称");
    expect(runFormSource).toContain("严重程度");
    expect(runFormSource).toContain("运行环境");
    expect(runFormSource).toContain("高级：添加 JSON 上下文");
  });

  it("keeps report metadata fixed and scrolls only the Markdown body", () => {
    expect(reportPanelSource).toMatch(
      /\.aiops-report\s*\{[^}]*grid-template-rows:\s*auto minmax\(0, 1fr\);[^}]*overflow:\s*hidden;/s
    );
    expect(reportPanelSource).toMatch(
      /\.aiops-report__document\s*\{[^}]*grid-template-rows:\s*auto minmax\(0, 1fr\) auto;[^}]*overflow:\s*hidden;/s
    );
    expect(reportPanelSource).toMatch(
      /\.aiops-report__document > :deep\(\.markdown-content\)\s*\{[^}]*overflow-y:\s*auto;/s
    );
  });
});
