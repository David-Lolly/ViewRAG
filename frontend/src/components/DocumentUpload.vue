<template>
  <div class="document-upload">
    <!-- 上传按钮触发器 -->
    <button
      @click="triggerFileInput"
      :disabled="uploading"
      class="flex items-center space-x-2 px-4 py-2.5 rounded-lg transition-colors shadow-sm font-medium disabled:bg-gray-400 disabled:cursor-not-allowed"
      :style="!uploading ? 'background-color: rgb(201, 100, 66); color: white;' : 'background-color: rgb(226, 176, 159); color: white;'"
      @mouseenter="!uploading && ($event.target.style.backgroundColor = 'rgb(198, 97, 63)')"
      @mouseleave="!uploading && ($event.target.style.backgroundColor = 'rgb(201, 100, 66)')"
    >
      <svg
        v-if="!uploading"
        class="w-5 h-5"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
      </svg>
      <div v-else class="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
      <span>{{ uploading ? '上传中...' : '上传文档' }}</span>
    </button>

    <!-- 隐藏的文件输入 -->
    <input
      ref="fileInput"
      type="file"
      multiple
      :accept="acceptedFileTypes"
      @change="handleFileSelect"
      class="hidden"
    />

    <!-- 上传进度对话框 -->
    <div
      v-if="showUploadDialog"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="closeUploadDialog"
    >
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg">
        <!-- 对话框头部 -->
        <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 class="text-xl font-semibold text-gray-800">上传文档</h2>
          <button
            v-if="!uploading"
            @click="closeUploadDialog"
            class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- 对话框内容 -->
        <div class="px-6 py-5 max-h-96 overflow-y-auto">
          <!-- 文件列表 -->
          <div class="space-y-3">
            <div
              v-for="(file, index) in selectedFiles"
              :key="index"
              class="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg"
            >
              <!-- 文件图标 -->
              <div class="flex-shrink-0">
                <img
                  :src="getFileIcon(file.name)"
                  :alt="getFileType(file.name)"
                  class="w-10 h-10"
                />
              </div>

              <!-- 文件信息 -->
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-800 truncate">{{ file.name }}</p>
                <p class="text-xs text-gray-500">{{ formatFileSize(file.size) }}</p>
              </div>

              <!-- 状态图标 -->
              <div class="flex-shrink-0">
                <!-- 上传成功 -->
                <svg
                  v-if="uploadStatus[index] === 'success'"
                  class="w-5 h-5 text-green-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                
                <!-- 上传中 -->
                <div
                  v-else-if="uploadStatus[index] === 'uploading'"
                  class="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"
                ></div>
                
                <!-- 等待上传 -->
                <svg
                  v-else-if="uploadStatus[index] === 'pending'"
                  class="w-5 h-5 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                
                <!-- 上传失败 -->
                <svg
                  v-else-if="uploadStatus[index] === 'error'"
                  class="w-5 h-5 text-red-500"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                </svg>
              </div>
            </div>
          </div>

          <!-- 总体进度 -->
          <div v-if="uploading" class="mt-5 p-4 bg-blue-50 rounded-lg">
            <div class="flex items-center justify-between mb-2">
              <span class="text-sm font-medium text-blue-900">上传进度</span>
              <span class="text-sm font-semibold text-blue-900">
                {{ uploadProgress.current }} / {{ uploadProgress.total }}
              </span>
            </div>
            <div class="h-2 bg-blue-200 rounded-full overflow-hidden">
              <div
                class="h-full bg-blue-600 transition-all duration-300"
                :style="{ width: `${(uploadProgress.current / uploadProgress.total) * 100}%` }"
              ></div>
            </div>
            <p class="text-xs text-blue-700 mt-2">
              正在上传: {{ uploadProgress.currentFile }}
            </p>
          </div>
        </div>

        <!-- 对话框底部 -->
        <div class="px-6 py-4 bg-gray-50 rounded-b-2xl flex items-center justify-end space-x-3">
          <button
            v-if="!uploading"
            @click="closeUploadDialog"
            class="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
          >
            取消
          </button>
          <button
            v-if="!uploading"
            @click="startUpload"
            :disabled="selectedFiles.length === 0"
            class="px-5 py-2 rounded-lg transition-colors font-medium disabled:bg-gray-300 disabled:cursor-not-allowed"
            :style="selectedFiles.length > 0 ? 'background-color: rgb(201, 100, 66); color: white;' : ''"
            @mouseenter="selectedFiles.length > 0 && ($event.target.style.backgroundColor = 'rgb(198, 97, 63)')"
            @mouseleave="selectedFiles.length > 0 && ($event.target.style.backgroundColor = 'rgb(201, 100, 66)')"
          >
            开始上传
          </button>
          <button
            v-else
            @click="closeUploadDialog"
            class="px-5 py-2 rounded-lg transition-colors font-medium"
            style="background-color: rgb(34, 197, 94); color: white;"
            @mouseenter="$event.target.style.backgroundColor = 'rgb(22, 163, 74)'"
            @mouseleave="$event.target.style.backgroundColor = 'rgb(34, 197, 94)'"
          >
            后台运行
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue';
import { uploadDocuments } from '../api/knowledgeBase';

