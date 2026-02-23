<template>
  <div ref="messageEl" class="message-container py-3 px-6 group"
       :class="{ 
         'opacity-40': isMarkedForDeletion
       }">
    <div class="max-w-4xl mx-auto flex items-start space-x-4" :class="{ 'flex-row-reverse space-x-reverse': isUser }">
      <!-- 头像 -->
      <div v-if="!isUser" class="flex-shrink-0">
        <div class="w-16 h-16 flex items-center justify-center transition-all duration-200 hover:scale-110">
          <ViewRAGMascot :status="mascotStatus" style="width:64px;height:64px;max-width:64px;" />
        </div>
      </div>

      <div class="flex-grow pt-0 relative" :class="{ 'flex flex-col items-end': isUser }">
        
        <!-- 用户消息：正常显示模式 -->
        <div v-if="isUser && !isEditing" class="space-y-2 flex flex-col items-end w-full">
          <!-- 附带的文档显示在用户消息上方 -->
          <div v-if="message.attached_documents && message.attached_documents.length > 0" class="mb-3 flex flex-wrap gap-2 justify-end">
            <div
              v-for="doc in message.attached_documents"
              :key="doc.doc_id"
              class="inline-flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-200"
            >
              <!-- 文件类型图标 -->
              <div
                class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold"
                :class="getDocTypeStyle(doc.document_type).bgClass"
              >
                <span :class="getDocTypeStyle(doc.document_type).textClass">
                  {{ getDocTypeStyle(doc.document_type).label }}
                </span>
              </div>
              <!-- 文件名 -->
              <div class="flex-1 min-w-0 max-w-[200px]">
                <div class="text-sm font-medium text-gray-900 truncate">{{ doc.file_name }}</div>
              </div>
            </div>
          </div>
          
          <!-- 图片显示在用户消息上方（Flex布局，一行最多3个，右对齐） -->
          <div v-if="normalizedImageUrls.length > 0" class="mb-2 flex flex-wrap justify-end gap-2 max-w-[260px]">
            <div
              v-for="(imgUrl, idx) in normalizedImageUrls"
              :key="idx"
              class="relative w-20 h-20 rounded-lg overflow-hidden border border-gray-200 shadow-sm cursor-pointer hover:shadow-md hover:border-gray-300 transition-all duration-200"
              @click="openImagePreview(imgUrl)"
            >
              <img 
                :src="imgUrl.startsWith('blob:') ? imgUrl : '/backend' + imgUrl" 
                alt="用户上传的图片" 
                class="w-full h-full object-cover"
              />
            </div>
          </div>

          <!-- 图片放大预览弹窗（Teleport 到 body 确保全屏居中） -->
          <Teleport to="body">
            <div
              v-if="imagePreviewVisible"
              class="fixed inset-0 z-[10000] flex items-center justify-center cursor-pointer"
              style="background: rgba(0, 0, 0, 0.6);"
              @click.self="closeImagePreview"
            >
              <button
                class="absolute top-6 right-6 w-10 h-10 flex items-center justify-center rounded-full text-white hover:bg-white hover:bg-opacity-20 transition-all duration-200 text-3xl z-10"
                @click="closeImagePreview"
                title="关闭"
              >&times;</button>
              <img
                :src="imagePreviewUrl"
                alt="预览大图"
                class="max-w-[85vw] max-h-[85vh] object-contain rounded-lg shadow-2xl"
                @click.stop
              />
            </div>
          </Teleport>
          <!-- 文本消息 -->
          <div class="leading-relaxed bg-blue-50 text-gray-900 px-5 py-3 rounded-2xl rounded-tr-sm shadow-sm max-w-[85%] text-left whitespace-pre-wrap" style="font-size: 1rem;">
            {{ message.content }}
          </div>
          
          <!-- 用户消息操作栏 -->
          <div class="flex items-center space-x-2 mt-1 mr-1 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
             <!-- 复制按钮 -->
             <button @click="copyFullResponse" class="relative group/btn p-1.5 hover:bg-gray-100 rounded-lg text-gray-500 hover:text-gray-700 transition-colors">
               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
               </svg>
               <span class="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-black text-white text-xs px-2 py-1 rounded opacity-0 group-hover/btn:opacity-100 pointer-events-none transition-opacity duration-150 whitespace-nowrap z-20 shadow-lg">
                 {{ copyButtonText }}
               </span>
             </button>
             
             <!-- 编辑按钮 -->
             <button @click="startEditing" class="relative group/btn p-1.5 hover:bg-gray-100 rounded-lg text-gray-500 hover:text-gray-700 transition-colors">
               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                 <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
               </svg>
               <span class="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-black text-white text-xs px-2 py-1 rounded opacity-0 group-hover/btn:opacity-100 pointer-events-none transition-opacity duration-150 whitespace-nowrap z-20 shadow-lg">
                 编辑
               </span>
             </button>
             
             <!-- 重新生成按钮 -->
             <button @click="$emit('regenerate', message)" class="relative group/btn p-1.5 hover:bg-gray-100 rounded-lg text-gray-500 hover:text-gray-700 transition-colors">
               <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                 <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
               </svg>
               <span class="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-black text-white text-xs px-2 py-1 rounded opacity-0 group-hover/btn:opacity-100 pointer-events-none transition-opacity duration-150 whitespace-nowrap z-20 shadow-lg">
                 重新生成
               </span>
             </button>
          </div>
        </div>

        <!-- 用户消息：编辑模式 -->
        <div v-if="isUser && isEditing" class="space-y-3">
          <!-- 可编辑的文本框 -->
          <textarea
            ref="editTextarea"
            v-model="editedContent"
            class="w-full p-3 border-2 border-blue-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-200 resize-none text-text-primary"
            :style="{ minHeight: '80px', maxHeight: '300px', fontSize: '1rem' }"
            rows="3"
            placeholder="编辑你的消息..."
          ></textarea>

          <!-- 图片管理（如果有图片） -->
          <div v-if="editedImages.length > 0" class="flex flex-wrap gap-2">
            <div v-for="(img, index) in editedImages" :key="index" class="relative inline-block">
              <img :src="img.startsWith('blob:') ? img : '/backend' + img" alt="图片" class="w-20 h-20 object-cover rounded-lg border border-gray-200" />
              <button
                @click="removeEditImage(index)"
                class="absolute -top-1 -right-1 w-5 h-5 bg-red-500 text-white rounded-full hover:bg-red-600 flex items-center justify-center shadow-md transition-all duration-200 hover:scale-110 text-xs"
                title="删除图片"
              >
                ×
              </button>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex items-center space-x-2">
            <button
              @click="cancelEditing"
              class="px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-sm font-medium transition-all duration-200 flex items-center space-x-1"
            >
              <span>取消</span>
            </button>
            <button
              @click="submitEdit"
              :disabled="!editedContent.trim()"
              class="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-all duration-200 flex items-center space-x-1"
            >
              <span>发送</span>
            </button>
          </div>
        </div>

        
        <!-- AI消息 -->
        <div v-if="!isUser" class="space-y-3">
          <!-- 错误提示和重试按钮 -->
          <div v-if="hasError" class="bg-red-50 border border-red-200 rounded-lg p-4 space-y-3">
            <div class="flex items-start space-x-2">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div class="flex-1">
                <h4 class="text-red-800 font-medium text-sm">生成失败</h4>
                <p class="text-red-700 text-sm mt-1">{{ errorMessage || '服务暂时不可用，请稍后重试' }}</p>
              </div>
            </div>
            <button
              @click="$emit('retry')"
              class="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition-all duration-200 flex items-center justify-center space-x-2"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>重试</span>
            </button>
          </div>

          <!-- 等待提示 -->
          <div v-if="showWaitingIndicator" class="waiting-indicator">
            <span class="text-sm text-gray-400">{{ waitingText }}</span>
          </div>

          <!-- 参考文档提示 -->
          <div v-if="props.retrievedDocuments && props.retrievedDocuments.length > 0"
               class="ref-docs-hint flex items-center space-x-1 cursor-pointer select-none group/hint w-fit py-1.5 rounded-lg transition-colors duration-200 hover:bg-gray-50/50"
               @click="docPanelVisible = true">
             <div class="w-5 h-5 flex items-center justify-center text-gray-400 group-hover/hint:text-black transition-all duration-300">
               <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                 <polyline points="9 18 15 12 9 6"></polyline>
               </svg>
             </div>
            <span class="text-sm text-gray-500 font-medium group-hover/hint:text-black transition-colors duration-150">
              找到了 <span class="font-semibold">{{ props.retrievedDocuments.length }}</span> 篇参考文档
            </span>
          </div>

          <!-- 思考过程折叠块 -->
          <ThinkingBlock
            v-if="message.thinking_content || message.isThinking"
            v-model:is-collapsed="thinkingCollapsed"
            :content="message.thinking_content"
            :is-thinking="message.isThinking"
            :duration="message.thinking_duration || 0"
          />

          <!-- 正式回答 -->
          <div v-if="message.content.trim()" class="space-y-4">
            <div class="markdown-renderer-container prose"
              v-html="formattedContent"
              @mouseenter.capture="onRefMarkerEnter"
              @mouseleave.capture="onRefMarkerLeave"
              @click.capture="onRefMarkerClick"
            ></div>

            
            <div v-if="message.content.trim() && !isStreaming" class="flex items-center justify-start -mt-2">
                <button @click="copyFullResponse" class="copy-full-response-button">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span>{{ copyButtonText }}</span>
                </button>
            </div>


            
            <!-- 参考资料右侧面板 -->
            <ReferenceDocPanel
              :visible="docPanelVisible"
              :documents="props.retrievedDocuments"
              @close="docPanelVisible = false"
              @open-doc="onDocPanelOpenDoc"
            />
          </div>

          
        </div>

        <!-- PreviewPopup 悬停预览弹窗 -->
        <PreviewPopup
          v-if="previewPopupRef"
          :reference="previewPopupRef"
          :position="previewPopupPosition"
          :visible="previewPopupVisible"
          @open-pdf="onPopupOpenPdf"
          @close="previewPopupVisible = false"
          @mouseenter="onPopupMouseEnter"
          @mouseleave="onPopupMouseLeave"
        />

        <!-- PDFViewerModal PDF 查看器 -->
        <PDFViewerModal
          v-if="pdfViewerRef"
          :visible="pdfViewerVisible"
          :doc-id="pdfViewerRef.doc_id"
          :file-name="pdfViewerRef.file_name"
          :chunk-bboxes="pdfViewerRef.chunk_bboxes"
          :chunk-type="pdfViewerRef.chunk_type"
          @close="pdfViewerVisible = false"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUpdated, onBeforeUnmount } from 'vue';
