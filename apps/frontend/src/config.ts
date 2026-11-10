/**
 * 前端运行时配置。
 *
 * 这里刻意不 import config/*.json：整份配置包含 LLM API Key 与云凭据，
 * 一旦被打包器引入就会泄露到浏览器。公开字段由 vite.config.ts 在启动/构建
 * 时读取本地 JSON 后写入 VITE_API_BASE_URL，这里只读这一个字段。
 */

const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const API_BASE_URL = resolveApiBaseUrl(
  normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL)
);

function normalizeApiBaseUrl(value: unknown): string {
  return typeof value === "string" && value.trim().length > 0
    ? value.trim()
    : DEFAULT_API_BASE_URL;
}

export function resolveApiBaseUrl(apiBaseUrl: string): string {
  return apiBaseUrl.trim().replace(/\/+$/, "");
}
