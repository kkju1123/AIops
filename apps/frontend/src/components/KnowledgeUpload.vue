<script setup lang="ts">
import { ChevronDown, FileUp, LoaderCircle, SlidersHorizontal } from "lucide-vue-next";
import { computed, ref } from "vue";

import { DOCUMENT_UPLOAD_POLICY, type DocumentChunkingConfiguration } from "@agent-py/api-contracts";

import { supportedFormatsMessage, validateKnowledgeDocumentFile } from "../knowledge/documentPolicy";

const emit = defineEmits<{ upload: [file: File, chunking: DocumentChunkingConfiguration] }>();
const props = withDefaults(defineProps<{ readonly disabled: boolean; readonly isUploading?: boolean }>(), { isUploading: false });
const notice = ref<string | null>(null);
const strategy = ref<DocumentChunkingConfiguration["strategy"]>("fixed-character");
const maxCharacters = ref(1200);
const overlapCharacters = ref(200);
const fileInput = ref<HTMLInputElement | null>(null);
const usesFixedCharacter = computed(() => strategy.value === "fixed-character");
const strategyLabel = computed(() => {
  if (strategy.value === "markdown-heading") return "Markdown 标题";
  if (strategy.value === "paragraph") return "段落边界";
  return `${maxCharacters.value} 字符，重叠 ${overlapCharacters.value}`;
});

function openPicker(): void {
  if (props.disabled || props.isUploading) return;
  fileInput.value?.click();
}

function buildChunkingConfiguration(): DocumentChunkingConfiguration {
  if (strategy.value === "fixed-character") {
    return {
      strategy: "fixed-character",
      maxCharacters: maxCharacters.value,
      overlapCharacters: overlapCharacters.value
    };
  }
  if (strategy.value === "markdown-heading") {
    return { strategy: "markdown-heading" };
  }
  return { strategy: "paragraph" };
}

function selectFile(file: File | null | undefined): void {
  if (file === null || file === undefined || props.disabled) return;
  const validationMessage = validateKnowledgeDocumentFile(file);
  if (validationMessage !== null) {
    notice.value = validationMessage;
    return;
  }
  notice.value = null;
  emit("upload", file, buildChunkingConfiguration());
}

function onChange(event: Event): void {
  const input = event.target as HTMLInputElement;
  selectFile(input.files?.[0]);
  input.value = "";
}

function onDrop(event: DragEvent): void {
  event.preventDefault();
  selectFile(event.dataTransfer?.files[0]);
}
</script>

<template>
  <section class="knowledge-upload" :class="{ 'knowledge-upload--disabled': disabled }">
    <div class="knowledge-upload__dropzone" role="button" :tabindex="disabled ? -1 : 0" :aria-disabled="disabled || isUploading" @click="openPicker" @keydown.enter.prevent="openPicker" @keydown.space.prevent="openPicker" @dragover.prevent @drop="onDrop">
      <div class="knowledge-upload__icon"><LoaderCircle v-if="isUploading" class="knowledge-upload__spin" :size="22" aria-hidden="true" /><FileUp v-else :size="22" aria-hidden="true" /></div>
      <div class="knowledge-upload__copy">
        <h3>{{ isUploading ? "正在上传并建立索引" : "拖入文档，或点击选择文件" }}</h3>
        <p>{{ isUploading ? "文件已提交，完成后会自动出现在文档列表中。" : supportedFormatsMessage() }}</p>
        <p v-if="notice" class="knowledge-upload__notice" role="alert">{{ notice }}</p>
      </div>
      <span class="knowledge-upload__select">{{ isUploading ? "处理中" : "选择文件" }}</span>
      <input ref="fileInput" class="knowledge-upload__file-input" :accept="DOCUMENT_UPLOAD_POLICY.allowedExtensions.join(',')" :disabled="disabled" type="file" @change="onChange">
    </div>

    <details class="knowledge-upload__advanced">
      <summary><span><SlidersHorizontal :size="16" aria-hidden="true" /><strong>高级分片设置</strong><small>{{ strategyLabel }}</small></span><ChevronDown :size="16" aria-hidden="true" /></summary>
      <div class="knowledge-upload__settings">
        <label class="knowledge-upload__field">分片策略<select v-model="strategy" :disabled="disabled || isUploading"><option value="fixed-character">固定长度</option><option value="markdown-heading">Markdown 标题/章节</option><option value="paragraph">段落边界</option></select></label>
        <template v-if="usesFixedCharacter">
          <label class="knowledge-upload__field">每片最大字符<input v-model.number="maxCharacters" :disabled="disabled || isUploading" min="100" max="5000" type="number"><small>建议 800–1500</small></label>
          <label class="knowledge-upload__field">重叠字符<input v-model.number="overlapCharacters" :disabled="disabled || isUploading" min="0" :max="maxCharacters - 1" type="number"><small>必须小于每片最大字符</small></label>
        </template>
        <p v-else class="knowledge-upload__strategy-note">
          {{ strategy === "markdown-heading" ? "按 Markdown 标题组织分片，无需设置字符数和重叠参数。" : "按段落边界组织分片，无需设置字符数和重叠参数。" }}
        </p>
      </div>
    </details>
  </section>
