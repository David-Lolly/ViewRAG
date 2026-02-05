<template>
  <div class="flex w-full h-full bg-background-main relative"
       @drop.prevent="handleDrop"
       @dragover.prevent="handleDragOver"
       @dragleave.prevent="handleDragLeave"
       @dragenter.prevent="handleDragEnter">
    
    <!-- 全局拖拽提示层 -->
    <div 
      v-if="isDragging" 
      class="fixed inset-0 bg-background-secondary bg-opacity-95 backdrop-blur-sm z-[10000] flex items-center justify-center pointer-events-none"
    >
      <div class="bg-white rounded-3xl shadow-2xl px-12 py-10 border-4 border-dashed border-button-active max-w-md">
        <div class="text-center">
          <div class="mb-6">
            <svg class="w-20 h-20 mx-auto text-button-active" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path>
            </svg>
          </div>
          <h3 class="text-2xl font-bold text-text-primary mb-3">释放以上传文件</h3>
          <p class="text-base text-text-secondary mb-2">
            支持文档：PDF、Word、Excel、PPT、TXT
          </p>
          <p class="text-base text-text-secondary">
            支持图片：PNG、JPG、GIF、WebP
          </p>
          <p class="text-sm text-gray-500 mt-4">
            图片上传需要选择多模态模型
          </p>
        </div>
      </div>
    </div>
    
    <ChatSidebar
      :sessions="sessions"
      :current-session-id="currentSessionId"
      :user-id="userId"
      :is-open="isSidebarOpen"
      @toggle="toggleSidebar"
      @new-chat="createNewSession"
      @session-select="selectSession"
      @logout="handleLogout" 
      @edit-config="navigateToConfig"
      @go-to-kb="navigateToKnowledgeBase" />

    <main class="relative flex-1 flex flex-col transition-all duration-300 ease-in-out"
          :style="{
            marginLeft: isSidebarOpen ? '288px' : '0px'
          }">

      <div class="flex-1 overflow-y-auto px-6 pt-4" ref="messagesContainer">
        <div v-if="!currentSessionId" class="flex items-center justify-center h-full">
          <div class="text-center max-w-md animate-fade-in">
            <img src="@/assets/TinyAISearchLOGO.jpg" alt="TinyAISearch Logo" class="w-20 h-20 rounded-2xl mx-auto mb-6 shadow-floating">
            <h1 class="text-4xl font-bold mb-3 text-text-primary">TinyAISearch</h1>
            <p class="text-text-secondary text-lg leading-relaxed">
              智能搜索助手，随时为您答疑解惑<br>
              <span class="text-sm opacity-75">输入内容，开始你的第一次对话吧！</span>
            </p>
          </div>
        </div>

        <div v-else class="max-w-4xl mx-auto" :style="{ paddingBottom: dynamicPaddingBottom }">
          <ChatMessage
            v-for="(msg, index) in messages"
            :key="msg.message_id"
            :message="msg"
            :user-id="userId"
            :is-streaming="index === messages.length - 1 && isLoading && msg.role === 'assistant' && !msg.streamEnded"
            :search-steps="index === messages.length - 1 ? currentSearchSteps : []"
            :is-marked-for-deletion="editingMessageIndex !== null && index > editingMessageIndex"
            :has-error="msg.hasError"
            :error-message="msg.errorMessage"
            @regenerate="handleRegenerate"
            @edit="handleEdit"
            @retry="handleRetry"
            class="mb-2 animate-slide-in"
            />
        </div>
      </div>

      
      <div ref="inputAreaRef" class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-background-main via-background-main to-transparent pt-3 pb-3 px-6">
        <div class="max-w-4xl mx-auto">
          <div class="bg-background-card rounded-xl shadow-input-card border border-gray-100 overflow-hidden">

            <!-- 图片预览区域（移到顶部） -->
            <div v-if="pendingImages.length > 0" class="px-4 pt-3 pb-3 border-b border-gray-100 flex flex-wrap gap-2">
              <div v-for="img in pendingImages" :key="img.id" class="relative inline-block">
                <img :src="img.previewUrl" :alt="img.file.name" 
                     class="w-24 h-24 object-cover rounded-lg border border-gray-200 shadow-sm" 
                     :class="{ 'opacity-50': img.uploading }" />
                
                <!-- 上传中遮罩层 -->
                <div v-if="img.uploading" class="absolute inset-0 flex items-center justify-center bg-black bg-opacity-40 rounded-lg">
                  <svg class="animate-spin h-6 w-6 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </div>
                
                <!-- 上传成功标识 -->
                <div v-if="!img.uploading && img.url" class="absolute top-1 left-1 bg-green-500 text-white px-1 py-0.5 rounded text-xs font-medium flex items-center shadow-md">
                  <svg class="w-2 h-2 mr-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>
                  </svg>
                  ✓
                </div>
                
                <!-- 删除按钮 -->
                <button
                  type="button"
                  @click="removeImage(img.id)"
                  :disabled="img.uploading"
                  class="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full hover:bg-red-600 flex items-center justify-center shadow-md transition-all duration-200 hover:scale-110 text-xs"
                  :class="{ 'opacity-50 cursor-not-allowed': img.uploading }"
                  title="删除图片"
                >
                  ×
                </button>
                
                <!-- 文件名提示 -->
                <div class="absolute bottom-0 left-0 right-0 bg-black bg-opacity-60 text-white text-xs px-1 py-0.5 rounded-b-lg truncate">
                  {{ img.file.name }}
                </div>
              </div>
              
              <!-- 添加更多图片按钮 -->
              <button
                v-if="pendingImages.length < 10"
                type="button"
                @click="triggerImageUpload"
                class="w-24 h-24 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center hover:border-blue-500 hover:bg-blue-50 transition-all duration-200"
                title="添加更多图片（最多10张）"
              >
                <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
                </svg>
              </button>
            </div>

            <form @submit.prevent class="relative flex flex-col">
              <div 
                class="flex-1 relative px-4 pt-3 pb-2"
              >
                <textarea
                  v-model="userInput"
                  @input="autoGrowTextarea"
                  @keydown.enter.exact.prevent="handleEnter"
                  @paste="handlePaste"
                  ref="textareaRef"
                  :disabled="isLoading"
                  class="w-full resize-none border-none outline-none bg-transparent text-text-primary placeholder-text-secondary leading-relaxed textarea-scrollable"
                  :style="{ maxHeight: '144px', minHeight: '24px', fontSize: '1rem' }"
                  rows="1"
                  placeholder="输入你的问题..."
                ></textarea>

                <div class="h-0.5 bg-gradient-to-r from-transparent via-gray-200 to-transparent opacity-30 mt-1.5"></div>
              </div>

              <!-- 底部操作栏 -->
              <div class="flex items-center justify-between px-4 py-2.5 gap-3">
                <!-- 左侧：加号按钮和下拉菜单 -->
                <div class="button-group">
                  <div class="relative group">
                    <button
                      ref="uploadMenuButton"
                      type="button"
                      @click="toggleUploadMenu"
                      class="chat-button flex items-center justify-center w-10 h-10 rounded-lg border border-gray-200 bg-white hover:bg-gray-50 hover:border-gray-300 text-gray-600 hover:text-gray-900 transition-all duration-300 focus:outline-none shadow-sm hover:shadow-inner active:shadow-inner"
                    >
                      <svg 
                        class="w-5 h-5 transition-transform duration-300 ease-in-out" 
                        :class="{ 'rotate-45': showMenuDropdown }"
                        fill="none" 
                        stroke="currentColor" 
                        viewBox="0 0 24 24" 
                        stroke-width="2.5"
                      >
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 4v16m8-8H4"></path>
                      </svg>
                    </button>
                  </div>
                  
                  <!-- 联网搜索按钮 -->
                  <div class="relative group">
                    <button
                      type="button"
                      @click="useWeb = !useWeb"
                      class="chat-button flex items-center justify-center gap-2 px-3 h-10 rounded-lg border transition-all duration-300 focus:outline-none shadow-sm hover:shadow-inner active:shadow-inner"
                      :class="{
                        'border-button-active bg-button-active  text-white': useWeb,
                        'border-button-disabled bg-button-disabled  text-white/100': !useWeb
                      }"
                    >
                      <GlobeAltIcon class="w-4 h-4" />
                      <span class="text-sm font-medium">联网搜索</span>
                    </button>
                    
                    <!-- 气泡提示 -->
                    <div class="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-60">
                      <div class="tooltip whitespace-nowrap relative">
                        {{ useWeb ? '关闭联网搜索' : '启用联网搜索' }}
                        <!-- 小三角箭头 -->
                        <div class="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-black"></div>
                      </div>
                    </div>
                  </div>
                </div>
                
                <!-- 右侧：模型选择器和发送按钮 -->
                <div class="button-group">
                  <!-- 模型选择器 -->
                  <div class="flex-shrink-0">
                    <ModelSelector
                      :models="availableModels"
                      :selectedModel="selectedModel"
                      @model-selected="handleModelSelect"
                    />
                  </div>
                  
                  <!-- 发送按钮 -->
                  <button
                    type="button"
                    @click="isLoading ? handleStop() : sendMessage()"
                    :disabled="!isLoading && (!userInput.trim() || hasUploadingImages)"
                    class="chat-button w-10 h-10 rounded-lg font-semibold transition-all duration-300 relative flex items-center justify-center flex-shrink-0 border focus:outline-none shadow-sm hover:shadow-inner active:shadow-inner"
                    :class="[
                      isLoading
                        ? 'bg-blue-600 hover:bg-blue-700 border-blue-600 hover:border-blue-700 text-white'
                        : ((!userInput.trim() || hasUploadingImages) ? 'bg-button-disabled border-button-disabled text-white/100 cursor-not-allowed shadow-none hover:shadow-none' : 'bg-button-active hover:bg-[rgb(178,87,53)] border-button-active hover:border-[rgb(178,87,53)] text-white')
                    ]"
                    :title="hasUploadingImages ? '图片上传中，请稍候...' : ''"
                  >
                    <!-- 上传中提示 -->
                    <svg v-if="hasUploadingImages" class="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    
                    <svg v-else-if="isLoading" class="w-4 h-4" viewBox="0 0 12 12" fill="currentColor">
                        <rect width="12" height="12" rx="1.5" />
                    </svg>
                    
                    <ArrowUpIcon v-else class="w-5 h-5" />
                  </button>
                </div>
              </div>
            </form>

            <input 
              ref="imageInput"
              type="file" 
              accept="image/*" 
              multiple
              @change="handleImageUpload" 
              class="hidden"
            />
            
            <input 
              ref="fileInput"
              type="file" 
              accept=".pdf,.doc,.docx,.txt,.xlsx,.pptx"
              @change="handleFileUpload" 
              class="hidden"
            />
          </div>

          <div class="text-center mt-3">
            <p class="text-xs text-text-secondary">
              {{ useWeb ? 'TinyAISearch 正在联网搜索最新信息' : 'TinyAISearch 正在使用AI知识直接回答' }}，可能会出错，请核实重要信息。
              <button class="text-blue-600 hover:text-blue-700 underline transition-colors duration-200">
                了解更多
              </button>
            </p>
          </div>
        </div>
      </div>
    </main>
    
    <!-- 上传菜单（固定定位，避免被overflow-hidden裁剪） -->
    <div 
      v-if="showMenuDropdown"
      ref="uploadMenu"
      class="fixed bg-white rounded-2xl shadow-xl border border-gray-200 py-2 z-[9999] w-auto"
      :style="uploadMenuStyle"
      @click.stop
    >
      <!-- 上传文档 -->
      <button
        type="button"
        @click="triggerFileUpload"
        class="w-full px-4 py-2 text-left flex items-center gap-3 hover:bg-gray-50 transition-colors duration-150 text-sm text-text-primary whitespace-nowrap"
      >
        <DocumentPlusIcon class="w-5 h-5 text-gray-700 flex-shrink-0" />
        <span class="font-normal">上传文档</span>
      </button>
      
      <!-- 上传图片 -->
      <button
        type="button"
        @click="triggerImageUploadFromMenu"
        :disabled="!isMultiModalModel"
        class="w-full px-4 py-2 text-left flex items-center gap-3 hover:bg-gray-50 transition-colors duration-150 text-sm whitespace-nowrap"
        :class="{
          'text-text-primary cursor-pointer': isMultiModalModel,
          'text-gray-300 cursor-not-allowed': !isMultiModalModel
        }"
      >
        <PhotoIcon class="w-5 h-5 flex-shrink-0" :class="{'text-gray-700': isMultiModalModel, 'text-gray-300': !isMultiModalModel}" />
        <span class="font-normal">上传图片</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch, computed } from 'vue';
