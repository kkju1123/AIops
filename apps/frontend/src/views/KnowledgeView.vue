<script setup lang="ts">
import { AlertTriangle, ChevronDown, Database, FileText, FileWarning, Search, SearchX, Upload } from "lucide-vue-next";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import type { DocumentIndexTask, KnowledgeDocument } from "@agent-py/api-contracts";

import AppErrorState from "../components/AppErrorState.vue";
import AppLoadingState from "../components/AppLoadingState.vue";
import DrillSopLibrary from "../components/DrillSopLibrary.vue";
import KnowledgeDocumentList from "../components/KnowledgeDocumentList.vue";
import KnowledgeUpload from "../components/KnowledgeUpload.vue";
import { useAuthStore } from "../stores/auth";
import { useKnowledgeStore } from "../stores/knowledge";

const knowledge = useKnowledgeStore();
const auth = useAuthStore();
const route = useRoute();
const pendingDeletion = ref<KnowledgeDocument | null>(null);
const isUploadOpen = ref(false);
const documentQuery = ref("");
const filteredDocuments = computed(() => {
  const query = documentQuery.value.trim().toLocaleLowerCase();
  if (query.length === 0) return knowledge.documents;
  return knowledge.documents.filter((document) => document.filename.toLocaleLowerCase().includes(query));
});
const documentCountLabel = computed(() => {
  if (documentQuery.value.trim().length === 0) return `${knowledge.documents.length} 份文档`;
  return `${filteredDocuments.value.length} / ${knowledge.documents.length} 份文档`;
});

onMounted(() => {
  if (auth.isGuest) return;
  void initializeFromCitation().catch(() => undefined);
});
onBeforeUnmount(() => { knowledge.stopPolling(); });

function run(operation: () => Promise<unknown>): void { void operation().catch(() => undefined); }
function openDocument(document: KnowledgeDocument): void { run(() => knowledge.openDocument(document)); }

async function initializeFromCitation(): Promise<void> {
  await knowledge.initialize();
  const knowledgeBaseId = route.query.knowledgeBaseId;
  if (typeof knowledgeBaseId === "string" && knowledgeBaseId !== knowledge.selectedKnowledgeBaseId) {
    await knowledge.selectKnowledgeBase(knowledgeBaseId);
  }
  const documentId = route.query.documentId;
  if (typeof documentId !== "string") return;
  const document = knowledge.documents.find((item) => item.id === documentId);
  if (document !== undefined) await knowledge.openDocument(document);
}

function confirmDelete(): void {
  const document = pendingDeletion.value;
  if (document === null) return;
  run(async () => {
    await knowledge.deleteDocument(document);
    pendingDeletion.value = null;
  });
}

function uploadDocument(file: File, chunking: import("@agent-py/api-contracts").DocumentChunkingConfiguration): void {
  run(() => knowledge.upload(file, chunking));
}
</script>

