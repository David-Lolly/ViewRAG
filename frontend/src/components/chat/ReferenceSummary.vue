<template>
  <div v-if="groups.length > 0" class="reference-summary mt-3">
    <!-- 折叠/展开头部 -->
    <button
      class="flex items-center space-x-1.5 text-sm text-gray-500 hover:text-gray-700 transition-colors duration-150"
      @click="expanded = !expanded"
    >
      <svg
        class="w-4 h-4 transition-transform duration-200"
        :class="{ 'rotate-90': expanded }"
        fill="none" stroke="currentColor" viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
      </svg>
      <span class="font-medium">📎 引用来源</span>
      <span class="px-1.5 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">{{ totalCount }}</span>
    </button>

    <!-- 分组列表 -->
    <Transition name="summary-expand">
      <div v-if="expanded" class="mt-2 pl-2 border-l-2 border-gray-200 space-y-3">
        <div v-for="group in groups" :key="group.doc_id">
          <!-- 文档名 -->
          <div class="flex items-center space-x-1.5 mb-1">
            <svg class="w-3.5 h-3.5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            <span class="text-xs font-medium text-gray-700 truncate">{{ group.file_name }}</span>
          </div>

          <!-- 引用项列表 -->
          <div class="space-y-1 pl-5">
            <button
              v-for="item in group.items"
              :key="item.ref_id"
              class="w-full text-left flex items-start space-x-2 px-2 py-1.5 rounded hover:bg-blue-50 transition-colors duration-150 group/item"
              @click="$emit('open-pdf', item)"
            >
              <span class="text-xs font-semibold text-blue-600 flex-shrink-0">[{{ item.ref_id }}]</span>
              <span class="text-xs text-gray-500 flex-shrink-0">{{ formatPageRange(item.chunk_bboxes) }}</span>
              <span class="text-xs text-gray-600 truncate group-hover/item:text-blue-700 transition-colors duration-150">
                {{ getItemLabel(item) }}
              </span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const TEXT_PREVIEW_LENGTH = 60

const props = defineProps({
  /** 引用列表 ReferenceItem[] */
  references: { type: Array, default: () => [] },
  /** 是否显示 */
  visible: { type: Boolean, default: true }
})

defineEmits(['open-pdf'])

const expanded = ref(true)

/** 按文档分组 */
const groups = computed(() => {
  if (!props.visible || !props.references || props.references.length === 0) return []

  const map = new Map()
  for (const item of props.references) {
    if (!map.has(item.doc_id)) {
      map.set(item.doc_id, {
        doc_id: item.doc_id,
        file_name: item.file_name,
        items: []
      })
    }
    map.get(item.doc_id).items.push(item)
  }
  return Array.from(map.values())
})

/** 引用总数 */
const totalCount = computed(() => props.references ? props.references.length : 0)

/**
 * 格式化页码范围
 * @param {Array<{page: number}>} bboxes
 * @returns {string}
 */
function formatPageRange(bboxes) {
  if (!bboxes || bboxes.length === 0) return ''
  const pages = [...new Set(bboxes.map(b => b.page))].sort((a, b) => a - b)
  if (pages.length === 1) return `P${pages[0]}`
  return `P${pages[0]}-P${pages[pages.length - 1]}`
}

/**
 * 获取引用项的简短描述
 * @param {Object} item - ReferenceItem
 * @returns {string}
 */
function getItemLabel(item) {
  if (item.chunk_type === 'IMAGE') {
    return item.retrieval_text || '图片'
  }
  if (item.chunk_type === 'TABLE') {
    return item.retrieval_text || '表格'
  }
  // TEXT
  const text = item.retrieval_text || item.content || ''
  if (text.length <= TEXT_PREVIEW_LENGTH) return text
  return text.slice(0, TEXT_PREVIEW_LENGTH) + '...'
}
</script>

<style scoped>
.summary-expand-enter-active {
  transition: all 0.2s ease-out;
}
.summary-expand-leave-active {
  transition: all 0.15s ease-in;
}
.summary-expand-enter-from,
.summary-expand-leave-to {
  opacity: 0;
  max-height: 0;
  overflow: hidden;
}
.summary-expand-enter-to,
.summary-expand-leave-from {
  opacity: 1;
  max-height: 500px;
}
</style>
