<template>
  <div class="model-selector-container">
    <div class="relative">
      <!-- 模型选择按钮 -->
      <button
        @click="toggleDropdown"
        class="flex items-center space-x-1.5 px-2.5 h-10 rounded-md hover:bg-gray-100 transition-colors duration-150 focus:outline-none"
      >
        <span class="text-sm font-medium text-gray-700">
          {{ selectedModel?.name || '选择模型' }}
        </span>
        <ChevronDownIcon 
          class="w-3.5 h-3.5 text-gray-500 transition-transform duration-200"
          :class="{ 'rotate-180': showDropdown }"
        />
      </button>

      <!-- 下拉菜单 - 带滚动 -->
      <transition
        enter-active-class="transition ease-out duration-100"
        enter-from-class="transform opacity-0 scale-95"
        enter-to-class="transform opacity-100 scale-100"
        leave-active-class="transition ease-in duration-75"
        leave-from-class="transform opacity-100 scale-100"
        leave-to-class="transform opacity-0 scale-95"
      >
        <div
          v-if="showDropdown"
          class="fixed bottom-auto left-auto bg-white rounded-lg shadow-xl border border-gray-200 w-[320px] z-[9999]"
          :style="dropdownStyle"
        >
          <div class="p-1 max-h-[240px] overflow-y-auto custom-scrollbar">
            <!-- 文本模型组 -->
            <div v-if="textModels.length > 0">
              <div class="px-3 py-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                文本模型
              </div>
              <button
                v-for="model in textModels"
                :key="model.name"
                @click="selectModel(model)"
                class="w-full text-left px-3 py-2 rounded-md hover:bg-gray-50 transition-colors duration-150"
              >
                <div class="flex items-center justify-between">
                  <div class="flex-1 min-w-0">
                    <p class="font-medium text-sm text-gray-900">{{ model.name }}</p>
                    <p class="text-xs text-gray-500 mt-0.5 line-clamp-1">
                      {{ model.description || '暂无描述' }}
                    </p>
                  </div>
                  <CheckIcon
                    v-if="selectedModel?.name === model.name"
                    class="w-4 h-4 text-indigo-600 flex-shrink-0 ml-2"
                  />
                </div>
              </button>
            </div>

            <!-- 多模态模型组 -->
            <div v-if="multiModels.length > 0" class="mt-1 pt-1 border-t border-gray-100">
              <div class="px-3 py-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                多模态模型
              </div>
              <button
                v-for="model in multiModels"
                :key="model.name"
                @click="selectModel(model)"
                class="w-full text-left px-3 py-2 rounded-md hover:bg-gray-50 transition-colors duration-150"
              >
                <div class="flex items-center justify-between">
                  <div class="flex-1 min-w-0">
                    <p class="font-medium text-sm text-gray-900">{{ model.name }}</p>
                    <p class="text-xs text-gray-500 mt-0.5 line-clamp-1">
                      {{ model.description || '暂无描述' }}
                    </p>
                  </div>
                  <CheckIcon
                    v-if="selectedModel?.name === model.name"
                    class="w-4 h-4 text-indigo-600 flex-shrink-0 ml-2"
                  />
                </div>
              </button>
            </div>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { ChevronDownIcon, CheckIcon } from '@heroicons/vue/24/outline';

const props = defineProps({
  models: {
    type: Array,
    default: () => []
  },
  selectedModel: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['model-selected']);

const showDropdown = ref(false);
const dropdownStyle = ref({});

// 文本模型列表
const textModels = computed(() => {
  return props.models.filter(model => model.type === 'text-model' || !model.type);
});

// 多模态模型列表
const multiModels = computed(() => {
  return props.models.filter(model => model.type === 'multi-model');
});

// 计算下拉菜单位置 - 右对齐
const updateDropdownPosition = () => {
  const button = document.querySelector('.model-selector-container button');
  if (button) {
    const rect = button.getBoundingClientRect();
    
    // 主菜单右对齐到按钮右侧
    dropdownStyle.value = {
      bottom: `${window.innerHeight - rect.top + 8}px`,
      right: `${window.innerWidth - rect.right}px`
    };
  }
};

const toggleDropdown = () => {
  showDropdown.value = !showDropdown.value;
  if (showDropdown.value) {
    updateDropdownPosition();
  }
};

const selectModel = (model) => {
  emit('model-selected', model);
  showDropdown.value = false;
};

// 点击外部关闭下拉菜单
const handleClickOutside = (event) => {
  const container = document.querySelector('.model-selector-container');
  if (container && !container.contains(event.target)) {
    showDropdown.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.model-selector-container {
  position: relative;
  z-index: 1;
}

/* 自定义滚动条 */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #d4d4d4;
  border-radius: 10px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: #a3a3a3;
}

/* 限制文本为单行 */
.line-clamp-1 {
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