import api from '@/services/api';
import ChatSidebar from '@/components/ChatSidebar.vue';
import ChatMessage from '@/components/ChatMessage.vue';
import ModelSelector from '@/components/ModelSelector.vue';
import IconSpinner from '@/components/IconSpinner.vue';
import {
  GlobeAltIcon,
  ArrowUpIcon,
  Bars3Icon,
  DocumentPlusIcon,
  PhotoIcon
} from '@heroicons/vue/24/outline';
import { useRouter } from 'vue-router';
import imageCompression from 'browser-image-compression';


const userId = sessionStorage.getItem('userId') || '';

defineEmits(['logout']);

const sessions = ref([]);
const currentSessionId = ref(null);
const messages = ref([]);
const userInput = ref('');
const useWeb = ref(false);
const isLoading = ref(false);
const isSidebarOpen = ref(true);

// 模型选择相关
const availableModels = ref([]);
const selectedModel = ref(null);
const currentSearchSteps = ref([]);
const messagesContainer = ref(null);
const textareaRef = ref(null);
const imageInput = ref(null);
const fileInput = ref(null);
const pendingImages = ref([]); // O.G. uploadedImages. Stores { id, file, blob, previewUrl }
const isDragging = ref(false);
const showMenuDropdown = ref(false);
const uploadMenuButton = ref(null);
const uploadMenu = ref(null);
const uploadMenuStyle = ref({});
const inputAreaRef = ref(null); // 输入框区域容器
const dynamicPaddingBottom = ref('288px'); // 动态底部内边距，默认288px
// const isUploadingImage = ref(false); // No longer needed
// const minioImageUrls = ref([]); // No longer needed, URLs are handled server-side