import { marked } from 'marked';
import hljs from 'highlight.js';
import 'highlight.js/styles/atom-one-light.css';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import { processReferences } from '@/utils/referenceRenderer.js';
import PreviewPopup from '@/components/chat/PreviewPopup.vue';
import PDFViewerModal from '@/components/pdf/PDFViewerModal.vue';
import ReferenceDocPanel from '@/components/chat/ReferenceDocPanel.vue';
import ThinkingBlock from '@/components/chat/ThinkingBlock.vue';
import ViewRAGMascot from '@/components/ViewRAGMascot.vue';

const props = defineProps({
  message: { type: Object, required: true },
  userId: { type: String, required: true },
  isStreaming: { type: Boolean, default: false },
  searchSteps: { type: Array, default: () => [] },
  isMarkedForDeletion: { type: Boolean, default: false },
  hasError: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
  /** ReferenceItem[] 引用数据 */
  references: { type: Array, default: () => [] },
  /** 引用是否可交互（流结束后为 true） */
  isInteractive: { type: Boolean, default: false },
  /** 图片别名 → URL 映射 */
  imageMapping: { type: Object, default: () => new Map() },
  /** ref_id → ReferenceItem 映射 */
  referencesMap: { type: Object, default: () => new Map() },
  /** 召回的文档列表（后端返回） */
  retrievedDocuments: { type: Array, default: () => [] },
  /** 等待场景类型 */
  pendingScenario: { type: String, default: null },
  /** 玩偶状态：'idle' | 'thinking' | 'answering' */
  mascotStatus: { type: String, default: 'idle' },
});

