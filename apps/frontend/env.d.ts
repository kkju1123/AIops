/// <reference types="vite/client" />

/** 由 vite.config.ts 的 define 在构建期注入的公开 API 地址。 */
declare const __API_BASE_URL__: string;

declare module "*.vue" {
  import type { DefineComponent } from "vue";

  const component: DefineComponent<object, object, unknown>;
  export default component;
}
