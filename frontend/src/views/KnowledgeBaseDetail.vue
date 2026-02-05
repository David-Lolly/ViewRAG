<template>
  <div class="knowledge-base-detail-container h-screen bg-background-main flex flex-col">
    <!-- 顶部导航栏 -->
    <header class="bg-white border-b border-gray-200 px-6 py-4">
      <div class="flex items-center justify-between">
        <!-- 左侧：返回按钮和知识库信息 -->
        <div class="flex items-center space-x-4">
          <button
            @click="goBack"
            class="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="返回知识库列表"
          >
            <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
            </svg>
          </button>
          
          <div v-if="!loading && knowledgeBase">
            <h1 class="text-2xl font-bold text-gray-800">{{ knowledgeBase.name }}</h1>
            <p class="text-sm text-gray-500 mt-0.5">
              {{ knowledgeBase.description || '暂无描述' }}
            </p>
          </div>
          
          <div v-else class="animate-pulse">
            <div class="h-8 w-48 bg-gray-200 rounded mb-2"></div>
            <div class="h-4 w-64 bg-gray-200 rounded"></div>
          </div>
        </div>

        <!-- 右侧：上传按钮 -->
        <DocumentUpload
          v-if="knowledgeBase"
          :kb-id="kbId"
          @upload-complete="handleUploadComplete"
        />
      </div>

      <!-- 统计信息栏 -->
      <div v-if="!loading && knowledgeBase" class="mt-4 flex items-center space-x-6 text-sm">
        <div class="flex items-center space-x-2 text-gray-600">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
          </svg>
          <span class="font-medium">{{ documents.length }} 个文档</span>
        </div>
        
        <div class="flex items-center space-x-2 text-gray-600">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <span>创建于 {{ formatDate(knowledgeBase.created_at) }}</span>
        </div>

        <!-- 处理中的文档数量 -->
        <div v-if="processingCount > 0" class="flex items-center space-x-2 text-blue-600">
          <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
          <span class="font-medium">{{ processingCount }} 个文档处理中</span>
        </div>
      </div>
    </header>

    <!-- 主内容区域 -->
    <main class="flex-1 overflow-y-auto px-6 py-6">
      <!-- 加载状态 -->
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="flex flex-col items-center space-y-3">
          <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
          <p class="text-gray-500 text-sm">加载中...</p>
        </div>
      </div>

      <!-- 文档列表 -->
      <div v-else>
        <DocumentList
          :documents="documents"
          @delete="handleDeleteDocument"
        />
      </div>
    </main>

    <!-- 删除确认对话框 -->
    <div
      v-if="deleteConfirmDialog.show"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="deleteConfirmDialog.show = false"
    >
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md">
        <div class="px-6 py-6">
          <div class="flex items-start space-x-4">
            <div class="w-12 h-12 bg-red-100 rounded-full flex items-center justify-center flex-shrink-0">
              <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
            </div>
            <div class="flex-1">
              <p class="text-base text-gray-800 mb-2">
                确定要删除文档 <span class="font-semibold">{{ deleteConfirmDialog.docName }}</span> 吗？
              </p>
              <p class="text-sm text-red-600">
                此操作无法恢复
              </p>
            </div>
          </div>
        </div>

        <div class="px-6 py-4 bg-gray-50 rounded-b-2xl flex items-center justify-end space-x-3">
          <button
            @click="deleteConfirmDialog.show = false"
            class="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
            :disabled="deleting"
          >
            取消
          </button>
          <button
            @click="confirmDeleteDocument"
            class="px-5 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center space-x-2"
            :disabled="deleting"
          >
            <span v-if="deleting" class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
            <span>{{ deleting ? '删除中...' : '确认删除' }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { getKnowledgeBaseDetail, getDocuments, deleteDocument } from '../api/knowledgeBase';
import DocumentList from '../components/DocumentList.vue';
import DocumentUpload from '../components/DocumentUpload.vue';

const router = useRouter();
const route = useRoute();
const kbId = route.params.id;

// 状态
const loading = ref(false);
const knowledgeBase = ref(null);
const documents = ref([]);
const deleting = ref(false);
const deleteConfirmDialog = ref({
  show: false,
  docId: null,
  docName: ''
});

// 轮询定时器
let pollingTimer = null;

// 计算处理中的文档数量
const processingCount = computed(() => {
  return documents.value.filter(doc => 
    ['UPLOADING', 'PARSING', 'CHUNKING', 'PROCESSING', 'EMBEDDING'].includes(doc.status)
  ).length;
});

// 加载知识库详情
const loadKnowledgeBase = async () => {
  try {
    const response = await getKnowledgeBaseDetail(kbId);
    knowledgeBase.value = response.data;
  } catch (error) {
    console.error('加载知识库详情失败:', error);
    alert('加载知识库详情失败，请稍后重试');
    goBack();
  }
};

// 加载文档列表
const loadDocuments = async () => {
  try {
    const response = await getDocuments(kbId);
    documents.value = response.data.documents || [];
  } catch (error) {
    console.error('加载文档列表失败:', error);
  }
};

// 初始加载
const initLoad = async () => {
  loading.value = true;
  try {
    await Promise.all([
      loadKnowledgeBase(),
      loadDocuments()
    ]);
  } finally {
    loading.value = false;
  }
};

// 上传完成回调
const handleUploadComplete = async () => {
  await loadDocuments();
  startPolling(); // 开始轮询
};

// 处理删除文档
const handleDeleteDocument = (docId) => {
  const doc = documents.value.find(d => d.id === docId);
  if (!doc) return;

  deleteConfirmDialog.value = {
    show: true,
    docId: docId,
    docName: doc.file_name
  };
};

// 确认删除文档
const confirmDeleteDocument = async () => {
  deleting.value = true;
  try {
    await deleteDocument(kbId, deleteConfirmDialog.value.docId);
    deleteConfirmDialog.value.show = false;
    await loadDocuments();
  } catch (error) {
    console.error('删除文档失败:', error);
    alert('删除文档失败，请稍后重试');
  } finally {
    deleting.value = false;
  }
};

// 返回知识库列表
const goBack = () => {
  router.push('/knowledge-base');
};

// 格式化日期
const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit'
  });
};

// 开始轮询（当有文档处理中时）
const startPolling = () => {
  // 清除现有定时器
  if (pollingTimer) {
    clearInterval(pollingTimer);
  }

  // 如果有处理中的文档，启动轮询
  if (processingCount.value > 0) {
    pollingTimer = setInterval(async () => {
      await loadDocuments();
      
      // 如果没有处理中的文档了，停止轮询
      if (processingCount.value === 0) {
        stopPolling();
      }
    }, 3000); // 每3秒轮询一次
  }
};

// 停止轮询
const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
};

// 组件挂载
onMounted(async () => {
  await initLoad();
  startPolling(); // 初始检查是否需要轮询
});

// 组件卸载
onUnmounted(() => {
  stopPolling();
});
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

