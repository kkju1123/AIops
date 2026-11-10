import { readFileSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";

import vue from "@vitejs/plugin-vue";
import { defineConfig } from "vitest/config";

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

/**
 * 只把 frontend.apiBaseUrl 暴露给前端。
 *
 * 之前 config.ts 直接 import config/project.json 与 config/user.project.json，
 * 会把 llm.apiKey、CLS 凭据等整份配置打进浏览器 bundle。这里在启动/构建时
 * 读取本地 JSON、仅取公开字段，写入 VITE_API_BASE_URL，前端通过
 * import.meta.env 读取。dev 与 build 都生效（vite 的 define 只在 build 生效）。
 */
function resolvePublicApiBaseUrl(): string {
  const configDir = fileURLToPath(new URL("../../config/", import.meta.url));
  const merged: Record<string, unknown> = {};
  for (const name of ["project.json", "user.project.json"]) {
    try {
      const parsed: unknown = JSON.parse(readFileSync(configDir + name, "utf8"));
      if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed)) {
        Object.assign(merged, parsed as Record<string, unknown>);
      }
    } catch {
      // 本地覆盖文件缺失或损坏时退回默认值，不阻断构建。
    }
  }
  const frontend = merged["frontend"];
  if (frontend !== null && typeof frontend === "object") {
    const value = (frontend as Record<string, unknown>)["apiBaseUrl"];
    if (typeof value === "string" && value.trim().length > 0) {
      return value.trim().replace(/\/+$/, "");
    }
  }
  return DEFAULT_API_BASE_URL;
}

process.env["VITE_API_BASE_URL"] = resolvePublicApiBaseUrl();

export default defineConfig({
  plugins: [vue()],
  envPrefix: "VITE_",
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "@agent-py/api-contracts": fileURLToPath(
        new URL("../../packages/api-contracts/src/index.ts", import.meta.url)
      )
    }
  },
  test: {
    include: ["tests/**/*.test.ts"]
  }
});