</template>

<style scoped>
.knowledge-upload { background: var(--surface-raised); border-bottom: 1px solid var(--line); display: grid; padding: clamp(1rem, 2.5vw, 1.75rem); }
.knowledge-upload--disabled { opacity: 0.72; }
.knowledge-upload__dropzone { align-items: center; border: 1px dashed var(--line-strong); cursor: pointer; display: grid; gap: 0.9rem; grid-template-columns: auto minmax(0, 1fr) auto; min-height: 8rem; padding: 1.25rem; transition: border-color var(--transition-fast), background var(--transition-fast); }
.knowledge-upload__dropzone:hover, .knowledge-upload__dropzone:focus-visible { background: var(--surface-hover); border-color: var(--accent-border); outline: 0; }
.knowledge-upload__icon { align-items: center; background: var(--accent-soft); border-radius: var(--radius-sm); color: var(--accent-strong); display: inline-flex; height: 3rem; justify-content: center; width: 3rem; }
.knowledge-upload__copy { min-width: 0; }
h3 { font-size: 0.95rem; font-weight: 680; margin: 0; }
p { color: var(--text-secondary); font-size: 0.78rem; line-height: 1.55; margin: 0.25rem 0 0; }
.knowledge-upload__notice { color: var(--danger); }
.knowledge-upload__select { align-items: center; background: var(--accent); border: 1px solid var(--accent); border-radius: var(--radius-sm); color: var(--on-accent); display: inline-flex; font-size: 0.8rem; font-weight: 800; min-height: 2.4rem; padding: 0 0.8rem; white-space: nowrap; }
.knowledge-upload__file-input { height: 1px; opacity: 0; overflow: hidden; position: absolute; width: 1px; }
.knowledge-upload__advanced { border: 1px solid var(--line); border-top: 0; }
.knowledge-upload__advanced summary { align-items: center; cursor: pointer; display: flex; justify-content: space-between; list-style: none; min-height: 3rem; padding: 0.65rem 0.9rem; }
.knowledge-upload__advanced summary::-webkit-details-marker { display: none; }
.knowledge-upload__advanced summary > span { align-items: center; display: flex; gap: 0.45rem; min-width: 0; }
.knowledge-upload__advanced summary strong { font-size: 0.78rem; }
.knowledge-upload__advanced summary small { color: var(--text-tertiary); font-size: 0.7rem; font-weight: 500; }
.knowledge-upload__advanced summary > svg { transition: transform var(--transition-fast); }
.knowledge-upload__advanced[open] summary > svg { transform: rotate(180deg); }
.knowledge-upload__settings { border-top: 1px solid var(--line); display: grid; gap: 0.9rem; grid-template-columns: repeat(3, minmax(0, 1fr)); padding: 1rem; }
.knowledge-upload__field { color: var(--text-tertiary); display: grid; font-size: 0.68rem; font-weight: 700; gap: 0.2rem; }
.knowledge-upload__field select, .knowledge-upload__field input { background: var(--surface-raised); border: 1px solid var(--line-strong); color: var(--text-primary); font-size: 0.74rem; min-height: 2.25rem; padding: 0 0.45rem; }
.knowledge-upload__field small { color: var(--text-tertiary); font-size: 0.66rem; font-weight: 500; }
.knowledge-upload__strategy-note { color: var(--text-tertiary); font-size: 0.72rem; line-height: 1.45; margin: 0; padding: 0.48rem 0; }
.knowledge-upload__spin { animation: knowledge-upload-spin 0.9s linear infinite; }
@keyframes knowledge-upload-spin { to { transform: rotate(360deg); } }
@media (max-width: 720px) { .knowledge-upload__dropzone { grid-template-columns: auto minmax(0, 1fr); } .knowledge-upload__select { grid-column: 2; justify-self: start; } .knowledge-upload__settings { grid-template-columns: minmax(0, 1fr); } }
</style>