const emit = defineEmits(['regenerate', 'edit', 'retry', 'open-pdf']);

// ---- 思考过程折叠状态 ----
const thinkingCollapsed = ref(true);

// ---- 引用交互状态 ----
const previewPopupVisible = ref(false);
const previewPopupRef = ref(null); // 当前悬停的 ReferenceItem
const previewPopupPosition = ref({ x: 0, y: 0 });
let showPopupTimer = null;
let hidePopupTimer = null;

const pdfViewerVisible = ref(false);
const pdfViewerRef = ref(null); // 当前打开 PDF 的 ReferenceItem

// ---- 参考资料面板状态 ----
const docPanelVisible = ref(false);

const messageEl = ref(null);
const editTextarea = ref(null);
const copyButtonText = ref('复制');
const isEditing = ref(false);
const editedContent = ref('');
const editedImages = ref([]);

const isUser = computed(() => props.message.role === 'user');
const userInitial = computed(() => props.userId ? props.userId.charAt(0).toUpperCase() : 'Y');

// 等待提示相关
const showWaitingIndicator = computed(() => {
  return !isUser.value && 
         props.pendingScenario && 
         !props.message.content && 
         !props.message.thinking_content &&
         !props.message.isThinking &&
         props.retrievedDocuments.length === 0;
});