const props = defineProps({
  kbId: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['upload-complete']);

// 支持的文件类型
const acceptedFileTypes = '.pdf,.docx,.doc,.txt,.md,.pptx,.ppt,.png,.jpg,.jpeg';

// 状态
const fileInput = ref(null);
const selectedFiles = ref([]);
const uploading = ref(false);
const showUploadDialog = ref(false);
const uploadStatus = reactive({});
const uploadProgress = reactive({
  current: 0,
  total: 0,
  currentFile: ''
});

// 触发文件选择
const triggerFileInput = () => {
  if (fileInput.value) {
    fileInput.value.click();
  }
};

// 处理文件选择
const handleFileSelect = (event) => {
  const files = Array.from(event.target.files);
  if (files.length === 0) return;

  selectedFiles.value = files;
  
  // 初始化上传状态
  files.forEach((_, index) => {
    uploadStatus[index] = 'pending';
  });

  showUploadDialog.value = true;
  
  // 清空 input，允许重复选择同一文件
  event.target.value = '';
};

// 开始上传
const startUpload = async () => {
  if (selectedFiles.value.length === 0) return;

  uploading.value = true;
  uploadProgress.current = 0;
  uploadProgress.total = selectedFiles.value.length;

  try {
    // 调用上传 API
    await uploadDocuments(
      props.kbId,
      selectedFiles.value,
      (progress) => {
        // 更新进度
        uploadProgress.current = progress.current;
        uploadProgress.currentFile = progress.currentFile;
        
        // 更新当前文件状态
        if (progress.current > 0) {
          uploadStatus[progress.current - 1] = 'success';
        }
        if (progress.current < uploadProgress.total) {
          uploadStatus[progress.current] = 'uploading';
        }
      }
    );

    // 所有文件上传完成
    selectedFiles.value.forEach((_, index) => {
      uploadStatus[index] = 'success';
    });

    // 通知父组件刷新列表
    emit('upload-complete');

    // 延迟关闭对话框
    setTimeout(() => {
      closeUploadDialog();
    }, 1000);

  } catch (error) {
    console.error('上传失败:', error);
    alert('上传失败，请稍后重试');
    
    // 标记失败的文件
    selectedFiles.value.forEach((_, index) => {
      if (uploadStatus[index] !== 'success') {
        uploadStatus[index] = 'error';
      }
    });
  } finally {
    uploading.value = false;
  }
};

// 关闭上传对话框
const closeUploadDialog = () => {
  if (uploading.value) {
    // 如果正在上传，询问确认
    if (!confirm('文档正在上传中，确定要关闭吗？上传将在后台继续。')) {
      return;
    }
  }
  
  showUploadDialog.value = false;
  selectedFiles.value = [];
  Object.keys(uploadStatus).forEach(key => delete uploadStatus[key]);
  uploadProgress.current = 0;
  uploadProgress.total = 0;
  uploadProgress.currentFile = '';
};

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
};

// 获取文件类型
const getFileType = (fileName) => {
  const ext = fileName.split('.').pop().toUpperCase();
  return ext;
};

// 获取文件图标
const getFileIcon = (fileName) => {
  const ext = fileName.split('.').pop().toUpperCase();
  const iconMap = {
    'PDF': '/pdf.svg',
    'DOCX': '/docx.svg',
    'DOC': '/docx.svg',
    'TXT': '/txt.svg',
    'MD': '/markdown.svg',
    'MARKDOWN': '/markdown.svg',
    'PPTX': '/pptx.svg',
    'PPT': '/pptx.svg',
    'PNG': '/pdf.svg',
    'JPG': '/pdf.svg',
    'JPEG': '/pdf.svg'
  };
  return iconMap[ext] || '/pdf.svg';
};
</script>

<style scoped>
/* 滚动条样式 */
.overflow-y-auto {
  scrollbar-width: thin;
  scrollbar-color: #d4d4d4 #f5f5f5;
}

.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background-color: #d4d4d4;
  border-radius: 10px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background-color: #a3a3a3;
}
</style>

