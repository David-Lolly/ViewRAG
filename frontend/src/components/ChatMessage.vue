<template>
  <div ref="messageEl" class="message-container py-3 px-6 group"
       :class="{ 
         'bg-background-secondary border-t border-b border-gray-100': isUser,
         'opacity-40': isMarkedForDeletion
       }">
    <div class="max-w-4xl mx-auto flex items-start space-x-4">
      <!-- 头像 -->
      <div class="flex-shrink-0">
        <div class="w-8 h-8 rounded-full flex items-center justify-center text-white font-semibold shadow-md transition-all duration-200 hover:scale-105"
             :class="isUser ? 'bg-gradient-to-br from-blue-500 to-blue-600' : 'bg-red-500'">
          <span v-if="isUser" class="text-xs">{{ userInitial }}</span>
          <span v-else>T</span>
        </div>
      </div>

      
      <div class="flex-grow pt-0 relative">
        <!-- 用户消息：悬浮操作按钮 -->
        <div v-if="isUser && !isEditing && !isMarkedForDeletion" 
             class="absolute -top-1 right-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center space-x-1 z-10">
          <!-- 重新生成按钮 -->
          <button
            @click="$emit('regenerate', message)"
            class="p-1.5 bg-white hover:bg-gray-100 rounded-lg shadow-sm border border-gray-200 transition-all duration-200 hover:scale-105"
            title="重新生成"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
          <!-- 编辑按钮 -->
          <button
            @click="startEditing"
            class="p-1.5 bg-white hover:bg-gray-100 rounded-lg shadow-sm border border-gray-200 transition-all duration-200 hover:scale-105"
            title="编辑消息"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
          </button>
        </div>


        
        <!-- 用户消息：正常显示模式 -->
        <div v-if="isUser && !isEditing" class="space-y-2">
          <!-- 图片显示在用户消息上方 -->
          <div v-if="message.image_url && (Array.isArray(message.image_url) ? message.image_url.length > 0 : true)" class="mb-2">
            <img 
              :src="message.image_url" 
              alt="用户上传的图片" 
              class="max-w-[300px] max-h-[300px] rounded-lg border border-gray-200 shadow-sm cursor-pointer hover:shadow-md transition-shadow duration-200"
              @click="previewImage(message.image_url)"
            />
          </div>
          <!-- 文本消息 -->
          <div class="text-text-primary leading-relaxed pt-1" style="font-size: 1rem;">
            <p>{{ message.content }}</p>
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
              <img :src="img" alt="图片" class="w-20 h-20 object-cover rounded-lg border border-gray-200" />
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
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span>取消</span>
            </button>
            <button
              @click="submitEdit"
              :disabled="!editedContent.trim()"
              class="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed text-white rounded-lg text-sm font-medium transition-all duration-200 flex items-center space-x-1"
            >
              <span>发送</span>
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </button>
          </div>
        </div>

        
        <!-- AI消息 -->
        <div v-if="!isUser" class="space-y-4">
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

          
          <div v-if="searchSteps.length > 0 && !message.content.trim()" class="space-y-2">
            
            <div
              v-for="(step, index) in searchSteps"
              :key="index"
              class="search-step-card group flex items-center space-x-3 p-3 bg-white rounded-lg border border-gray-100 shadow-sm hover:shadow-md transition-all duration-300 animate-fade-in"
              :style="{ animationDelay: `${index * 150}ms` }">
               <div class="flex-shrink-0 w-6 h-6 rounded-full bg-gradient-to-br from-blue-50 to-blue-100 flex items-center justify-center group-hover:from-blue-100 group-hover:to-blue-200 transition-all duration-300">
                <span class="text-sm">{{ step.icon }}</span>
              </div>
              <div class="flex-1 min-w-0 flex justify-between items-center">
                <p class="text-text-primary text-xs font-medium">{{ step.text }}</p>
                <p class="text-text-secondary text-xs">{{ step.timestamp }}</p>
              </div>
              <div class="flex-shrink-0">
                <div class="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse-gentle"></div>
              </div>
            </div>
            <div v-if="isStreaming" class="flex items-center mt-2">
              <div class="flex items-center space-x-2 px-2 py-1 bg-blue-50 rounded-full">
                <div class="w-1.5 h-1.5 bg-blue-500 rounded-full animate-pulse"></div>
                <span class="text-blue-600 text-xs font-medium">AI正在思考中...</span>
              </div>
            </div>
          </div>

          
          <div v-if="message.content.trim()" class="space-y-4">
            
            <div class="markdown-renderer-container prose" v-html="formattedContent"></div>

            
            <div v-if="message.content.trim() && !isStreaming" class="flex items-center justify-start -mt-2">
                <button @click="copyFullResponse" class="copy-full-response-button">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    <span>{{ copyButtonText }}</span>
                </button>
            </div>


            
            <div v-if="flattenedReferences.length > 0" class="reference-section mt-4 p-3 bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg border border-gray-200 shadow-sm">
              
               <div class="flex items-center mb-2">
                <div class="w-5 h-5 bg-blue-500 rounded-md flex items-center justify-center mr-2">
                  <svg class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"></path>
                  </svg>
                </div>
                <h4 class="font-semibold text-text-primary text-sm">参考资料</h4>
                <span class="ml-2 px-1.5 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full font-medium">{{ flattenedReferences.length }}</span>
              </div>
               <div class="grid gap-2">
                <a v-for="(item, index) in flattenedReferences" :key="index" :href="item.url" target="_blank" rel="noopener noreferrer" class="reference-link group flex items-start space-x-2 p-2 bg-white rounded-md border border-gray-200 hover:border-blue-300 hover:shadow-sm transition-all duration-200">
                  <div class="flex-shrink-0 w-4 h-4 bg-blue-50 rounded-full flex items-center justify-center group-hover:bg-blue-100 transition-colors duration-200 mt-0.5">
                    <svg class="w-2 h-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-text-primary text-xs font-medium leading-relaxed group-hover:text-blue-700 transition-colors duration-200 line-clamp-1">{{ item.title }}</p>
                  </div>
                   <div class="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                    <svg class="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
                  </div>
                </a>
              </div>
            </div>
          </div>

          
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUpdated } from 'vue';
import { marked } from 'marked';
import hljs from 'highlight.js';
import 'highlight.js/styles/atom-one-light.css';
import katex from 'katex';
import 'katex/dist/katex.min.css';