const waitingText = computed(() => {
  if (props.pendingScenario === 'retrieval') {
    return '正在搜索资料...';
  }
  return '正在思考...';
});

// 将 image_url 统一为数组格式
const normalizedImageUrls = computed(() => {
  const urls = props.message.image_url;
  if (!urls) return [];
  if (Array.isArray(urls)) return urls.filter(Boolean);
  return [urls];
});

// 图片放大预览状态
const imagePreviewVisible = ref(false);
const imagePreviewUrl = ref('');

const openImagePreview = (imgUrl) => {
  imagePreviewUrl.value = imgUrl.startsWith('blob:') ? imgUrl : '/backend' + imgUrl;
  imagePreviewVisible.value = true;
};

const closeImagePreview = () => {
  imagePreviewVisible.value = false;
  imagePreviewUrl.value = '';
};

// 获取文档类型样式
const getDocTypeStyle = (docType) => {
  const typeMap = {
    'PDF': { label: 'PDF', bgClass: 'bg-red-50', textClass: 'text-red-500' },
    'DOCX': { label: 'DOC', bgClass: 'bg-blue-50', textClass: 'text-blue-500' },
    'TXT': { label: 'TXT', bgClass: 'bg-gray-100', textClass: 'text-gray-600' },
    'MARKDOWN': { label: 'MD', bgClass: 'bg-purple-50', textClass: 'text-purple-500' },
    'PPTX': { label: 'PPT', bgClass: 'bg-orange-50', textClass: 'text-orange-500' },
    'IMAGE': { label: 'IMG', bgClass: 'bg-green-50', textClass: 'text-green-500' },
  };
  return typeMap[docType] || { label: 'FILE', bgClass: 'bg-gray-100', textClass: 'text-gray-600' };
};

// 数学公式渲染函数
const processMathFormulas = (text) => {
  if (!text) return { processedText: text, mathPlaceholders: [] };
  
  const mathPlaceholders = [];
  let processedText = text;
  
  // 首先处理块级公式 $$...$$（使用更严格的匹配）
  processedText = processedText.replace(/\$\$([^\$]+?)\$\$/g, (match, formula) => {
    try {
      const rendered = katex.renderToString(formula.trim(), {
        displayMode: true,
        throwOnError: false,
        strict: false,
        output: 'html'
      });
      // 使用不会被HTML转义的占位符格式
      const placeholder = `MATHBLOCKPLACEHOLDER${mathPlaceholders.length}ENDPLACEHOLDER`;
      mathPlaceholders.push({ placeholder, html: rendered, type: 'block' });
      return placeholder;
    } catch (e) {
      console.warn('LaTeX block render error:', e, 'Formula:', formula);
      return match; // 如果渲染失败，返回原文
    }
  });
  
  // 然后处理行内公式 $...$（避免匹配到 $$ 的情况）
  processedText = processedText.replace(/(?<!\$)\$(?!\$)([^\$\n]+?)\$(?!\$)/g, (match, formula) => {
    try {
      const rendered = katex.renderToString(formula.trim(), {
        displayMode: false,
        throwOnError: false,
        strict: false,
        output: 'html'
      });
      // 使用不会被HTML转义的占位符格式
      const placeholder = `MATHINLINEPLACEHOLDER${mathPlaceholders.length}ENDPLACEHOLDER`;
      mathPlaceholders.push({ placeholder, html: rendered, type: 'inline' });
      return placeholder;
    } catch (e) {
      console.warn('LaTeX inline render error:', e, 'Formula:', formula);
      return match; // 如果渲染失败，返回原文
    }
  });
  
  return { processedText, mathPlaceholders };
};