// 判断当前选择的模型是否为多模态模型
const isMultiModalModel = computed(() => {
  return selectedModel.value?.type === 'multi-model';
});

const router = useRouter();


const abortController = ref(null);
const editingMessageIndex = ref(null);
const retryPayload = ref(null);
// 发送并发与去重保护
const sendLock = ref(false);
const lastSendSignature = ref('');
const lastSendTime = ref(0);

const initAssistantStreamState = (message) => {
  if (!message) return;
  message.rawChunks = [];
  message._streamLogged = false;
};

const appendAssistantStreamChunk = (message, chunk) => {
  if (!message || typeof chunk !== 'string') return;
  if (!Array.isArray(message.rawChunks)) {
    message.rawChunks = [];
  }
  message.rawChunks.push(chunk);
};

const finalizeAssistantStreamLog = (message, context = '') => {
  if (!message || message._streamLogged) return;
  const label = context ? ` ${context}` : '';
  if (Array.isArray(message.rawChunks) && message.rawChunks.length > 0) {
    const fullResponse = message.rawChunks.join('');
    console.log(`[Stream][complete${label}] full response:`, fullResponse);
  } else {
    console.log(`[Stream][complete${label}] no chunks captured; final content:`, message.content);
  }
  message.rawChunks = [];
  message._streamLogged = true;
};

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value;
};

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
    }
  });
};

const autoGrowTextarea = () => {
  nextTick(() => {
    const textarea = textareaRef.value;
    if (textarea) {
      textarea.style.height = 'auto';
      const maxHeight = 144; // 最大高度为144px（约6行）
      if (textarea.scrollHeight <= maxHeight) {
        textarea.style.height = `${textarea.scrollHeight}px`;
      } else {
        textarea.style.height = `${maxHeight}px`;
      }
    }
  });
};

/**
 * 专为AI视觉模型优化的图片压缩函数
 * @param {File} file 原始图片文件
 * @returns {Promise<File>} 压缩后的图片文件 (Blob)
 */
async function compressImageForAI(file) {
  const options = {
    maxSizeMB: 0.5,           // 目标体积: 小于 500KB
    maxWidthOrHeight: 1280,   // 目标尺寸: 小于 1280px
    useWebWorker: true,         // 使用后台线程，不阻塞UI
    fileType: 'image/webp',     // 优先转换为高效的WebP格式
    initialQuality: 0.7,        // 初始压缩质量
  };

  try {
    const compressedFile = await imageCompression(file, options);
    console.log(`图片压缩成功: ${file.name} -> ${compressedFile.name}, 大小: ${Math.round(compressedFile.size / 1024)}KB`);
    return compressedFile;
  } catch (error) {
    console.error(`图片压缩失败: ${file.name}, 将使用原图.`, error);
    showToast(`图片 ${file.name} 压缩失败，将尝试使用原图`, 'error');
    return file; // 压缩失败则返回原图
  }
}

// 图片上传相关
const triggerImageUpload = () => {
  if (isMultiModalModel.value && imageInput.value) {
    imageInput.value.click();
  }
};

const handleImageUpload = (event) => {
  const files = Array.from(event.target.files);
  if (files.length > 0) {
    processImageFiles(files);
  }
};

// 处理粘贴事件
const handlePaste = async (event) => {
  const items = event.clipboardData?.items;
  if (!items) return;
  
  const imageFiles = [];
  
  // 遍历剪贴板项目，查找图片
  for (let i = 0; i < items.length; i++) {
    const item = items[i];
    
    // 检查是否为图片类型
    if (item.type.startsWith('image/')) {
      event.preventDefault(); // 阻止默认粘贴行为（避免粘贴图片的文件路径）
      
      const file = item.getAsFile();
      if (file) {
        imageFiles.push(file);
      }
    }
  }
  
  // 如果有图片，处理它们
  if (imageFiles.length > 0) {
    // 检查是否为多模态模型
    if (!isMultiModalModel.value) {
      showToast('图片粘贴需要选择多模态模型，请在右下角切换模型', 'error');
      return;
    }
    
    await processImageFiles(imageFiles);
    showToast(`成功粘贴 ${imageFiles.length} 张图片`, 'success');
  }
};

const processImageFiles = async (files) => {
  const imageFiles = files.filter(f => f.type.startsWith('image/'));
  
  if (imageFiles.length === 0) {
    return;
  }
  
  if (pendingImages.value.length + imageFiles.length > 10) {
    alert(`最多只能上传10张图片，当前已有${pendingImages.value.length}张`);
    return;
  }
  
  for (const file of imageFiles) {
    const id = Date.now() + Math.random();

    // 压缩图片
    const compressedBlob = await compressImageForAI(file);
    
    // 生成本地预览URL
    const previewUrl = URL.createObjectURL(compressedBlob);

    pendingImages.value.push({
      id,
      file, // a.k.a original file
      blob: compressedBlob,
      previewUrl,
    });
  }
  
  // 清空文件输入，以便可以再次选择相同的文件
  if (imageInput.value) {
    imageInput.value.value = '';
  }
};

// 上传单张图片 (This function is now obsolete and will be removed)
/*
const uploadSingleImage = async (imageId, imageBase64, filename) => {
...
};
*/

// 新增：显示Toast提示
const showToast = (message, type = 'info') => {
  // 创建toast元素
  const toast = document.createElement('div');
  toast.className = `fixed top-4 right-4 px-6 py-3 rounded-lg shadow-lg z-50 transition-all duration-300 ${
    type === 'success' ? 'bg-green-500 text-white' : 
    type === 'error' ? 'bg-red-500 text-white' : 
    'bg-blue-500 text-white'
  }`;
  toast.textContent = message;
  toast.style.opacity = '0';
  toast.style.transform = 'translateY(-20px)';
  
  document.body.appendChild(toast);
  
  // 动画显示
  setTimeout(() => {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  }, 10);
  
  // 3秒后淡出并移除
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(-20px)';
    setTimeout(() => {
      document.body.removeChild(toast);
    }, 300);
  }, 3000);
};

