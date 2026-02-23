<template>
  <div class="space-y-4">
    <div>
      <label class="block text-sm font-medium text-gray-700">模型名称 *</label>
      <input 
        type="text" 
        v-model="localModel.name"
        @input="updateModel"
        placeholder="e.g., qwen-turbo, qwen-vl-plus"
        class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
      />
    </div>

    <!-- 模型类型选择 (仅聊天模型显示) -->
    <div v-if="modelType === 'chat'">
      <label class="block text-sm font-medium text-gray-700">模型类型 *</label>
      <div class="mt-2 space-y-2">
        <div class="flex items-center">
          <input 
            type="radio" 
            id="type-text"
            value="text-model"
            v-model="localModel.type"
            @change="updateModel"
            class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
          />
          <label for="type-text" class="ml-2 block text-sm text-gray-900">
            文本生成模型 (Text-only)
          </label>
        </div>
        <div class="flex items-center">
          <input 
            type="radio" 
            id="type-multi"
            value="multi-model"
            v-model="localModel.type"
            @change="updateModel"
            class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
          />
          <label for="type-multi" class="ml-2 block text-sm text-gray-900">
            多模态模型 (Text + Image)
          </label>
        </div>
        <div class="flex items-center">
          <input 
            type="radio" 
            id="type-reason"
            value="reason-model"
            v-model="localModel.type"
            @change="updateModel"
            class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
          />
          <label for="type-reason" class="ml-2 block text-sm text-gray-900">
            推理模型 (Reasoning)
          </label>
        </div>
      </div>
      <p class="mt-1 text-xs text-gray-500">
        多模态模型支持图片输入，测试时将使用图片进行验证；推理模型支持思维链 (CoT)。
      </p>
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700">API Base URL *</label>
      <input 
        type="text" 
        v-model="localModel.base_url"
        @input="updateModel"
        placeholder="e.g., https://dashscope.aliyuncs.com/compatible-mode/v1"
        class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
      />
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700">API Key *</label>
      <div class="relative">
        <input 
          :type="showPassword ? 'text' : 'password'" 
          v-model="localModel.api_key"
          @input="updateModel"
          placeholder="sk-..."
          class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 pr-10 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
        />
        <button 
          type="button"
          @click="showPassword = !showPassword"
          class="absolute inset-y-0 right-0 pr-3 flex items-center text-sm leading-5">
          <svg v-if="!showPassword" class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          <svg v-else class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
          </svg>
        </button>
      </div>
    </div>

    <div v-if="modelType !== 'embedding' && modelType !== 'rerank'">
      <label class="block text-sm font-medium text-gray-700">Temperature</label>
      <input 
        type="number" 
        step="0.1" 
        min="0" 
        max="2"
        v-model.number="localModel.temperature"
        @input="updateModel"
        class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
      />
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700">描述（可选）</label>
      <textarea 
        v-model="localModel.description"
        @input="updateModel"
        rows="2"
        placeholder="描述该模型的用途和特点"
        class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
      ></textarea>
    </div>

    <div v-if="showDefault" class="flex items-center">
      <input 
        type="radio" 
        :checked="localModel.is_default"
        @change="handleDefaultChange"
        :name="`default-model-${modelType}`"
        class="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
      />
      <label class="ml-2 block text-sm text-gray-900">设为默认模型</label>
    </div>

    <!-- 测试按钮和状态 -->
    <div class="pt-4">
      <button 
        @click="$emit('test')"
        :disabled="!canTest || testStatus.testing"
        class="w-full flex justify-center items-center py-2 px-4 border rounded-md shadow-sm text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2"
        :class="testButtonClass">
        <svg v-if="testStatus.testing" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>{{ testButtonText }}</span>
      </button>
      
      <div v-if="testStatus.message" 
           :class="['mt-2 text-sm p-2 rounded', testStatus.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700']">
        {{ testStatus.message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  },
  testStatus: {
    type: Object,
    default: () => ({ testing: false, message: '', success: false })
  },
  modelType: {
    type: String,
    required: true
  },
  showDefault: {
    type: Boolean,
    default: false
  },
  modelIndex: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits(['update:modelValue', 'test', 'set-default']);

const localModel = ref({ ...props.modelValue });
const showPassword = ref(false);

// 确保聊天模型有默认的type字段
if (props.modelType === 'chat' && !localModel.value.type) {
  localModel.value.type = 'text-model';
}

// 监听外部值变化
watch(() => props.modelValue, (newVal) => {
  localModel.value = { ...newVal };
  // 确保聊天模型有type字段
  if (props.modelType === 'chat' && !localModel.value.type) {
    localModel.value.type = 'text-model';
  }
}, { deep: true });

// 更新父组件
function updateModel() {
  emit('update:modelValue', { ...localModel.value });
}

// 处理默认模型选择
function handleDefaultChange() {
  emit('set-default');
}

// 是否可以测试
const canTest = computed(() => {
  return localModel.value.name && localModel.value.base_url && localModel.value.api_key;
});

// 测试按钮样式
const testButtonClass = computed(() => {
  if (!canTest.value || props.testStatus.testing) {
    return 'bg-gray-300 text-gray-500 cursor-not-allowed';
  }
  if (props.testStatus.success) {
    return 'bg-green-600 text-white hover:bg-green-700 focus:ring-green-500';
  }
  return 'bg-indigo-600 text-white hover:bg-indigo-700 focus:ring-indigo-500';
});

// 测试按钮文本
const testButtonText = computed(() => {
  if (props.testStatus.testing) return '测试中...';
  if (props.testStatus.success) return '✓ 测试通过';
  if (props.testStatus.message && !props.testStatus.success) return '✗ 重新测试';
  return '测试连接';
});
</script>