marked.setOptions({
  gfm: true,
  breaks: true,
  highlight: (code, lang) => {
    const language = hljs.getLanguage(lang) ? lang : 'plaintext';
    return hljs.highlight(code, { language }).value;
  },
});

const formattedContent = computed(() => {
  if (isUser.value) return props.message.content;
  if (typeof props.message.content !== 'string') return '';
  let cleanContent = props.message.content;
  
  // 先提取并渲染数学公式，用占位符替代
  const { processedText, mathPlaceholders } = processMathFormulas(cleanContent);
  
  // 处理markdown
  let htmlContent = marked(processedText);
  
  // 将占位符替换为渲染好的数学公式
  mathPlaceholders.forEach((item) => {
    const foundIndex = htmlContent.indexOf(item.placeholder);
    if (foundIndex !== -1) {
      htmlContent = htmlContent.substring(0, foundIndex) + item.html + htmlContent.substring(foundIndex + item.placeholder.length);
    }
  });

  // 引用标记后处理：将 [N] 和 ![desc](image:图片N) 替换为交互式 HTML
  if (props.references && props.references.length > 0) {
    htmlContent = processReferences(htmlContent, {
      isInteractive: props.isInteractive,
      imageMapping: props.imageMapping instanceof Map ? props.imageMapping : new Map(Object.entries(props.imageMapping || {})),
      references: props.referencesMap instanceof Map ? props.referencesMap : new Map(Object.entries(props.referencesMap || {})),
    });
  }
  
  return htmlContent;
});

// ---- 引用标记事件委托 ----

/**
 * 根据 ref_id 查找 ReferenceItem
 */
function findReference(refId) {
  const id = Number(refId);
  if (props.referencesMap instanceof Map) {
    return props.referencesMap.get(id);
  }
  return props.references?.find(r => r.ref_id === id);
}

/**
 * 处理引用标记 mouseenter（事件委托）
 */
function onRefMarkerEnter(event) {
  if (!props.isInteractive) return;
  const target = event.target.closest('.ref-marker');
  if (!target) return;

  const refId = target.dataset.refId;
  const refItem = findReference(refId);
  if (!refItem) return;

  clearTimeout(hidePopupTimer);
  showPopupTimer = setTimeout(() => {
    previewPopupRef.value = refItem;
    // 计算弹窗位置：标记下方偏移
    const rect = target.getBoundingClientRect();
    previewPopupPosition.value = {
      x: Math.min(rect.left, window.innerWidth - 340),
      y: rect.bottom + 6
    };
    previewPopupVisible.value = true;
  }, 200);
}

/**
 * 处理引用标记 mouseleave（事件委托）
 */
function onRefMarkerLeave(event) {
  const target = event.target.closest('.ref-marker');
  if (!target) return;

  clearTimeout(showPopupTimer);
  hidePopupTimer = setTimeout(() => {
    previewPopupVisible.value = false;
  }, 300);
}

/**
 * 处理引用标记 click（事件委托）
 */
function onRefMarkerClick(event) {
  if (!props.isInteractive) return;
  const target = event.target.closest('.ref-marker');
  if (!target) return;

  const refId = target.dataset.refId;
  const refItem = findReference(refId);
  if (!refItem) return;

  // 关闭预览弹窗，打开 PDF 查看器
  previewPopupVisible.value = false;
  openPdfViewer(refItem);
}

/**
 * 打开 PDF 查看器（新标签页）
 */