const removeImage = (imageId) => {
  if (imageId) {
    const index = pendingImages.value.findIndex(img => img.id === imageId);
    if (index !== -1) {
      const removedImg = pendingImages.value.splice(index, 1)[0];
      // 释放之前创建的Object URL
      URL.revokeObjectURL(removedImg.previewUrl);
    }
  } else {
    // 清空所有图片并释放所有Object URL
    pendingImages.value.forEach(img => URL.revokeObjectURL(img.previewUrl));
    pendingImages.value = [];
  }
  
  if (imageInput.value) {
    imageInput.value.value = '';
  }
};

// 计算上传状态
const hasUploadingImages = computed(() => {
  // This logic is no longer relevant as uploading happens on send
  return false; 
});

// 拖拽上传相关
let dragCounter = 0; // 用于跟踪拖拽进入/离开事件

const handleDragEnter = (e) => {
  dragCounter++;
  isDragging.value = true;
};

const handleDragOver = (e) => {
  isDragging.value = true;
};

const handleDragLeave = (e) => {
  dragCounter--;
  // 只有当完全离开应用窗口时才隐藏提示
  if (dragCounter === 0) {
    isDragging.value = false;
  }
};

const handleDrop = async (e) => {
  dragCounter = 0;
  isDragging.value = false;
  
  const files = Array.from(e.dataTransfer.files);
  if (files.length === 0) return;
  
  // 分类文件
  const imageFiles = files.filter(f => f.type.startsWith('image/'));
  const documentFiles = files.filter(f => {
    const ext = f.name.split('.').pop().toLowerCase();
    return ['pdf', 'doc', 'docx', 'txt', 'xlsx', 'pptx'].includes(ext);
  });
  
  // 处理图片文件
  if (imageFiles.length > 0) {
    if (!isMultiModalModel.value) {
      showToast('图片上传需要选择多模态模型，请在右下角切换模型', 'error');
      return;
    }
    await processImageFiles(imageFiles);
  }
  
  // 处理文档文件
  if (documentFiles.length > 0) {
    // 模拟文件输入的 change 事件
    const dataTransfer = new DataTransfer();
    documentFiles.forEach(file => dataTransfer.items.add(file));
    
    if (fileInput.value) {
      fileInput.value.files = dataTransfer.files;
      await handleFileUpload({ target: fileInput.value });
    }
  }
  
  // 如果没有支持的文件
  if (imageFiles.length === 0 && documentFiles.length === 0) {
    showToast('不支持的文件格式，请上传文档（PDF、Word、Excel、PPT、TXT）或图片（PNG、JPG、GIF、WebP）', 'error');
  }
};

const fetchMessages = async (sessionId) => {
  try {
    const response = await api.getMessages(sessionId);
    messages.value = response.data.map((m, index) => {
      // 为从数据库加载的消息生成稳定的前端ID
      const frontendId = `loaded-${sessionId}-${index}-${m.message_id}`;
      
      // 用户消息：保留所有字段
      if (m.role === 'user') {
        return {
          message_id: frontendId,      // 前端稳定ID
          db_message_id: m.message_id, // 数据库真实ID
          role: 'user',
          content: m.content,
          image_url: m.image_url,
          timestamp: m.timestamp,
          streamEnded: true  // 历史消息标记为已完成
        };
      }
      
      console.log(`[Debug] 2. 正在处理AI消息 (index: ${index}):`, JSON.parse(JSON.stringify(m)));

      try {
        let parsedContent;
        if (typeof m.content === 'string') {
          try {
            parsedContent = JSON.parse(m.content);
            console.log(`[Debug] 3. 成功将消息内容解析为JSON对象:`, JSON.parse(JSON.stringify(parsedContent)));
          } catch (e) {
            console.log(`[Debug] 3. 消息内容不是一个有效的JSON字符串，将作为纯文本处理。内容:`, m.content);
            parsedContent = m.content;
          }
        } else {
          parsedContent = m.content;
          console.log(`[Debug] 3. 消息内容已经是对象类型:`, JSON.parse(JSON.stringify(parsedContent)));
        }

        let finalContent = '';
        let finalReferences = [];

        if (typeof parsedContent === 'object' && parsedContent !== null) {
          if (parsedContent.text) {
            finalContent = parsedContent.text;
            console.log(`[Debug] 4. 从解析后的对象中提取 'text' 属性作为最终内容。`);
          } else {
            console.warn(`[Debug] 4. 警告：解析后的对象没有 'text' 属性，内容将为空。对象:`, JSON.parse(JSON.stringify(parsedContent)));
          }
          finalReferences = parsedContent.references || [];
        } else if (typeof parsedContent === 'string') {
          finalContent = parsedContent;
          console.log(`[Debug] 4. 内容是纯字符串，直接作为最终内容。`);
        }

        const finalMessageObject = { 
          message_id: frontendId,
          db_message_id: m.message_id,
          role: 'assistant', 
          content: finalContent, 
          references: finalReferences,
          streamEnded: true  // 历史消息标记为已完成流式传输
        };
        console.log(`[Debug] 5. 最终生成并推入渲染数组的消息对象:`, JSON.parse(JSON.stringify(finalMessageObject)));
        return finalMessageObject;

      } catch (e) {
        console.error(`[Debug] X. 处理消息时发生未知错误:`, e);
        const errorObject = { 
          message_id: frontendId,
          db_message_id: m.message_id,
          role: 'assistant', 
          content: `加载此条消息时出错: ${String(m.content)}`, 
          references: [] 
        };
        console.log(`[Debug] X. 返回错误消息对象:`, JSON.parse(JSON.stringify(errorObject)));
        return errorObject;
      }
    });
      // AI消息：解析content
    //   try {
    //     let content = typeof m.content === 'string' ? JSON.parse(m.content) : m.content;
    //     if (typeof content.text === 'string') {
    //       try {
    //         const nestedContent = JSON.parse(content.text);
    //         if (typeof nestedContent.text !== 'undefined') content = nestedContent;
    //       } catch (e) {  }
    //     }
    //     return { 
    //       message_id: frontendId,      // 前端稳定ID
    //       db_message_id: m.message_id, // 数据库真实ID
    //       role: 'assistant', 
    //       content: content.text || '', 
    //       references: content.references || [] 
    //     };
    //   } catch (e) {
    //     return { 
    //       message_id: frontendId,
    //       db_message_id: m.message_id,
    //       role: 'assistant', 
    //       content: String(m.content), 
    //       references: [] 
    //     };
    //   }
    // });
    scrollToBottom();
  } catch (error) {
    console.error("加载消息时出错:", error);
    messages.value = [{ 
      message_id: `error-${Date.now()}`,
      role: 'assistant', 
      content: '加载历史消息失败。' 
    }];
  }
};

const selectSession = async (sessionId) => {
  if (isLoading.value || currentSessionId.value === sessionId) return;
  currentSessionId.value = sessionId;
  messages.value = [];
  // When switching sessions, clear any pending images
  removeImage(null); 
  isLoading.value = true;
  try {
    await fetchMessages(sessionId);
  } finally {
    isLoading.value = false;
    // 切换会话后自动聚焦输入框
    nextTick(() => textareaRef.value?.focus());
  }
};

