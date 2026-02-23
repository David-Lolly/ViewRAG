<template>
  <div class="thinking-block-container my-2">
    <!-- 标题行：点击切换折叠 -->
    <div 
      class="flex items-center space-x-1 cursor-pointer select-none group/thinking w-fit py-1.5 rounded-lg transition-colors duration-200 hover:bg-gray-50/50"
      @click="toggle"
    >
      <div 
        class="w-5 h-5 flex items-center justify-center text-gray-400 group-hover/thinking:text-black transition-colors duration-200"
        :aria-label="localCollapsed ? '展开思考过程' : '收起思考过程'"
      >
        <!-- 折叠：向下箭头 -->
        <svg v-if="localCollapsed" xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
        <!-- 展开：向上箭头 -->
        <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="6 15 12 9 18 15"></polyline>
        </svg>
      </div>
      <span class="text-sm text-gray-500 font-medium group-hover/thinking:text-black transition-colors duration-200">
        {{ headerText }}
      </span>
    </div>

    <!-- 内容区域 -->
    <div 
      v-show="!localCollapsed"
      class="pl-2 ml-2.5 border-l-2 border-gray-100 transition-all duration-300 ease-in-out"
    >
      <div class="text-sm text-gray-500 leading-relaxed whitespace-pre-wrap py-2 pr-4 font-mono">
        {{ content }}<span v-if="isThinking && !content.endsWith('█')" class="inline-block w-2 h-4 align-text-bottom bg-gray-400 ml-1 animate-pulse"></span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue';

const props = defineProps({
  content: {
    type: String,
    default: ''
  },
  isThinking: {
    type: Boolean,
    default: false
  },
  isCollapsed: {
    type: Boolean,
    default: true
  },
  duration: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits(['toggle', 'update:isCollapsed']);

const localCollapsed = ref(props.isCollapsed);

// 标题文本计算
const headerText = computed(() => {
    if (props.isThinking) {
        return '思考中...';
    }
    const baseText = '思考过程';
    if (props.duration > 0) {
        return `${baseText} (用时 ${props.duration.toFixed(1)} 秒)`;
    }
    return baseText;
});

// 监听 props 变化同步到 local
watch(() => props.isCollapsed, (val) => {
  localCollapsed.value = val;
});

const toggle = () => {
    localCollapsed.value = !localCollapsed.value;
    emit('toggle', localCollapsed.value);
    emit('update:isCollapsed', localCollapsed.value);
};
</script>

<style scoped>
/* 使用 Tailwind 类名，这里仅作备份或者是特殊覆盖 */
.thinking-block-container {
    /* 确保容器不会溢出 */
    max-width: 100%;
}
</style>