function openPdfViewer(refItem) {
  const params = new URLSearchParams({
    docId: refItem.doc_id,
    fileName: refItem.file_name,
    chunkType: refItem.chunk_type,
    bboxes: JSON.stringify(refItem.chunk_bboxes)
  })
  window.open(`/pdf-viewer?${params.toString()}`, '_blank')
}

/**
 * PreviewPopup 鼠标移入 → 保持弹窗可见
 */
function onPopupMouseEnter() {
  clearTimeout(hidePopupTimer);
}

/**
 * PreviewPopup 鼠标移出 → 延迟隐藏
 */
function onPopupMouseLeave() {
  hidePopupTimer = setTimeout(() => {
    previewPopupVisible.value = false;
  }, 300);
}

/**
 * PreviewPopup "查看原文" 点击
 */
function onPopupOpenPdf() {
  previewPopupVisible.value = false;
  if (previewPopupRef.value) {
    openPdfViewer(previewPopupRef.value);
  }
}

/**
 * ReferenceSummary 点击摘要项
 */
function onSummaryOpenPdf(refItem) {
  openPdfViewer(refItem);
}

/**
 * ReferenceDocPanel 点击文档项
 */
function onDocPanelOpenDoc(doc) {
  // 从 references 中找到该文档的第一个引用，打开 PDF
  const refItem = props.references?.find(r => r.doc_id === doc.doc_id);
  if (refItem) {
    docPanelVisible.value = false;
    openPdfViewer(refItem);
  }
}

// 清理定时器
onBeforeUnmount(() => {
  clearTimeout(showPopupTimer);
  clearTimeout(hidePopupTimer);
});

// 开始编辑
const startEditing = () => {
  isEditing.value = true;
  editedContent.value = props.message.content;
  
  // 处理图片URL
  if (props.message.image_url) {
    if (Array.isArray(props.message.image_url)) {
      editedImages.value = [...props.message.image_url];
    } else {
      editedImages.value = [props.message.image_url];
    }
  } else {
    editedImages.value = [];
  }
  
  // 聚焦到textarea
  setTimeout(() => {
    if (editTextarea.value) {
      editTextarea.value.focus();
    }
  }, 100);
};

// 取消编辑
const cancelEditing = () => {
  isEditing.value = false;
  editedContent.value = '';
  editedImages.value = [];
};

// 提交编辑
const submitEdit = () => {
  if (!editedContent.value.trim()) return;
  
  emit('edit', {
    message: props.message,
    newContent: editedContent.value.trim(),
    newImages: editedImages.value
  });
  
  isEditing.value = false;
};

// 删除编辑中的图片
const removeEditImage = (index) => {
  editedImages.value.splice(index, 1);
};

// References 处理（已移除旧的 flattenedReferences，改用顶部"找到了N篇知识库资料"）

// 复制完整回复
const copyFullResponse = () => {
    if (navigator.clipboard && props.message.content) {
        navigator.clipboard.writeText(props.message.content).then(() => {
            copyButtonText.value = '已复制!';
            setTimeout(() => {
                copyButtonText.value = '复制';
            }, 2000);
        });
    }
};

const setupCodeBlocks = () => {
  if (!messageEl.value) return;
  messageEl.value.querySelectorAll('pre').forEach(preEl => {
    if (preEl.closest('.code-block-container')) return;
    const codeEl = preEl.querySelector('code');
    if (!codeEl) return;
    const languageClass = Array.from(codeEl.classList).find(cls => cls.startsWith('language-'));
    const languageName = languageClass ? languageClass.replace('language-', '') : null;
    const container = document.createElement('div');
    container.className = 'code-block-container';
    const header = document.createElement('div');
    header.className = 'code-block-header';
    const langSpan = document.createElement('span');
    langSpan.className = 'language-name';
    langSpan.textContent = languageName || 'Code';
    const copyIconSVG = `
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
      </svg>`;
    const successIconSVG = `
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="text-green-500" viewBox="0 0 16 16">
        <path d="M12.736 3.97a.733.733 0 0 1 1.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 0 1-1.065.02L3.217 8.384a.757.757 0 0 1 0-1.06.733.733 0 0 1 1.047 0l3.052 3.093 5.4-6.425a.247.247 0 0 1 .02-.022Z"/>
      </svg>`;
    const copyButton = document.createElement('button');
    copyButton.className = 'copy-code-button';
    copyButton.innerHTML = copyIconSVG;
    let copyTimeout;
    copyButton.onclick = () => {
      navigator.clipboard.writeText(codeEl.innerText).then(() => {
        copyButton.innerHTML = successIconSVG;
        clearTimeout(copyTimeout);
        copyTimeout = setTimeout(() => {
          copyButton.innerHTML = copyIconSVG;
        }, 2000);
      });
    };
    header.appendChild(langSpan);
    header.appendChild(copyButton);
    container.appendChild(header);
    preEl.parentNode.insertBefore(container, preEl);
    container.appendChild(preEl);
  });
};