const fetchSessions = async () => {
  try {
    const response = await api.getSessions(userId);
    sessions.value = response.data;
    if (sessions.value.length > 0 && !currentSessionId.value) {
      await selectSession(sessions.value[0].session_id);
    }
  } catch (error) {
    console.error("加载会话列表时出错:", error);
  }
};

const createNewSession = async () => {
  if (isLoading.value) return;
  currentSessionId.value = null;
  useWeb.value = false
  messages.value = [];
  removeImage(null); // New session should not have pending images
  nextTick(() => textareaRef.value?.focus());
};

const handleStop = () => {
  console.log('[Chat] 用户点击停止按钮, isLoading=', isLoading.value);
  
  // 1. 中断网络请求
  if (abortController.value) {
    abortController.value.abort();
    abortController.value = null;
  }
  
  // 2. 立即重置状态（关键！防止卡死）
  isLoading.value = false;
  sendLock.value = false;
  
  // 3. 清理搜索步骤
  currentSearchSteps.value = [];
  
  // 4. 确保最后一条消息有正确的状态
  const lastMsg = messages.value[messages.value.length - 1];
  if (lastMsg && lastMsg.role === 'assistant') {
    // 如果还没有内容，显示"已停止"
    if (!lastMsg.content || lastMsg.content.trim() === '') {
      lastMsg.content = '回答已停止。';
    }
    lastMsg.streamEnded = true;  // 标记为已结束
  }
  
  console.log('[Chat] 停止完成，isLoading=', isLoading.value);
};

const sendMessage = async () => {
  console.log('[Chat] sendMessage called. isLoading=', isLoading.value, 'sendLock=', sendLock.value, 'userInput=', userInput.value);
  
  // 防御性检查：如果状态异常，先重置
  if (isLoading.value && !abortController.value) {
    console.warn('[Chat] 检测到状态异常：isLoading=true 但没有活动请求，重置状态');
    isLoading.value = false;
    sendLock.value = false;
  }
  
  // Guard against sending empty messages, unless there are images
  if (!userInput.value.trim() && pendingImages.value.length === 0) return;
  if (isLoading.value || sendLock.value) {
    console.warn('[Chat] Blocked duplicate send: isLoading or sendLock active');
    return;
  }

  // 短时间内相同内容去重
  const signature = `${userInput.value.trim()}|imgs:${pendingImages.value.map(i => i.previewUrl).join(',')}`;
  const now = Date.now();
  if (signature && signature === lastSendSignature.value && now - lastSendTime.value < 800) {
    console.warn('[Chat] Blocked rapid duplicate by signature');
    return;
  }
  lastSendSignature.value = signature;
  lastSendTime.value = now;
  sendLock.value = true;

  isLoading.value = true;
  let sessionIdToUse = currentSessionId.value;

  // 1. Ensure a session exists before sending anything
  if (!sessionIdToUse) {
    try {
      const title = userInput.value.trim().substring(0, 10) || '新对话';
      const response = await api.createSession(userId, title);
      sessionIdToUse = response.data.session_id;
      currentSessionId.value = sessionIdToUse;
      await fetchSessions();
    } catch (error) {
      console.error("创建新会话时出错:", error);
      messages.value.push({ role: 'assistant', content: '创建新会話失败，请重试。' });
      isLoading.value = false;
      return;
    }
  }

  const query = userInput.value;
  const hasImages = pendingImages.value.length > 0;
  
  // Add user's message to the UI immediately for better UX
  // 使用稳定的前端ID作为Vue的key，真实的message_id存储在 db_message_id 中
  const tempUserMessageIndex = messages.value.length;
  const frontendId = `frontend-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  
  const userMessage = { 
    message_id: frontendId,  // 前端稳定ID，用于Vue的key
    db_message_id: null,     // 数据库真实ID，后续会更新
    role: 'user', 
    content: query,
  };
  
  // 只有在有图片时才添加 image_url 字段
  if (hasImages) {
    userMessage.image_url = pendingImages.value.map(img => img.previewUrl);
  }
  
  messages.value.push(userMessage);
  
  // Prepare for assistant's response
  const frontendAssistantId = `frontend-assistant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  const assistantMessage = {
    message_id: frontendAssistantId,
    db_message_id: null,
    role: 'assistant',
    content: '',
    references: [],
    streamEnded: false,
  };
  initAssistantStreamState(assistantMessage);
  messages.value.push(assistantMessage);
  currentSearchSteps.value = [];
  scrollToBottom();

  // 2. 保存用户消息到数据库（有图片或无图片）
  try {
    const formData = new FormData();
    formData.append('text', query);
    formData.append('session_id', sessionIdToUse);
    formData.append('user_id', userId);
    
    // 只有在有图片时才添加图片
    if (hasImages) {
      pendingImages.value.forEach(img => {
        formData.append('images', img.blob, 'image.webp');
      });
    }
    // 注意：不添加空的 Blob

    // Call the endpoint to save the message
    console.log('[Chat] Calling sendMessageWithImages');
    const response = await api.sendMessageWithImages(formData);
    console.log('[Chat] sendMessageWithImages resp:', response);
    
    // 保存数据库真实ID到 db_message_id，但不改变前端的 message_id（保持Vue key稳定）
    if (response.message_id && messages.value[tempUserMessageIndex]) {
      messages.value[tempUserMessageIndex].db_message_id = response.message_id;
      console.log('[Chat] Saved db_message_id:', response.message_id, 'frontend_id:', messages.value[tempUserMessageIndex].message_id);
    }
    
    // Clear pending images and input
    if (hasImages) {
      removeImage(null);
    }
    userInput.value = '';
    autoGrowTextarea();

  } catch (error) {
    console.error("保存用户消息失败:", error);
    messages.value[messages.value.length - 1].content = `发送消息失败: ${error.message}`;
    messages.value[messages.value.length - 1].streamEnded = true;
    isLoading.value = false;
    return;
  }

  // 3. Always call searchStream to get the AI response
  // The backend will now have the latest message (with or without images) in its history
  abortController.value = new AbortController();
  // 如果当前有图片，强制使用直接LLM（不调用联网搜索）
  const shouldUseWeb = useWeb.value && !hasImages;
  const payload = {
    session_id: sessionIdToUse,
    user_id: userId,
    use_web: shouldUseWeb,
    selected_model: selectedModel.value?.name || null,
    // 明确传递 query 到后端，避免后端依赖历史中查找最新用户消息
    query: query,
  };

  try {
    let buffer = '';
    let fullResponseText = ''; // 收集完整的AI回复文本用于调试
    // 确保发送到后端的 payload 包含 query；若未设置则回退到最近一条 user 消息
    const payloadToSend = Object.assign({}, payload);
    if (!payloadToSend.query || payloadToSend.query === '') {
      const lastUser = [...messages.value].reverse().find(m => m.role === 'user');
      payloadToSend.query = lastUser ? lastUser.content : '';
    }
    retryPayload.value = payloadToSend;
    console.log('[Chat] Start searchStream. payload=', payloadToSend);
    await api.searchStream(
      payloadToSend,
      (chunk) => {
        buffer += chunk;
        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, newlineIndex);
          buffer = buffer.slice(newlineIndex + 1);
          if (line.trim()) {
            // 收集answer_chunk文本
            try {
              const chunkData = JSON.parse(line);
              if (chunkData.type === 'answer_chunk') {
                fullResponseText += chunkData.payload || '';
              }
            } catch (e) {
              // 忽略解析错误
            }
            processStreamChunk(line);
          }
        }
      },
      () => { // onComplete
        const lastMsg = messages.value[messages.value.length - 1];
        if (lastMsg && lastMsg.role === 'assistant') {
          lastMsg.streamEnded = true;
          finalizeAssistantStreamLog(lastMsg, 'searchStream');
          
          // 打印前端接收到的完整回复
          console.log('===== 前端接收 - 完整AI回复开始 =====');
          console.log('完整回复文本:\n', fullResponseText);
          console.log('消息对象content:\n', lastMsg.content);
          console.log('参考来源数量:', lastMsg.references ? lastMsg.references.length : 0);
          console.log('===== 前端接收 - 完整AI回复结束 =====');
        }
        console.log('[Chat] searchStream complete');
      },
      (error) => { // onError
        console.error('流处理错误:', error);
        
        // 立即重置状态（不依赖 finally，防止卡死）
        isLoading.value = false;
        sendLock.value = false;
        abortController.value = null;
        
        if (error.name === 'AbortError') {
          console.log('用户主动取消了请求');
          const lastMsg = messages.value[messages.value.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            if (!lastMsg.content || lastMsg.content.trim() === '') {
              lastMsg.content = '回答已停止。';
            }
            lastMsg.streamEnded = true;
            finalizeAssistantStreamLog(lastMsg, 'searchStream abort');
          }
        } else {
          console.error('网络错误:', error);
          const lastMsg = messages.value[messages.value.length - 1];
          if (lastMsg && lastMsg.role === 'assistant') {
            lastMsg.hasError = true;
            lastMsg.errorMessage = error.message || '网络或服务器错误，请稍后再试';
            lastMsg.streamEnded = true;
            finalizeAssistantStreamLog(lastMsg, 'searchStream error');
          }
        }
      },
      abortController.value.signal
    );
  } finally {
    isLoading.value = false;
    sendLock.value = false;
    abortController.value = null;
    userInput.value = ''; // Ensure input is cleared
    autoGrowTextarea();
    // Final rendering check
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.streamEnded = true;
      finalizeAssistantStreamLog(lastMsg, 'sendMessage finally');
    }
    console.log('[Chat] sendMessage finished');
  }
};

