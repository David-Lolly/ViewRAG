<template>
  <Teleport to="body">
    <Transition name="popup-fade">
      <div
        v-if="visible"
        ref="popupEl"
        class="preview-popup fixed z-50 bg-white rounded-lg shadow-floating border border-gray-200 w-80 max-h-96 overflow-hidden"
        :style="popupStyle"
        @mouseenter="onPopupMouseEnter"
        @mouseleave="onPopupMouseLeave"
      >
        <!-- 头部：文档名 + 页码 -->
        <div class="flex items-center justify-between px-3 py-2 bg-gray-50 border-b border-gray-100">
          <div class="flex items-center space-x-1.5 min-w-0">
            <svg class="w-4 h-4 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            <span class="text-xs text-text-secondary truncate">{{ reference.file_name }}</span>
          </div>
          <span class="text-xs text-text-secondary flex-shrink-0 ml-2">{{ pageRangeText }}</span>
        </div>

        <!-- 内容区域 -->
        <div class="p-3">
          <!-- TEXT 类型：截断文本 -->
          <div v-if="reference.chunk_type === 'TEXT'" class="text-sm text-text-primary leading-relaxed">
            {{ truncatedContent }}
          </div>

          <!-- IMAGE 类型：缩略图 + 描述 -->
          <div v-else-if="reference.chunk_type === 'IMAGE'" class="space-y-2">
            <img
              :src="reference.image_url"
              :alt="reference.retrieval_text"
              class="w-full max-h-48 object-contain rounded border border-gray-100 bg-gray-50"
            />
            <p class="text-xs text-text-secondary leading-relaxed">{{ reference.retrieval_text }}</p>
          </div>

          <!-- TABLE 类型：可滚动表格 -->
          <div v-else-if="reference.chunk_type === 'TABLE'"
            class="text-sm overflow-auto max-h-48 prose prose-sm"
            v-html="tableHtml"
          ></div>
        </div>

        <!-- 底部：查看原文按钮 -->
        <div class="px-3 py-2 border-t border-gray-100 bg-gray-50">
          <button
            class="w-full text-center text-xs text-blue-600 hover:text-blue-700 font-medium py-1 rounded hover:bg-blue-50 transition-colors duration-150"
            @click="$emit('open-pdf')"
          >
            查看原文 →
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref } from 'vue'
import { marked } from 'marked'

const TEXT_MAX_LENGTH = 200

const props = defineProps({
  /** 引用数据 ReferenceItem */
  reference: { type: Object, required: true },
  /** 弹窗定位 { x, y } */
  position: { type: Object, default: () => ({ x: 0, y: 0 }) },
  /** 是否可见 */
  visible: { type: Boolean, default: false }
})

const emit = defineEmits(['open-pdf', 'close', 'mouseenter', 'mouseleave'])

const popupEl = ref(null)

/** 计算页码范围文本 */
const pageRangeText = computed(() => {
  const bboxes = props.reference.chunk_bboxes
  if (!bboxes || bboxes.length === 0) return ''
  const pages = [...new Set(bboxes.map(b => b.page))].sort((a, b) => a - b)
  if (pages.length === 1) return `P${pages[0]}`
  return `P${pages[0]}-P${pages[pages.length - 1]}`
})

/** TEXT 类型截断内容 */
const truncatedContent = computed(() => {
  const content = props.reference.content || ''
  if (content.length <= TEXT_MAX_LENGTH) return content
  return content.slice(0, TEXT_MAX_LENGTH) + '...'
})

/** TABLE 类型渲染为 HTML */
const tableHtml = computed(() => {
  if (props.reference.chunk_type !== 'TABLE') return ''
  return marked(props.reference.content || '')
})

/** 弹窗定位样式 */
const popupStyle = computed(() => ({
  left: `${props.position.x}px`,
  top: `${props.position.y}px`
}))

function onPopupMouseEnter() {
  emit('mouseenter')
}

function onPopupMouseLeave() {
  emit('mouseleave')
}
</script>

<style scoped>
.preview-popup {
  animation: popup-slide-in 0.15s ease-out;
}

/* 过渡动画 */
.popup-fade-enter-active {
  transition: opacity 0.15s ease-out, transform 0.15s ease-out;
}
.popup-fade-leave-active {
  transition: opacity 0.1s ease-in, transform 0.1s ease-in;
}
.popup-fade-enter-from {
  opacity: 0;
  transform: translateY(4px);
}
.popup-fade-leave-to {
  opacity: 0;
  transform: translateY(2px);
}

@keyframes popup-slide-in {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 表格样式覆盖 */
.preview-popup :deep(table) {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.75rem;
}
.preview-popup :deep(th),
.preview-popup :deep(td) {
  border: 1px solid #e5e7eb;
  padding: 0.375rem 0.5rem;
  text-align: left;
}
.preview-popup :deep(th) {
  background-color: #f9fafb;
  font-weight: 600;
}
</style>
