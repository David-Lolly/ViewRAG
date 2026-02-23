<template>
  <Teleport to="body">
    <Transition name="panel-slide">
      <div v-if="visible" class="fixed inset-0 z-[9998]" @click.self="$emit('close')">
        <!-- 右侧面板 -->
        <div class="absolute top-[10%] right-[2%] h-[80%] w-[340px] bg-gray-50 shadow-2xl flex flex-col rounded-2xl">
          <!-- 头部 -->
          <div class="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-100 rounded-t-2xl">
            <h3 class="text-sm font-semibold text-gray-900">全部参考资料</h3>
            <button
              @click="$emit('close')"
              class="w-7 h-7 flex items-center justify-center rounded-full hover:bg-gray-100 transition-colors duration-150"
            >
              <svg class="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- 文档列表 -->
          <div class="flex-1 overflow-y-auto px-3 py-3 space-y-2.5">
            <div
              v-for="(doc, index) in documents"
              :key="doc.doc_id"
              class="doc-card bg-white rounded-xl border border-gray-200/80 hover:border-gray-300 hover:shadow-sm transition-all duration-200 cursor-pointer overflow-hidden"
              @click="$emit('open-doc', doc)"
            >
              <div class="px-3.5 pt-3 pb-3">
                <!-- 文档标题 -->
                <h4 class="text-[13px] font-medium text-gray-900 leading-snug mb-1.5 line-clamp-2">
                  {{ index + 1 }}. {{ doc.file_name }}
                </h4>

                <!-- 摘要（仅当存在时显示，最多128字符） -->
                <p v-if="doc.summary && doc.summary.trim()" 
                   class="text-xs text-gray-500 leading-relaxed line-clamp-2">
                  {{ truncateSummary(doc.summary) }}
                </p>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-if="!documents || documents.length === 0" class="flex flex-col items-center justify-center py-12 text-gray-400">
              <svg class="w-10 h-10 mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p class="text-xs">暂无参考资料</p>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
defineProps({
  /** 是否显示面板 */
  visible: { type: Boolean, default: false },
  /** 召回的文档列表 */
  documents: { type: Array, default: () => [] }
})

defineEmits(['close', 'open-doc'])

/**
 * 截取摘要前128个字符
 */
function truncateSummary(summary) {
  if (!summary) return ''
  return summary.length > 128 ? summary.substring(0, 128) + '...' : summary
}
</script>

<style scoped>
/* 面板滑入动画 */
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

.doc-card:hover {
  background-color: #ffffff;
  transform: translateY(-1px);
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