const processStreamChunk = (line) => {
  // 限制日志大小：仅打印前200字符
  if (typeof line === 'string') {
    const preview = line.length > 200 ? line.slice(0, 200) + ' ...' : line;
    console.debug('[Stream] chunk line:', preview);
  }
  try {
    const chunk = JSON.parse(line);
    const { type, payload } = chunk;
    const currentMessage = messages.value[messages.value.length - 1];

    switch (type) {
      case 'process': {
        let icon = '⏳'; 
        if (payload.includes("正在分析问题")) {
          icon = '🤔';
        } else if (payload.includes("不需要搜索")) {
          icon = '💬';
        } else if (payload.includes("搜索关键词")) {
          icon = '🔍';
        } else if (payload.includes("搜索完成")) {
          icon = '✅';
        }

        currentSearchSteps.value.push({
          text: payload,
          icon: icon,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        });
        scrollToBottom();
        break;
      }
      case 'answer_chunk':
        if (currentMessage && currentMessage.role === 'assistant') {
          appendAssistantStreamChunk(currentMessage, payload);
          currentMessage.content += payload;
          scrollToBottom();
        }
        break;
      case 'reference':
        if (currentMessage && currentMessage.role === 'assistant') {
          currentMessage.references = payload;
        }
        break;
      case 'error':
        if (currentMessage && currentMessage.role === 'assistant') {
          currentMessage.hasError = true;
          currentMessage.errorMessage = payload;
          currentMessage.streamEnded = true;
        }
        break;
    }
  } catch (error) {
    console.error('解析JSON块时出错:', error, '原始数据:', line);
  }
};

const handleEnter = (e) => {
  if (!e.shiftKey && !e.isComposing) {
    console.log('[Chat] handleEnter fired');
    e.preventDefault();
    sendMessage();
  }
};

const handleLogout = () => {
  sessionStorage.clear();
  router.push('/login');
};

const navigateToConfig = () => {
  router.push('/config');
};

const navigateToKnowledgeBase = () => {
  router.push('/knowledge-base');
};

// 处理重新生成
const handleRegenerate = async (message) => {
  if (isLoading.value) return;
  
  const messageIndex = messages.value.findIndex(m => m.message_id === message.message_id);
  if (messageIndex === -1) return;
  
  editingMessageIndex.value = messageIndex;
  messages.value = messages.value.slice(0, messageIndex + 1);
  
  const payload = {
    session_id: currentSessionId.value,
    message_id: message.db_message_id,  // 使用数据库真实ID
    new_query: message.content,
    new_image_urls: message.image_url ? (Array.isArray(message.image_url) ? message.image_url : [message.image_url]) : null,
    selected_model: selectedModel.value?.name || null,
    // 如果该消息带有图片，则强制直接LLM（不走联网搜索）
    use_web: (message.image_url && message.image_url.length > 0) ? false : useWeb.value
  };
  
  // 为新的AI回复生成前端ID
  const frontendAssistantId = `frontend-assistant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  const assistantMessage = {
    message_id: frontendAssistantId,
    db_message_id: null,
    role: 'assistant',
    content: '',
    references: [],
    streamEnded: false,
  };
  initAssistantStreamState(assistantMessage);
  messages.value.push(assistantMessage);
  currentSearchSteps.value = [];
  isLoading.value = true;
  
  await callRegenerateAPI(payload);
  editingMessageIndex.value = null;
};

// 处理编辑
const handleEdit = async ({ message, newContent, newImages }) => {
  if (isLoading.value) return;
  
  const messageIndex = messages.value.findIndex(m => m.message_id === message.message_id);
  if (messageIndex === -1) return;
  
  editingMessageIndex.value = messageIndex;
  messages.value[messageIndex].content = newContent;
  // 如果 newImages 是空数组，设置为 null，避免显示空的图片区域
  messages.value[messageIndex].image_url = (newImages && newImages.length > 0) ? newImages : null;
  messages.value = messages.value.slice(0, messageIndex + 1);
  
  const payload = {
    session_id: currentSessionId.value,
    message_id: message.db_message_id,  // 使用数据库真实ID
    new_query: newContent,
    new_image_urls: newImages && newImages.length > 0 ? newImages : null,
    selected_model: selectedModel.value?.name || null,
    // 如果新图片存在，则强制直接LLM（不走联网搜索）
    use_web: (newImages && newImages.length > 0) ? false : useWeb.value
  };
  
  // 为新的AI回复生成前端ID
  const frontendAssistantId = `frontend-assistant-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  const assistantMessage = {
    message_id: frontendAssistantId,
    db_message_id: null,
    role: 'assistant',
    content: '',
    references: [],
    streamEnded: false,
  };
  initAssistantStreamState(assistantMessage);
  messages.value.push(assistantMessage);
  currentSearchSteps.value = [];
  isLoading.value = true;
  
  await callRegenerateAPI(payload);
  editingMessageIndex.value = null;
};

