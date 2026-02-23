<template>
  <Teleport to="body">
    <Transition name="panel-slide">
      <div v-if="visible" class="fixed inset-0 z-[9998]" @click.self="$emit('close')">
        <!-- 右侧面板 -->
        <div class="absolute top-[10%] right-[2%] h-[80%] w-[340px] bg-gray-50 shadow-2xl flex flex-col rounded-2xl">
          <!-- 头部 -->
          <div class="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-100 rounded-t-2xl">
            <h3 class="text-sm font-semibold text-gray-900">会话文件</h3>
            <button
              @click="$emit('close')"
              class="w-7 h-7 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors duration-150"
            >
              <svg class="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- 文件列表 -->
          <div class="flex-1 overflow-y-auto px-3 py-3 space-y-2">
            <div
              v-for="doc in documents"
              :key="doc.doc_id"
              class="flex items-center gap-3 px-3.5 py-3 bg-white rounded-xl border border-gray-200/80 hover:border-gray-300 hover:shadow-sm transition-all duration-200"
            >
              <!-- 文件类型图标 -->
              <div
                class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold"
                :class="getFileTypeInfo(doc.file_name).bgClass"
              >
                <span :class="getFileTypeInfo(doc.file_name).textClass">
                  {{ getFileTypeInfo(doc.file_name).label }}
                </span>
              </div>
              <!-- 文件名 -->
              <div class="flex-1 min-w-0">
                <div class="text-[13px] font-medium text-gray-900 truncate">{{ doc.file_name }}</div>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-if="!documents || documents.length === 0" class="flex flex-col items-center justify-center py-12 text-gray-400">
              <svg class="w-10 h-10 mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p class="text-xs">暂无文件</p>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { getFileTypeInfo } from '@/utils/fileTypeInfo.js'

defineProps({
  visible: { type: Boolean, default: false },
  documents: { type: Array, default: () => [] }
})

defineEmits(['close'])
</script>

<style scoped>
.panel-slide-enter-active {
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.panel-slide-leave-active {
  transition: all 0.2s ease-in;
}
.panel-slide-enter-from {
  opacity: 0;
}
.panel-slide-enter-from > div {
  transform: translateX(100%);
}
.panel-slide-leave-to {
  opacity: 0;
}
.panel-slide-leave-to > div {
  transform: translateX(100%);
}
</style>