onMounted(setupCodeBlocks);
onUpdated(setupCodeBlocks);
</script>

<style>
.prose {
  --tw-prose-body: theme('colors.text-primary');
  --tw-prose-headings: theme('colors.text-primary');
  --tw-prose-lead: theme('colors.text-secondary');
  --tw-prose-links: theme('colors.blue.600');
  --tw-prose-bold: theme('colors.text-primary');
  --tw-prose-counters: theme('colors.text-secondary');
  --tw-prose-bullets: theme('colors.text-secondary');
  --tw-prose-hr: theme('colors.gray.200');
  --tw-prose-quotes: theme('colors.text-primary');
  --tw-prose-quote-borders: theme('colors.gray.200');
  --tw-prose-captions: theme('colors.text-secondary');
  --tw-prose-code: theme('colors.text-primary');
  --tw-prose-pre-code: theme('colors.gray.800');
  --tw-prose-pre-bg: #f6f8fa;
  --tw-prose-th-borders: theme('colors.gray.300');
  --tw-prose-td-borders: theme('colors.gray.200');
}

.prose table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1.25em;
  margin-bottom: 1.25em;
  border: 1px solid theme('colors.gray.300');
  display: table !important;
  max-width: 100%;
  overflow-x: auto;
  table-layout: auto;
}

.prose th,
.prose td {
  border: 1px solid theme('colors.gray.300');
  padding: 0.75rem 1rem;
}

.prose th {
  font-weight: 600;
  background-color: theme('colors.gray.50');
}

.prose tbody tr:nth-child(even) {
  background-color: theme('colors.gray.50');
}

.code-block-container {
  background-color: #f6f8fa;
  border-radius: 8px;
  border: 1px solid #d0d7de;
  margin-top: 1.5em;
  margin-bottom: 1.5em;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  max-width: 100%;
  width: 100%;
}

.code-block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0.875rem;
  background-color: #eef2f5;
  border-bottom: 1px solid #d0d7de;
  min-width: 0;
}

.language-name {
  color: #24292f;
  font-size: 0.8125rem;
  font-family: sans-serif;
  text-transform: capitalize;
}

