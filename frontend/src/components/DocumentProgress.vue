<template>
  <div class="document-progress">
    <!-- 进度条容器 -->
    <div class="relative">
      <!-- 背景进度条 -->
      <div class="h-2 bg-gray-200 rounded-full overflow-hidden">
        <!-- 实际进度 -->
        <div
          class="h-full transition-all duration-500 ease-out rounded-full"
          :class="progressBarColor"
          :style="{ width: `${progress}%` }"
        >
          <!-- 动画效果（处理中时显示） -->
          <div
            v-if="isProcessing"
            class="h-full w-full animate-pulse bg-white/30"
          ></div>
        </div>
      </div>

      <!-- 进度百分比（可选显示） -->
      <div
        v-if="showPercentage"
        class="absolute -top-6 right-0 text-xs font-semibold"
        :class="progressTextColor"
      >
        {{ progress }}%
      </div>
    </div>

    <!-- 当前步骤说明 -->
    <div class="flex items-center justify-between mt-2">
      <div class="flex items-center space-x-2">
        <!-- 状态图标 -->
        <div class="flex-shrink-0">
          <!-- 处理中 -->
          <svg
            v-if="isProcessing"
            class="w-4 h-4 text-blue-500 animate-spin"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          
          <!-- 完成 -->
          <svg
            v-else-if="status === 'COMPLETED'"
            class="w-4 h-4 text-green-500"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
          </svg>
          
          <!-- 失败 -->
          <svg
            v-else-if="status === 'FAILED'"
            class="w-4 h-4 text-red-500"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
          </svg>
          
          <!-- 上传中 -->
          <svg
            v-else
            class="w-4 h-4 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"/>
          </svg>
        </div>

        <!-- 步骤文字 -->
        <span class="text-sm font-medium" :class="stepTextColor">
          {{ currentStep }}
        </span>
      </div>

      <!-- 错误信息（失败时显示） -->
      <div v-if="status === 'FAILED' && errorMessage" class="flex items-center space-x-1">
        <button
          @click="showError = !showError"
          class="text-xs text-red-600 hover:text-red-700 underline"
        >
          {{ showError ? '隐藏' : '查看' }}错误
        </button>
      </div>
    </div>

    <!-- 错误详情（展开时显示） -->
    <div
      v-if="showError && errorMessage"
      class="mt-2 p-3 bg-red-50 border border-red-200 rounded-lg"
    >
      <p class="text-xs text-red-700">{{ errorMessage }}</p>
    </div>

    <!-- 详细步骤指示器（可选） -->
    <div v-if="showSteps" class="mt-4 space-y-2">
      <div
        v-for="(step, index) in steps"
        :key="index"
        class="flex items-center space-x-3"
      >
        <!-- 步骤图标 -->
        <div class="flex-shrink-0">
          <div
            v-if="currentStepIndex > index"
            class="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center"
          >
            <svg class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
          </div>
          <div
            v-else-if="currentStepIndex === index"
            class="w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center animate-pulse"
          >
            <div class="w-2 h-2 bg-white rounded-full"></div>
          </div>
          <div
            v-else
            class="w-5 h-5 bg-gray-300 rounded-full"
          ></div>
        </div>

        <!-- 步骤名称 -->
        <span
          class="text-sm"
          :class="currentStepIndex >= index ? 'text-gray-700 font-medium' : 'text-gray-400'"
        >
          {{ step.name }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { STATUS_PROGRESS_MAP } from '../api/knowledgeBase';

const props = defineProps({
  // 文档状态
  status: {
    type: String,
    required: true,
    validator: (value) => ['QUEUED', 'PARSING', 'CHUNKING', 'ENRICHING', 'VECTORIZING', 'COMPLETED', 'FAILED'].includes(value)
  },
  // 进度百分比（0-100）
  progress: {
    type: Number,
    default: 0
  },
  // 当前步骤描述
  currentStep: {
    type: String,
    default: ''
  },
  // 错误信息
  errorMessage: {
    type: String,
    default: ''
  },
  // 是否显示百分比
  showPercentage: {
    type: Boolean,
    default: true
  },
  // 是否显示详细步骤
  showSteps: {
    type: Boolean,
    default: false
  }
});

const showError = ref(false);

// 处理步骤定义
const steps = [
  { name: '排队中', status: 'QUEUED' },
  { name: '解析中', status: 'PARSING' },
  { name: '分段中', status: 'CHUNKING' },
  { name: '内容增强', status: 'ENRICHING' },
  { name: '向量化', status: 'VECTORIZING' },
  { name: '完成', status: 'COMPLETED' }
];

// 当前步骤索引
const currentStepIndex = computed(() => {
  return steps.findIndex(step => step.status === props.status);
});

// 是否正在处理中
const isProcessing = computed(() => {
  return ['QUEUED', 'PARSING', 'CHUNKING', 'ENRICHING', 'VECTORIZING'].includes(props.status);
});

// 进度条颜色
const progressBarColor = computed(() => {
  if (props.status === 'FAILED') return 'bg-red-500';
  if (props.status === 'COMPLETED') return 'bg-green-500';
  return 'bg-blue-500';
});

// 进度文字颜色
const progressTextColor = computed(() => {
  if (props.status === 'FAILED') return 'text-red-600';
  if (props.status === 'COMPLETED') return 'text-green-600';
  return 'text-blue-600';
});

// 步骤文字颜色
const stepTextColor = computed(() => {
  if (props.status === 'FAILED') return 'text-red-600';
  if (props.status === 'COMPLETED') return 'text-green-600';
  if (isProcessing.value) return 'text-blue-600';
  return 'text-gray-600';
});

// 监听状态变化，自动隐藏错误信息
watch(() => props.status, () => {
  if (props.status !== 'FAILED') {
    showError.value = false;
  }
});
</script>

<style scoped>
/* 动画效果 */
@keyframes shimmer {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(100%);
  }
}

.animate-shimmer {
  animation: shimmer 2s infinite;
}
</style>