// 处理重试
const handleRetry = async () => {
  if (!retryPayload.value || isLoading.value) return;
  
  const lastMsg = messages.value[messages.value.length - 1];
  if (lastMsg && lastMsg.hasError) {
    messages.value.pop();
  }
  
  const retryAssistant = { role: 'assistant', content: '', references: [], streamEnded: false };
  initAssistantStreamState(retryAssistant);
  messages.value.push(retryAssistant);
  currentSearchSteps.value = [];
  isLoading.value = true;
  
  await callSearchAPI(retryPayload.value);
};

// 调用regenerate API
const callRegenerateAPI = async (payload) => {
  abortController.value = new AbortController();
  let fullResponseText = ''; // 收集完整的AI回复文本用于调试
  
  try {
    await api.regenerateStream(
      payload,
      (chunk) => {
        const lines = chunk.split('\n').filter(line => line.trim());
        lines.forEach(line => {
          try {
            const data = JSON.parse(line);
            const lastMsg = messages.value[messages.value.length - 1];
            
            if (data.type === 'search_step') {
              currentSearchSteps.value.push({
                icon: data.payload.icon,
                text: data.payload.text,
                timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
              });
            } else if (data.type === 'answer_chunk') {
              fullResponseText += data.payload || ''; // 收集文本
              appendAssistantStreamChunk(lastMsg, data.payload);
              lastMsg.content += data.payload;
            } else if (data.type === 'reference') {
              if (!lastMsg.references) lastMsg.references = [];
              lastMsg.references.push(data.payload);
            } else if (data.type === 'error') {
              lastMsg.hasError = true;
              lastMsg.errorMessage = data.payload;
              lastMsg.streamEnded = true;
            }
            scrollToBottom();
          } catch (e) {
            console.error('解析chunk失败:', e);
          }
        });
      },
      () => {
        const lastMsg = messages.value[messages.value.length - 1];
        lastMsg.streamEnded = true;
        isLoading.value = false;
        abortController.value = null;
        finalizeAssistantStreamLog(lastMsg, 'regenerate');
        
        // 打印前端接收到的完整回复
        console.log('===== 前端接收(重新生成) - 完整AI回复开始 =====');
        console.log('完整回复文本:\n', fullResponseText);
        console.log('消息对象content:\n', lastMsg.content);
        console.log('参考来源数量:', lastMsg.references ? lastMsg.references.length : 0);
        console.log('===== 前端接收(重新生成) - 完整AI回复结束 =====');
        
        scrollToBottom();
      },
      (error) => {
        console.error('Regenerate失败:', error);
        
        // 立即重置状态（防止卡死）
        isLoading.value = false;
        sendLock.value = false;
        abortController.value = null;
        
        const lastMsg = messages.value[messages.value.length - 1];
        if (lastMsg && lastMsg.role === 'assistant') {
          if (error.name === 'AbortError') {
            if (!lastMsg.content || lastMsg.content.trim() === '') {
              lastMsg.content = '回答已停止。';
            }
          } else {
            lastMsg.hasError = true;
            lastMsg.errorMessage = error.message || '生成失败，请重试';
          }
          lastMsg.streamEnded = true;
          finalizeAssistantStreamLog(lastMsg, 'regenerate error');
        }
      },
      abortController.value.signal
    );
  } catch (error) {
    console.error('调用regenerate API失败:', error);
    
    // 立即重置状态（防止卡死）
    isLoading.value = false;
    sendLock.value = false;
    abortController.value = null;
    
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.hasError = true;
      lastMsg.errorMessage = error.message || '生成失败，请重试';
      lastMsg.streamEnded = true;
      finalizeAssistantStreamLog(lastMsg, 'regenerate catch');
    }
  }
};

// 调用search API
const callSearchAPI = async (payload) => {
  abortController.value = new AbortController();
  retryPayload.value = payload;
  
  try {
    await api.searchStream(
      payload,
      (chunk) => {
        const lines = chunk.split('\n').filter(line => line.trim());
        lines.forEach(line => {
          try {
            const data = JSON.parse(line);
            const lastMsg = messages.value[messages.value.length - 1];
            
            if (data.type === 'search_step') {
              currentSearchSteps.value.push({
                icon: data.payload.icon,
                text: data.payload.text,
                timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
              });
            } else if (data.type === 'answer_chunk') {
              appendAssistantStreamChunk(lastMsg, data.payload);
              lastMsg.content += data.payload;
            } else if (data.type === 'reference') {
              if (!lastMsg.references) lastMsg.references = [];
              lastMsg.references.push(data.payload);
            } else if (data.type === 'error') {
              lastMsg.hasError = true;
              lastMsg.errorMessage = data.payload;
              lastMsg.streamEnded = true;
            }
            scrollToBottom();
          } catch (e) {
            console.error('解析chunk失败:', e);
          }
        });
      },
      () => {
        const lastMsg = messages.value[messages.value.length - 1];
        lastMsg.streamEnded = true;
        isLoading.value = false;
        abortController.value = null;
        retryPayload.value = null;
        finalizeAssistantStreamLog(lastMsg, 'search retry');
        scrollToBottom();
      },
      (error) => {
        console.error('Search失败:', error);
        
        // 立即重置状态（防止卡死）
        isLoading.value = false;
        sendLock.value = false;
        abortController.value = null;
        retryPayload.value = null;
        
        const lastMsg = messages.value[messages.value.length - 1];
        if (lastMsg && lastMsg.role === 'assistant') {
          if (error.name === 'AbortError') {
            if (!lastMsg.content || lastMsg.content.trim() === '') {
              lastMsg.content = '回答已停止。';
            }
          } else {
            lastMsg.hasError = true;
            lastMsg.errorMessage = error.message || '生成失败，请重试';
          }
          lastMsg.streamEnded = true;
          finalizeAssistantStreamLog(lastMsg, 'search retry error');
        }
      },
      abortController.value.signal
    );
  } catch (error) {
    console.error('调用search API失败:', error);
    
    // 立即重置状态（防止卡死）
    isLoading.value = false;
    sendLock.value = false;
    abortController.value = null;
    retryPayload.value = null;
    
    const lastMsg = messages.value[messages.value.length - 1];
    if (lastMsg && lastMsg.role === 'assistant') {
      lastMsg.hasError = true;
      lastMsg.errorMessage = error.message || '生成失败，请重试';
      lastMsg.streamEnded = true;
      finalizeAssistantStreamLog(lastMsg, 'search retry catch');
    }
  }
};