.copy-code-button {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #24292f;
  background: none;
  border: none;
  padding: 4px;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.copy-code-button:hover {
  background-color: #d0d7de;
}

.copy-code-button svg {
  width: 16px;
  height: 16px;
}

.code-block-container pre {
  margin: 0;
  border-radius: 0;
  border: none;
  background: transparent !important;
  overflow-x: auto;
  overflow-y: hidden;
  max-width: 100%;
  width: 100%;
  box-sizing: border-box;
}

.code-block-container pre code {
  font-size: 0.875rem;
  line-height: 1.5;
  display: block;
  white-space: pre;
  word-wrap: normal;
  overflow-wrap: normal;
  min-width: 100%;
  width: max-content;
}

.prose h1,
.prose h2,
.prose h3,
.prose h4,
.prose h5,
.prose h6 {
  font-size: 1em !important;
  font-weight: 600 !important;
  margin-top: 1.5em;
  margin-bottom: 0.75em;
}

.prose :where(h1, h2, h3, h4, h5, h6):first-child {
  margin-top: 0;
}

.prose :where(p) {
  margin-top: 0.75em;
  margin-bottom: 0.75em;
}

/* ============================================
   引用标记样式 — 方案C：浅蓝背景 + 深蓝字正方形角标
   ============================================ */

/* 引用标记基础样式 */
.ref-marker {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.65em;
  width: 1.4em;
  height: 1.4em;
  padding: 0;
  border-radius: 3px;
  vertical-align: super;
  position: relative;
  top: -0.15em;
  line-height: 1;
  font-weight: 700;
  margin: 0 0.95em;
  transition: all 0.2s ease;
}

.ref-marker.ref-inactive {
  color: #6b7280;
  background-color: #f3f4f6;
  cursor: default;
}

.ref-marker.ref-active {
  color: #1d4ed8;
  background-color: #dbeafe;
  cursor: pointer;
}

.ref-marker.ref-active:hover {
  background-color: #bfdbfe;
  color: #1e40af;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
}

/* 图片引用容器 */
.ref-image-container {
  margin: 1em auto;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.ref-image-container .ref-image {
  max-width: 100%;
  max-height: 400px;
}

.ref-image-container figcaption {
  margin-top: 0.5em;
  font-size: 0.75rem;
  color: #6b7280;
}
</style>

<style scoped>
/* 复制按钮样式 */
.copy-full-response-button {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
  background-color: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 9999px;
  cursor: pointer;
  transition: all 0.2s ease-in-out;
}

.copy-full-response-button:hover {
  background-color: #e5e7eb;
  color: #1f2937;
}

.prose {
  color: #24292f;
}

.prose :where(p) {
  margin-top: 0;
  margin-bottom: 1rem;
}

.prose :where(code):not(:where(pre *)) {
  background-color: rgba(175, 184, 193, 0.2);
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  border-radius: 6px;
}

.prose :where(blockquote) {
  border-left: 0.25em solid #d0d7de;
  padding: 0 1em;
  color: #57606a;
}

.prose :where(blockquote p):last-of-type {
  margin-bottom: 0;
}

/* 分隔线样式优化 */
.prose :where(hr) {
  max-width: 100%;
  margin: 1.5rem 0;
  border: none;
  height: 1px;
  background: #d1d5db;
  opacity: 0.8;
}

/* 确保列表和其他元素也有合适的宽度 */
.prose :where(ul, ol) {
  max-width: 100%;
}

.prose :where(li) {
  margin-top: 0.25em;
  margin-bottom: 0.25em;
}

/* 数学公式样式 */
.prose .katex {
  font-size: 1.1em;
}

.prose .katex-display {
  margin: 1.5em 0;
  text-align: center;
  overflow-x: auto;
  overflow-y: hidden;
}

.prose .katex-display > .katex {
  display: inline-block;
  white-space: nowrap;
  max-width: 100%;
}

/* 行内数学公式 */
.prose .katex-inline {
  margin: 0 0.1em;
}

/* 数学公式在移动端的适配 */
@media (max-width: 768px) {
  .prose .katex-display {
    margin: 1em 0;
    padding: 0 0.5em;
  }
  
  .prose .katex {
    font-size: 1em;
  }
}

/* Markdown 渲染器容器 */
.markdown-renderer-container {
  font-size: 1rem;
  line-height: 1.5;
  color: #24292f;
  max-width: 100%;
  overflow-x: hidden;
  word-wrap: break-word;
  overflow-wrap: break-word;
  width: 100%;
}

.prose {
  max-width: 100% !important;
  width: 100%;
}

.prose > * {
  max-width: 100%;
}

.animate-fade-in {
  animation: fadeIn 0.6s ease-out forwards;
  opacity: 0;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.search-step-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.search-step-card:hover {
  transform: translateY(-1px);
}

.reference-link {
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.reference-link:hover {
  transform: translateY(-0.5px);
}

.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.animate-pulse-gentle {
  animation: pulseGentle 2s ease-in-out infinite;
}

@keyframes pulseGentle {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.6;
  }
}

@media (max-width: 768px) {
  .message-container {
    padding: 0.75rem;
  }

  .max-w-4xl {
    max-width: 100%;
  }

  .space-x-4 > :not([hidden]) ~ :not([hidden]) {
    margin-left: 0.75rem;
  }
}

/* 等待提示样式 */
.waiting-indicator {
  padding: 4px 0;
  font-size: 14px;
  color: #9ca3af;
  transition: opacity 0.15s ease;
}
</style>
