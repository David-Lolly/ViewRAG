<template>
  <div class="knowledge-base-list-container h-screen bg-background-main flex flex-col">
    <!-- 顶部导航栏 -->
    <header class="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <button
          @click="goBack"
          class="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="返回"
        >
          <svg class="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
          </svg>
        </button>
        <div>
          <h1 class="text-2xl font-bold text-gray-800">个人知识库</h1>
          <p class="text-sm text-gray-500 mt-0.5">管理和组织您的文档资料</p>
        </div>
      </div>
      
      <button
        @click="showCreateDialog = true"
        class="flex items-center space-x-2 px-4 py-2.5 rounded-lg transition-colors shadow-sm font-medium"
        style="background-color: rgb(201, 100, 66); color: white;"
        :style="{ 
          '&:hover': { backgroundColor: 'rgb(198, 97, 63)' }
        }"
        @mouseenter="$event.target.style.backgroundColor = 'rgb(198, 97, 63)'"
        @mouseleave="$event.target.style.backgroundColor = 'rgb(201, 100, 66)'"
      >
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
        </svg>
        <span>新建知识库</span>
      </button>
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

      <!-- 空状态 -->
      <div v-else-if="knowledgeBases.length === 0" class="flex flex-col items-center justify-center py-20">
        <div class="w-24 h-24 bg-gray-100 rounded-full flex items-center justify-center mb-6">
          <svg class="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
          </svg>
        </div>
        <h3 class="text-xl font-semibold text-gray-700 mb-2">还没有知识库</h3>
        <p class="text-gray-500 mb-6">创建您的第一个知识库，开始管理文档</p>
        <button
          @click="showCreateDialog = true"
          class="px-6 py-2.5 rounded-lg transition-colors font-medium"
          style="background-color: rgb(201, 100, 66); color: white;"
          @mouseenter="$event.target.style.backgroundColor = 'rgb(198, 97, 63)'"
          @mouseleave="$event.target.style.backgroundColor = 'rgb(201, 100, 66)'"
        >
          创建知识库
        </button>
      </div>

      <!-- 知识库列表 -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        <div
          v-for="kb in knowledgeBases"
          :key="kb.id"
          @click="enterKnowledgeBase(kb.id)"
          class="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg hover:border-blue-300 transition-all duration-200 cursor-pointer group"
        >
          <!-- 知识库图标和操作按钮 -->
          <div class="flex items-start justify-between mb-4">
            <div class="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg flex items-center justify-center shadow-sm">
              <svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
              </svg>
            </div>
            
            <!-- 删除按钮 -->
            <button
              @click.stop="confirmDelete(kb)"
              class="opacity-0 group-hover:opacity-100 p-2 hover:bg-red-50 rounded-lg transition-all"
              title="删除知识库"
            >
              <svg class="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
              </svg>
            </button>
          </div>

          <!-- 知识库名称 -->
          <h3 class="text-lg font-semibold text-gray-800 mb-2 line-clamp-1 group-hover:text-blue-600 transition-colors">
            {{ kb.name }}
          </h3>

          <!-- 知识库描述 -->
          <p class="text-sm text-gray-500 mb-4 line-clamp-2 min-h-[2.5rem]">
            {{ kb.description || '暂无描述' }}
          </p>

          <!-- 底部信息 -->
          <div class="flex items-center justify-between pt-4 border-t border-gray-100">
            <div class="flex items-center space-x-1 text-sm text-gray-600">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
              </svg>
              <span>{{ kb.document_count }} 个文档</span>
            </div>
            
            <div class="text-xs text-gray-400">
              {{ formatDate(kb.created_at) }}
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- 创建知识库对话框 -->
    <div
      v-if="showCreateDialog"
      class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      @click.self="closeCreateDialog"
    >
      <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md transform transition-all">
        <!-- 对话框头部 -->
        <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 class="text-xl font-semibold text-gray-800">新建知识库</h2>
          <button
            @click="closeCreateDialog"
            class="p-1 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <svg class="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <!-- 对话框内容 -->
        <div class="px-6 py-5 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              知识库名称 <span class="text-red-500">*</span>
            </label>
            <input
              v-model="newKbName"
              type="text"
              placeholder="例如：AI技术文档"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
              maxlength="50"
              @keyup.enter="createKnowledgeBase"
            />
            <p class="text-xs text-gray-500 mt-1">{{ newKbName.length }}/50</p>
          </div>

          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              描述
            </label>
            <textarea
              v-model="newKbDescription"
              placeholder="简要描述这个知识库的用途..."
              rows="3"
              class="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none resize-none transition-all"
              maxlength="200"
            ></textarea>
            <p class="text-xs text-gray-500 mt-1">{{ newKbDescription.length }}/200</p>
          </div>
        </div>

        <!-- 对话框底部 -->
        <div class="px-6 py-4 bg-gray-50 rounded-b-2xl flex items-center justify-end space-x-3">
          <button
            @click="closeCreateDialog"
            class="px-4 py-2 text-gray-700 hover:bg-gray-200 rounded-lg transition-colors"
            :disabled="creating"
          >
            取消
          </button>
          <button
            @click="createKnowledgeBase"
            :disabled="!newKbName.trim() || creating"
            class="px-5 py-2 rounded-lg transition-colors font-medium disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center space-x-2"
            :style="newKbName.trim() && !creating ? 'background-color: rgb(201, 100, 66); color: white;' : ''"
            @mouseenter="newKbName.trim() && !creating && ($event.target.style.backgroundColor = 'rgb(198, 97, 63)')"
            @mouseleave="newKbName.trim() && !creating && ($event.target.style.backgroundColor = 'rgb(201, 100, 66)')"
          >
            <span v-if="creating" class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></span>
            <span>{{ creating ? '创建中...' : '创建' }}</span>
          </button>
        </div>
      </div>
    </div>

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
                确定要删除知识库 <span class="font-semibold">{{ deleteConfirmDialog.kb?.name }}</span> 吗？
              </p>
              <p class="text-sm text-red-600">
                此操作将删除该知识库及其所有文档，且无法恢复
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
            @click="confirmDeleteKnowledgeBase"
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
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { getKnowledgeBases, createKnowledgeBase as createKb, deleteKnowledgeBase as deleteKb } from '../api/knowledgeBase';