const props = defineProps({
  message: { type: Object, required: true },
  userId: { type: String, required: true },
  isStreaming: { type: Boolean, default: false },
  searchSteps: { type: Array, default: () => [] },
  isMarkedForDeletion: { type: Boolean, default: false },
  hasError: { type: Boolean, default: false },
  errorMessage: { type: String, default: '' },
});

const emit = defineEmits(['regenerate', 'edit', 'retry']);

const messageEl = ref(null);
const editTextarea = ref(null);
const copyButtonText = ref('复制');
const isEditing = ref(false);
const editedContent = ref('');
const editedImages = ref([]);

const isUser = computed(() => props.message.role === 'user');
const userInitial = computed(() => props.userId ? props.userId.charAt(0).toUpperCase() : 'Y');

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
  
  console.log('[Math] 提取的公式数量:', mathPlaceholders.length);
  console.log('[Math] 占位符列表:', mathPlaceholders.map(item => item.placeholder));
  
  // 处理markdown
  let htmlContent = marked(processedText);
  
  console.log('[Math] Markdown处理后，查找占位符...');
  
  // 最后将占位符替换为渲染好的数学公式（使用非全局替换，确保每个占位符只被替换一次）
  mathPlaceholders.forEach((item, index) => {
    // 使用字符串替换而不是正则表达式，避免特殊字符问题
    // 只替换第一次出现的占位符
    const foundIndex = htmlContent.indexOf(item.placeholder);
    if (foundIndex !== -1) {
      console.log(`[Math] 替换占位符 ${index}: ${item.placeholder.substring(0, 30)}... 在位置 ${foundIndex}`);
      htmlContent = htmlContent.substring(0, foundIndex) + item.html + htmlContent.substring(foundIndex + item.placeholder.length);
    } else {
      console.warn(`[Math] 未找到占位符 ${index}: ${item.placeholder}`);
      console.warn('[Math] HTML内容片段:', htmlContent.substring(0, 200));
    }
  });
  
  return htmlContent;
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

// References 处理
const flattenedReferences = computed(() => {
    if (!props.message.references) return [];
    const references = [];
    for (const item of props.message.references) {
        if (typeof item === 'object' && item !== null) {
            for (const [title, url] of Object.entries(item)) {
                references.push({ title, url });
            }
        }
    }
    return references;
});

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
</style>
