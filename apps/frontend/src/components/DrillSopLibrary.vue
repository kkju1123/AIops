<script setup lang="ts">
import type { LiveDemoSopDocument, LiveDemoSopDocumentDetail } from "@agent-py/api-contracts";
import { BookOpen, FileText, Lock, Search } from "lucide-vue-next";
import { computed, onMounted, ref } from "vue";

import { createLiveDemoClient, type LiveDemoClient } from "../liveDemo/liveDemoClient";
import { toUserFacingError } from "../ui/userFacingError";
import AppErrorState from "./AppErrorState.vue";
import AppLoadingState from "./AppLoadingState.vue";
import MarkdownContent from "./MarkdownContent.vue";

const props = defineProps<{ readonly client?: LiveDemoClient }>();
const client = props.client ?? createLiveDemoClient();

const documents = ref<readonly LiveDemoSopDocument[]>([]);
const selected = ref<LiveDemoSopDocumentDetail | null>(null);
const isLoading = ref(true);
const isOpening = ref(false);
const errorMessage = ref<string | null>(null);
const query = ref("");

const filtered = computed(() => {
  const keyword = query.value.trim().toLocaleLowerCase();
  if (keyword.length === 0) return documents.value;
  return documents.value.filter((item) => item.filename.toLocaleLowerCase().includes(keyword));
});

onMounted(() => { void load(); });

async function load(): Promise<void> {
  isLoading.value = true;
  errorMessage.value = null;
  try {
    documents.value = (await client.listSopDocuments()).items;
    const first = documents.value[0];
    if (first !== undefined) await open(first.id);
  } catch (error) {
    errorMessage.value = toUserFacingError(error);
  } finally {
    isLoading.value = false;
  }
}

async function open(documentId: string): Promise<void> {
  isOpening.value = true;
  try {
    selected.value = await client.getSopDocument(documentId);
  } catch (error) {
    errorMessage.value = toUserFacingError(error);
  } finally {
    isOpening.value = false;
  }
}

function formatSize(bytes: number): string {
  return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`;
}
</script>

<template>
  <section class="sop-library" aria-label="演练 SOP 库">
    <header class="sop-library__header">
      <div>
        <p><BookOpen :size="14" aria-hidden="true" />演练环境知识库</p>
        <h2>故障演练检索的 SOP</h2>
        <span>智能诊断的第一步会用 pgvector 向量召回 + BM25 关键词召回、RRF 融合与 BGE 重排检索这些文档。</span>
      </div>
      <strong class="sop-library__readonly"><Lock :size="13" aria-hidden="true" />访客只读</strong>
    </header>

    <AppLoadingState v-if="isLoading" label="正在加载演练 SOP" />
    <AppErrorState v-else-if="errorMessage !== null && documents.length === 0" :can-retry="true" :message="errorMessage" @retry="load" />
    <p v-else-if="documents.length === 0" class="sop-library__empty">演练服务账号还没有 SOP 文档。</p>
    <div v-else class="sop-library__body">
      <nav class="sop-library__list" aria-label="SOP 文档">
        <label class="sop-library__search"><Search :size="14" aria-hidden="true" /><input v-model="query" type="search" placeholder="搜索 SOP" aria-label="搜索 SOP 文档" /></label>
        <ul>
          <li v-for="item in filtered" :key="item.id">
            <button type="button" :aria-current="selected?.id === item.id ? 'true' : undefined" :class="{ 'is-active': selected?.id === item.id }" @click="open(item.id)">
              <FileText :size="15" aria-hidden="true" />
              <span><strong>{{ item.filename }}</strong><small>{{ formatSize(item.sizeBytes) }} · 索引 {{ item.indexStatus }}</small></span>
            </button>
          </li>
        </ul>
        <p v-if="filtered.length === 0" class="sop-library__empty">没有匹配的文档。</p>
      </nav>
      <article class="sop-library__document" :aria-busy="isOpening" aria-label="SOP 正文">
        <template v-if="selected !== null">
          <header><FileText :size="16" aria-hidden="true" /><strong>{{ selected.filename }}</strong></header>
          <MarkdownContent :content="selected.content" mode="report" />
        </template>
      </article>
    </div>
  </section>
</template>

<style scoped>
.sop-library { background: var(--surface-raised); display: flex; flex-direction: column; height: 100%; min-height: 0; overflow: hidden; }
.sop-library__header { align-items: flex-start; border-bottom: 1px solid var(--line); display: flex; gap: 1rem; justify-content: space-between; padding: 1rem clamp(1rem, 3vw, 2rem); }
.sop-library__header p { align-items: center; color: var(--text-tertiary); display: flex; font-size: 0.68rem; font-weight: 700; gap: 0.35rem; letter-spacing: 0.04em; margin: 0 0 0.3rem; }
.sop-library__header h2 { font-size: 1.1rem; margin: 0; }
.sop-library__header span { color: var(--text-secondary); display: block; font-size: 0.74rem; line-height: 1.6; margin-top: 0.35rem; max-width: 46rem; }
.sop-library__readonly { align-items: center; border: 1px solid var(--status-waiting-border); color: var(--status-waiting-text); display: inline-flex; flex: 0 0 auto; font-size: 0.66rem; gap: 0.3rem; padding: 0.2rem 0.45rem; }
.sop-library__body { display: grid; flex: 1; grid-template-columns: minmax(14rem, 20rem) minmax(0, 1fr); min-height: 0; }
.sop-library__list { border-right: 1px solid var(--line); min-height: 0; overflow-y: auto; padding: 0.75rem; }
.sop-library__search { align-items: center; border: 1px solid var(--line-strong); color: var(--text-tertiary); display: flex; gap: 0.4rem; margin-bottom: 0.5rem; padding: 0 0.55rem; }
.sop-library__search input { background: transparent; border: 0; color: var(--text-primary); flex: 1; font: inherit; font-size: 0.78rem; min-height: 2.3rem; min-width: 0; outline: none; }
.sop-library__list ul { display: grid; gap: 0.15rem; list-style: none; margin: 0; padding: 0; }
.sop-library__list button { align-items: center; color: var(--text-secondary); display: flex; gap: 0.55rem; min-height: 3.2rem; padding: 0.45rem 0.55rem; text-align: left; width: 100%; }
.sop-library__list button:hover { background: var(--surface-hover); color: var(--text-primary); }
.sop-library__list button.is-active { background: var(--accent-soft); color: var(--accent-strong); }
.sop-library__list button > span { display: grid; min-width: 0; }
.sop-library__list strong { font-size: 0.78rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sop-library__list small { color: var(--text-tertiary); font-size: 0.66rem; margin-top: 0.15rem; }
.sop-library__document { min-height: 0; min-width: 0; overflow-wrap: anywhere; overflow-y: auto; padding: 1rem clamp(1rem, 3vw, 2rem) 2rem; }
.sop-library__document > header { align-items: center; border-bottom: 1px solid var(--line); color: var(--text-secondary); display: flex; font-size: 0.8rem; gap: 0.45rem; margin-bottom: 1rem; padding-bottom: 0.65rem; }
.sop-library__empty { color: var(--text-tertiary); font-size: 0.8rem; margin: 1rem clamp(1rem, 3vw, 2rem); }
@media (max-width: 760px) {
  .sop-library { height: auto; overflow: visible; }
  .sop-library__header { flex-direction: column; }
  .sop-library__body { display: block; }
  .sop-library__list { border-bottom: 1px solid var(--line); border-right: 0; max-height: 16rem; }
  .sop-library__document { overflow: visible; }
}
</style>