// 获取可用的对话模型列表
const fetchChatModels = async () => {
  try {
    const response = await api.getChatModels();
    if (response.data.success && response.data.models) {
      availableModels.value = response.data.models;
      // 设置默认模型
      const defaultModel = availableModels.value.find(m => m.is_default);
      if (defaultModel) {
        selectedModel.value = defaultModel;
      } else if (availableModels.value.length > 0) {
        selectedModel.value = availableModels.value[0];
      }
      console.log('已加载对话模型列表:', availableModels.value);
      console.log('默认模型:', selectedModel.value);
    }
  } catch (error) {
    console.error('获取对话模型列表失败:', error);
  }
};

// 处理模型选择
const handleModelSelect = (model) => {
  selectedModel.value = model;
  console.log('切换到模型:', model.name);
};

// 触发文件上传
const triggerFileUpload = () => {
  showMenuDropdown.value = false; // 关闭菜单
  if (fileInput.value) {
    fileInput.value.click();
  }
};

// 处理文件上传
const handleFileUpload = async (event) => {
  const files = Array.from(event.target.files);
  if (files.length > 0) {
    for (const file of files) {
      const id = Date.now() + Math.random();
      pendingImages.value.push({
        id,
        file,
        blob: file, // 直接使用File对象作为blob
        previewUrl: URL.createObjectURL(file)
      });
    }
    if (fileInput.value) {
      fileInput.value.value = '';
    }
  }
};

// 触发菜单下拉
const triggerImageUploadFromMenu = () => {
  showMenuDropdown.value = false; // 关闭菜单
  triggerImageUpload(); // 触发图片上传
};

// 切换上传菜单并计算位置
const toggleUploadMenu = () => {
  showMenuDropdown.value = !showMenuDropdown.value;
  if (showMenuDropdown.value) {
    nextTick(() => {
      updateUploadMenuPosition();
    });
  }
};

// 更新上传菜单位置
const updateUploadMenuPosition = () => {
  if (uploadMenuButton.value) {
    const rect = uploadMenuButton.value.getBoundingClientRect();
    uploadMenuStyle.value = {
      bottom: `${window.innerHeight - rect.top + 8}px`,
      left: `${rect.left}px`
    };
  }
};

// 更新输入框区域高度，动态调整消息容器的底部内边距
const updateInputAreaHeight = () => {
  if (inputAreaRef.value) {
    const height = inputAreaRef.value.offsetHeight;
    // 添加额外的20px作为缓冲，确保消息不会被遮挡
    dynamicPaddingBottom.value = `${height + 20}px`;
  }
};

// 点击外部关闭菜单
const handleClickOutside = (e) => {
  if (showMenuDropdown.value) {
    // 检查点击是否在按钮或菜单内部
    const isClickInsideButton = uploadMenuButton.value && uploadMenuButton.value.contains(e.target);
    const isClickInsideMenu = uploadMenu.value && uploadMenu.value.contains(e.target);
    
    // 如果点击在按钮和菜单外部，则关闭菜单
    if (!isClickInsideButton && !isClickInsideMenu) {
      showMenuDropdown.value = false;
    }
  }
};

// ResizeObserver 实例
let inputAreaResizeObserver = null;

onMounted(() => {
  fetchSessions();
  fetchChatModels();  // 加载模型列表
  
  // 添加全局点击事件监听
  document.addEventListener('click', handleClickOutside);
  
  // 初始化输入框高度和自动聚焦
  nextTick(() => {
    updateInputAreaHeight();
    
    // 使用 ResizeObserver 监听输入框区域高度变化
    if (inputAreaRef.value) {
      inputAreaResizeObserver = new ResizeObserver(() => {
        updateInputAreaHeight();
      });
      inputAreaResizeObserver.observe(inputAreaRef.value);
    }
    
    // 页面加载完成后自动聚焦输入框
    textareaRef.value?.focus();
  });
});

onUnmounted(() => {
  console.log('[Chat] 组件卸载，清理资源');
  
  // 1. 移除事件监听
  document.removeEventListener('click', handleClickOutside);
  
  // 2. 清理 ResizeObserver
  if (inputAreaResizeObserver) {
    inputAreaResizeObserver.disconnect();
    inputAreaResizeObserver = null;
  }
  
  // 3. 中断正在进行的请求（关键！防止幽灵请求）
  if (abortController.value) {
    console.log('[Chat] 中断未完成的请求');
    abortController.value.abort();
    abortController.value = null;
  }
  
  // 4. 重置所有状态
  isLoading.value = false;
  sendLock.value = false;
  
  // 5. 清理图片预览 URL（防止内存泄漏）
  pendingImages.value.forEach(img => {
    if (img.previewUrl) {
      URL.revokeObjectURL(img.previewUrl);
    }
  });
  pendingImages.value = [];
});

watch(userInput, autoGrowTextarea);
</script>

<style scoped>

.overflow-y-auto {
  scrollbar-width: thin;
  scrollbar-color: rgba(156, 163, 175, 0.5) transparent;
}
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}
.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}
.overflow-y-auto::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.5);
  border-radius: 3px;
}
.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: rgba(156, 163, 175, 0.8);
}

/* 浏览器兼容性 - 确保输入框字体在Chrome和Edge中显示一致 */
textarea {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  font-feature-settings: "kern" 1;
}

/* textarea滚动条样式 */
.textarea-scrollable {
  scrollbar-width: thin;
  scrollbar-color: rgba(156, 163, 175, 0.5) transparent;
}

.textarea-scrollable::-webkit-scrollbar {
  width: 6px;
}

.textarea-scrollable::-webkit-scrollbar-track {
  background: transparent;
}

.textarea-scrollable::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.5);
  border-radius: 3px;
}

.textarea-scrollable::-webkit-scrollbar-thumb:hover {
  background: rgba(156, 163, 175, 0.8);
}

.animate-fade-in {
  animation: fadeIn 0.6s ease-out;
}
.animate-slide-in {
  animation: slideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
@keyframes slideIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
textarea:focus + .absolute {
  background: linear-gradient(90deg, transparent, theme('colors.blue.400'), transparent);
  opacity: 0.6;
  transition: opacity 0.3s ease;
}
@media (max-width: 768px) {
  .absolute.bottom-0 {
    padding-left: 1rem;
    padding-right: 1rem;
  }
}
</style>