<template>
  <DrillSopLibrary v-if="auth.isGuest" />
  <section v-else class="knowledge-view" aria-label="知识库工作区">
    <header class="knowledge-view__header">
      <p>管理用于对话和智能诊断的知识来源。</p>
      <div class="knowledge-view__header-actions"><label v-if="knowledge.knowledgeBases.length > 1" class="knowledge-view__base"><span>当前知识库</span><select :value="knowledge.selectedKnowledgeBaseId ?? ''" :disabled="knowledge.isLoading" aria-label="当前知识库" @change="run(() => knowledge.selectKnowledgeBase(($event.target as HTMLSelectElement).value))"><option v-for="base in knowledge.knowledgeBases" :key="base.id" :value="base.id">{{ base.name }}</option></select></label><button v-if="knowledge.documents.length > 0 || isUploadOpen" type="button" :aria-expanded="isUploadOpen" aria-controls="knowledge-upload-panel" @click="isUploadOpen = !isUploadOpen"><Upload :size="16" aria-hidden="true" />{{ isUploadOpen ? '收起上传' : '上传文档' }}<ChevronDown :size="15" :class="{ 'knowledge-view__chevron--open': isUploadOpen }" aria-hidden="true" /></button></div>
    </header>

    <AppLoadingState v-if="knowledge.isLoading && knowledge.documents.length === 0" label="正在加载知识库" />
    <AppErrorState v-else-if="knowledge.errorMessage && knowledge.documents.length === 0" :can-retry="true" :message="knowledge.errorMessage" @retry="run(knowledge.initialize)" />
    <template v-else>
      <KnowledgeUpload v-if="isUploadOpen" id="knowledge-upload-panel" :disabled="knowledge.isUploading || knowledge.selectedKnowledgeBaseId === null" :is-uploading="knowledge.isUploading" @upload="uploadDocument" />
      <section v-if="knowledge.pendingOverwriteFile" class="knowledge-view__confirmation" role="alert"><FileWarning :size="18" aria-hidden="true" /><div><strong>发现同名文档</strong><p>{{ knowledge.pendingOverwriteFile.name }} 会替换现有文档及其向量数据。</p></div><div><button type="button" @click="knowledge.clearPendingOverwrite">取消</button><button type="button" class="knowledge-view__danger-command" @click="run(knowledge.overwritePendingUpload)">确认替换</button></div></section>
      <div class="knowledge-view__body">
        <section class="knowledge-view__documents" aria-labelledby="knowledge-documents-heading">
          <header v-if="knowledge.documents.length > 0"><div><p>文档</p><h3 id="knowledge-documents-heading">{{ documentCountLabel }}</h3></div><label class="knowledge-view__search"><Search :size="15" aria-hidden="true" /><input v-model="documentQuery" type="search" placeholder="搜索文档" aria-label="搜索知识文档" /></label></header>
          <section v-if="knowledge.documents.length === 0 && !isUploadOpen" class="knowledge-view__empty" aria-labelledby="knowledge-documents-heading"><FileText :size="28" aria-hidden="true" /><h2 id="knowledge-documents-heading">还没有文档</h2><p>上传 SOP、故障复盘或运行手册，让模型在对话和诊断中引用可靠来源。</p><button type="button" @click="isUploadOpen = true"><Upload :size="16" aria-hidden="true" />开始上传</button><small>支持 Markdown 与 PDF，单个文件不超过 10 MB</small></section>
          <section v-else-if="knowledge.documents.length === 0" class="knowledge-view__upload-hint"><Database :size="20" aria-hidden="true" /><span><strong>文档列表</strong><small>上传完成并建立索引后，文档会显示在这里。</small></span></section>
          <section v-else-if="filteredDocuments.length === 0" class="knowledge-view__empty knowledge-view__empty--search"><SearchX :size="26" aria-hidden="true" /><h2>没有匹配的文档</h2><p>换一个关键词，或清除搜索条件后重试。</p><button type="button" @click="documentQuery = ''">清除搜索</button></section>
          <KnowledgeDocumentList v-else :documents="filteredDocuments" :index-tasks="knowledge.indexTasks" :preview="knowledge.chunkPreview" :selected-document="knowledge.selectedDocument" @close="knowledge.closeDocument" @delete="pendingDeletion = $event" @detail="openDocument" @rebuild="run(() => knowledge.rebuildDocumentIndex($event))" @retry="run(() => knowledge.retryIndexTask($event))" />
        </section>
      </div>
    </template>

    <section v-if="pendingDeletion" class="knowledge-view__confirmation knowledge-view__confirmation--delete" role="alertdialog" aria-label="确认删除文档"><AlertTriangle :size="18" aria-hidden="true" /><div><strong>删除 {{ pendingDeletion.filename }}？</strong><p>此操作会删除文档记录和已建立的向量索引。</p></div><div><button type="button" @click="pendingDeletion = null">取消</button><button type="button" class="knowledge-view__danger-command" @click="confirmDelete">确认删除</button></div></section>
  </section>
</template>

