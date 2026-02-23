<template>
  <div class="document-list">
    <!-- 空状态 -->
    <div v-if="documents.length === 0" class="text-center py-12">
      <div class="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg class="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
        </svg>
      </div>
      <h3 class="text-lg font-semibold text-gray-700 mb-2">还没有文档</h3>
      <p class="text-sm text-gray-500">上传文档开始使用知识库</p>
    </div>

    <!-- 文档列表 -->
    <div v-else class="space-y-3">
      <div
        v-for="doc in documents"
        :key="doc.id"
        class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-all duration-200"
      >
        <!-- 文档头部：图标、名称、操作 -->
        <div class="flex items-start space-x-3">
          <!-- 文档类型图标 -->
          <div class="flex-shrink-0 mt-1">
            <img
              :src="getDocTypeIcon(doc.document_type)"
              :alt="doc.document_type"
              class="w-10 h-10"
            />
          </div>

          <!-- 文档信息 -->
          <div class="flex-1 min-w-0">
            <!-- 文档名称和状态 -->
            <div class="flex items-start justify-between mb-2">
              <div class="flex-1 min-w-0 mr-3">
                <h4 class="text-sm font-semibold text-gray-800 truncate" :title="doc.file_name">
                  {{ doc.file_name }}
                </h4>
                <div class="flex items-center space-x-3 mt-1">
                  <span class="text-xs text-gray-500">
                    {{ formatDate(doc.created_at) }}
                  </span>
                  <span
                    class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                    :class="getStatusStyle(doc.status)"
                  >
                    {{ getStatusText(doc.status) }}
                  </span>
                </div>
              </div>

              <!-- 操作按钮 -->
              <div class="flex items-center space-x-1">
                <!-- 删除按钮 -->
                <button
                  @click="$emit('delete', doc.id)"
                  class="p-1.5 hover:bg-red-50 rounded transition-colors group"
                  title="删除文档"
                >
                  <svg class="w-4 h-4 text-gray-400 group-hover:text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                </button>
              </div>
            </div>

            <!-- 处理进度（处理中或失败时显示） -->
            <div v-if="shouldShowProgress(doc.status)" class="mt-3">
              <DocumentProgress
                :status="doc.status"
                :progress="doc.progress || getProgress(doc.status)"
                :current-step="doc.current_step || getCurrentStep(doc.status)"
                :error-message="doc.error_message || ''"
                :show-percentage="true"
                :show-steps="false"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import DocumentProgress from './DocumentProgress.vue';
import { STATUS_PROGRESS_MAP } from '../api/knowledgeBase';

const props = defineProps({
  documents: {
    type: Array,
    default: () => []
  }
});

defineEmits(['delete']);

// 从 STATUS_PROGRESS_MAP 获取进度和步骤文本
const getProgress = (status) => {
  const info = STATUS_PROGRESS_MAP[status];
  return info ? info.progress : 0;
};

const getCurrentStep = (status) => {
  const info = STATUS_PROGRESS_MAP[status];
  return info ? info.step : '';
};

// 判断是否显示进度条
const shouldShowProgress = (status) => {
  return ['QUEUED', 'PARSING', 'CHUNKING', 'ENRICHING', 'VECTORIZING', 'FAILED'].includes(status);
};

// 获取文档类型图标
const getDocTypeIcon = (type) => {
  const iconMap = {
    'PDF': '/pdf.svg',
    'DOCX': '/doc、docx.svg',
    'DOC': '/docx.svg',
    'TXT': '/txt.svg',
    'MARKDOWN': '/file-markdown.svg',
    'MD': '/markdown.svg',
    'IMAGE': '/pdf.svg', // 图片暂时使用 PDF 图标
    'PNG': '/pdf.svg',
    'JPG': '/pdf.svg',
    'JPEG': '/pdf.svg',
    'PPTX': '/pptx.svg',
    'PPT': '/pptx.svg'
  };
  return iconMap[type] || '/pdf.svg';
};

// 获取状态样式
const getStatusStyle = (status) => {
  const styles = {
    'QUEUED': 'bg-gray-100 text-gray-700',
    'PARSING': 'bg-blue-100 text-blue-700',
    'CHUNKING': 'bg-blue-100 text-blue-700',
    'ENRICHING': 'bg-blue-100 text-blue-700',
    'VECTORIZING': 'bg-blue-100 text-blue-700',
    'COMPLETED': 'bg-green-100 text-green-700',
    'FAILED': 'bg-red-100 text-red-700'
  };
  return styles[status] || 'bg-gray-100 text-gray-700';
};

// 获取状态文本
const getStatusText = (status) => {
  const texts = {
    'QUEUED': '排队中',
    'PARSING': '解析中',
    'CHUNKING': '分段中',
    'ENRICHING': '内容增强',
    'VECTORIZING': '向量化',
    'COMPLETED': '已完成',
    'FAILED': '失败'
  };
  return texts[status] || status;
};

// 格式化日期
const formatDate = (dateString) => {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  const minutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(diff / (1000 * 60 * 60));
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  
  if (minutes < 1) return '刚刚';
  if (minutes < 60) return `${minutes}分钟前`;
  if (hours < 24) return `${hours}小时前`;
  if (days < 7) return `${days}天前`;
  
  return date.toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};
</script>

<style scoped>
/* 文本截断 */
.truncate {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