const router = useRouter();
const userId = sessionStorage.getItem('userId');

// 状态
const loading = ref(false);
const knowledgeBases = ref([]);
const showCreateDialog = ref(false);
const newKbName = ref('');
const newKbDescription = ref('');
const creating = ref(false);
const deleting = ref(false);

const deleteConfirmDialog = ref({
  show: false,
  kb: null
});

// 加载知识库列表
const loadKnowledgeBases = async () => {
  loading.value = true;
  try {
    const response = await getKnowledgeBases(userId);
    knowledgeBases.value = response.data.knowledge_bases || [];
  } catch (error) {
    console.error('加载知识库列表失败:', error);
    alert('加载知识库列表失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};

// 创建知识库
const createKnowledgeBase = async () => {
  if (!newKbName.value.trim()) {
    alert('请输入知识库名称');
    return;
  }

  creating.value = true;
  try {
    await createKb(userId, newKbName.value.trim(), newKbDescription.value.trim());
    closeCreateDialog();
    await loadKnowledgeBases();
  } catch (error) {
    console.error('创建知识库失败:', error);
    alert('创建知识库失败，请稍后重试');
  } finally {
    creating.value = false;
  }
};

// 关闭创建对话框
const closeCreateDialog = () => {
  showCreateDialog.value = false;
  newKbName.value = '';
  newKbDescription.value = '';
};

// 确认删除
const confirmDelete = (kb) => {
  deleteConfirmDialog.value = {
    show: true,
    kb: kb
  };
};

// 确认删除知识库
const confirmDeleteKnowledgeBase = async () => {
  deleting.value = true;
  try {
    await deleteKb(deleteConfirmDialog.value.kb.id);
    deleteConfirmDialog.value.show = false;
    await loadKnowledgeBases();
  } catch (error) {
    console.error('删除知识库失败:', error);
    alert('删除知识库失败，请稍后重试');
  } finally {
    deleting.value = false;
  }
};

// 进入知识库详情
const enterKnowledgeBase = (kbId) => {
  router.push(`/knowledge-base/${kbId}`);
};

// 返回
const goBack = () => {
  router.push('/');
};

// 格式化日期
const formatDate = (dateString) => {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now - date;
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  
  if (days === 0) return '今天';
  if (days === 1) return '昨天';
  if (days < 7) return `${days}天前`;
  if (days < 30) return `${Math.floor(days / 7)}周前`;
  if (days < 365) return `${Math.floor(days / 30)}个月前`;
  
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' });
};

// 组件挂载时加载数据
onMounted(() => {
  loadKnowledgeBases();
});
</script>

<style scoped>
/* 文本截断 */
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

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