<style scoped>
.knowledge-view { background: var(--surface-raised); box-sizing: border-box; display: flex; flex-direction: column; height: 100%; min-height: 0; overflow: hidden; }
.knowledge-view__header { align-items: center; border-bottom: 1px solid var(--line); display: flex; gap: 1.5rem; justify-content: space-between; min-height: 4.25rem; padding: 0.75rem clamp(1rem, 3vw, 2rem); }
.knowledge-view__header > p { color: var(--text-secondary); font-size: 0.82rem; margin: 0; }
.knowledge-view__documents > header p { color: var(--text-tertiary); font-size: 0.72rem; font-weight: 700; margin: 0 0 0.25rem; }
.knowledge-view__base { display: grid; gap: 0.35rem; min-width: min(16rem, 100%); }
.knowledge-view__base > span { color: var(--text-tertiary); font-size: 0.7rem; font-weight: 700; }
.knowledge-view__header-actions { align-items: end; display: flex; gap: 0.65rem; }
.knowledge-view__header-actions > button { align-items: center; border: 1px solid var(--line-strong); display: inline-flex; gap: 0.4rem; min-height: 2.55rem; padding: 0 0.7rem; white-space: nowrap; }
.knowledge-view__header-actions > button svg:last-child { transition: transform var(--transition-fast); }
.knowledge-view__chevron--open { transform: rotate(180deg); }
select { background: var(--surface-raised); border: 1px solid var(--line-strong); border-radius: 0.45rem; color: var(--text-primary); min-height: 2.55rem; padding: 0 0.65rem; }
.knowledge-view__body { background: var(--surface-raised); display: grid; flex: 1 1 auto; min-height: 0; min-width: 0; overflow: hidden; }
.knowledge-view__documents { display: grid; grid-template-rows: auto minmax(0, 1fr); min-height: 0; min-width: 0; overflow: hidden; }
.knowledge-view__documents > header { align-items: center; border-bottom: 1px solid var(--line); display: flex; justify-content: space-between; min-height: 4.25rem; padding: 0.8rem 1rem; }
.knowledge-view__documents > header h3 { font-size: 0.98rem; font-weight: 680; margin: 0; }
.knowledge-view__search { align-items: center; border: 1px solid var(--line-strong); display: flex; gap: 0.4rem; margin-left: auto; min-height: 2.35rem; padding: 0 0.65rem; width: min(18rem, 42vw); }
.knowledge-view__search input { background: transparent; border: 0; color: var(--text-primary); min-width: 0; outline: 0; width: 100%; }
.knowledge-view__empty { align-content: center; align-items: center; display: grid; justify-items: center; margin: auto; max-width: 32rem; padding: 3rem 1.5rem; text-align: center; }
.knowledge-view__empty > svg { color: var(--text-tertiary); margin-bottom: 0.9rem; }
.knowledge-view__empty h2 { font-size: 1.05rem; margin: 0; }
.knowledge-view__empty p { color: var(--text-secondary); font-size: 0.82rem; line-height: 1.65; margin: 0.6rem 0 1.2rem; }
.knowledge-view__empty button { align-items: center; background: var(--accent); color: var(--on-accent); display: inline-flex; gap: 0.4rem; min-height: 2.5rem; padding: 0 0.85rem; }
.knowledge-view__empty small { color: var(--text-tertiary); font-size: 0.7rem; margin-top: 0.75rem; }
.knowledge-view__empty--search button { background: transparent; border-color: var(--line-strong); color: var(--text-primary); }
.knowledge-view__upload-hint { align-items: center; color: var(--text-tertiary); display: flex; gap: 0.65rem; padding: 1rem clamp(1rem, 3vw, 2rem); }
.knowledge-view__upload-hint span { display: grid; }
.knowledge-view__upload-hint strong { color: var(--text-secondary); font-size: 0.8rem; }
.knowledge-view__upload-hint small { font-size: 0.72rem; margin-top: 0.2rem; }
.knowledge-view__confirmation { align-items: center; background: var(--status-waiting-bg); border-bottom: 1px solid var(--status-waiting-border); display: grid; gap: 0.8rem; grid-template-columns: auto minmax(0, 1fr) auto; padding: 0.75rem 1rem; }
.knowledge-view__confirmation > svg { color: var(--status-waiting-text); }
.knowledge-view__confirmation strong { font-size: 0.84rem; }
.knowledge-view__confirmation p { color: var(--text-secondary); font-size: 0.78rem; margin: 0.25rem 0 0; }
.knowledge-view__confirmation > div:last-child { display: flex; gap: 0.45rem; }
.knowledge-view__confirmation button { border: 1px solid var(--line-strong); border-radius: 0.4rem; font-size: 0.78rem; min-height: 2rem; padding: 0 0.55rem; white-space: nowrap; }
.knowledge-view__confirmation button:hover { color: var(--accent-strong); }
.knowledge-view__confirmation .knowledge-view__danger-command { border-color: var(--danger); color: var(--danger); }
.knowledge-view__confirmation--delete { background: var(--danger-soft); border-color: var(--status-danger-border); }
@media (max-width: 680px) { .knowledge-view { height: auto; min-height: 100%; overflow-y: auto; } .knowledge-view__body { flex: 0 0 auto; overflow: visible; } .knowledge-view__documents { display: block; overflow: visible; } .knowledge-view__header { align-items: stretch; flex-direction: column; gap: 1rem; } .knowledge-view__header-actions { align-items: stretch; flex-direction: column; } .knowledge-view__base { min-width: 0; } .knowledge-view__search { width: min(14rem, 58vw); } .knowledge-view__confirmation { align-items: start; grid-template-columns: auto minmax(0, 1fr); } .knowledge-view__confirmation > div:last-child { flex-wrap: wrap; grid-column: 2; } }
</style>
