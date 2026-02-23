<template>
  <div class="min-h-screen bg-gray-50 p-4 sm:p-8">
    <div class="max-w-5xl w-full bg-white shadow-lg rounded-lg p-8 space-y-8 mx-auto">
      <div class="text-center">
        <h1 class="text-3xl font-bold text-gray-800">系统配置向导</h1>
        <p class="text-gray-500 mt-2">请按步骤完成所有模型配置，所有测试通过后才能保存</p>
      </div>

      <!-- 快速设置区域 -->
      <div class="bg-indigo-50 border border-indigo-200 rounded-lg p-6 mb-8">
        <h3 class="text-lg font-medium text-indigo-900 mb-4 flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clip-rule="evenodd" />
          </svg>
          快速设置 (推荐)
        </h3>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">选择服务提供商</label>
            <select v-model="quickSetup.provider" class="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 border">
              <option value="">请选择...</option>
              <option v-for="(preset, key) in PROVIDER_PRESETS" :key="key" :value="key">
                {{ preset.name }}
              </option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">API Key (应用于所有模型)</label>
            <input type="password" v-model="quickSetup.apiKey" placeholder="sk-..." class="block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm p-2 border">
            <p v-if="quickSetup.provider && PROVIDER_PRESETS[quickSetup.provider]?.apiKeyUrl" class="mt-1 text-xs text-gray-500">
              获取 API Key: <a :href="PROVIDER_PRESETS[quickSetup.provider].apiKeyUrl" target="_blank" class="text-indigo-600 hover:text-indigo-800 underline">点击前往官网</a>
            </p>
          </div>
        </div>
        <div class="mt-4 flex justify-end">
          <button 
            @click="applyQuickSetup" 
            :disabled="!quickSetup.provider || !quickSetup.apiKey"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400 disabled:cursor-not-allowed">
            应用配置预设
          </button>
        </div>
        <p class="mt-2 text-xs text-indigo-600">
          * 应用预设将自动填充下方所有步骤的配置，您仍需手动点击每一步的"测试连接"以确认。
        </p>
      </div>

      <!-- 进度指示器 -->
      <div class="flex items-center justify-center space-x-2 mb-8">
        <div v-for="(step, index) in configSteps" :key="index" class="flex items-center">
          <div :class="[
            'w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold',
            step.completed ? 'bg-green-500 text-white' : 'bg-gray-300 text-gray-600'
          ]">
            {{ index + 1 }}
          </div>
          <div v-if="index < configSteps.length - 1" class="w-16 h-1 bg-gray-300 mx-2"></div>
        </div>
      </div>

      <!-- 步骤1: Summary Model -->
      <ConfigSection title="步骤1: 摘要模型配置" description="用于文本摘要、表格理解等任务">
        <ModelConfig 
          v-model="systemConfig.Model_Config.LLM.summary_model"
          :testStatus="testStatus.summary"
          modelType="summary"
          @test="testModel('summary', systemConfig.Model_Config.LLM.summary_model)"
        />
      </ConfigSection>

      <!-- 步骤2: Vision Model -->
      <ConfigSection title="步骤2: 视觉模型配置" description="用于图像理解任务">
        <ModelConfig 
          v-model="systemConfig.Model_Config.LLM.vision_model"
          :testStatus="testStatus.vision"
          modelType="vision"
          @test="testModel('vision', systemConfig.Model_Config.LLM.vision_model)"
        />
      </ConfigSection>

      <!-- 步骤3: Chat Models (支持多个) -->
      <ConfigSection title="步骤3: 对话模型配置" description="用户可选择的对话模型，至少配置一个">
        <div class="space-y-4">
          <div v-for="(chatModel, index) in systemConfig.Model_Config.LLM.chat_model" :key="index" 
               class="border rounded-lg p-4 bg-gray-50">
            <div class="flex justify-between items-center mb-4">
              <h4 class="font-medium text-gray-700">对话模型 {{ index + 1 }}</h4>
              <button v-if="systemConfig.Model_Config.LLM.chat_model.length > 1" 
                      @click="removeChatModel(index)"
                      class="text-red-600 hover:text-red-800 text-sm">
                删除
              </button>
            </div>
            
            <ModelConfig 
              v-model="systemConfig.Model_Config.LLM.chat_model[index]"
              :testStatus="testStatus.chat[index]"
              modelType="chat"
              :showDefault="true"
              :modelIndex="index"
              @test="testModel(`chat_${index}`, systemConfig.Model_Config.LLM.chat_model[index])"
              @set-default="setDefaultChatModel(index)"
            />
          </div>
          
          <button @click="addChatModel" 
                  class="w-full py-2 px-4 border-2 border-dashed border-gray-300 rounded-md text-gray-600 hover:border-indigo-500 hover:text-indigo-600">
            + 添加对话模型
          </button>
        </div>
      </ConfigSection>

      <!-- 步骤4: Embedding Model -->
      <ConfigSection title="步骤4: 嵌入模型配置" description="用于文本向量化和语义搜索">
        <ModelConfig 
          v-model="systemConfig.Model_Config.Embedding.embedding_model"
          :testStatus="testStatus.embedding"
          modelType="embedding"
          @test="testModel('embedding', systemConfig.Model_Config.Embedding.embedding_model)"
        />
      </ConfigSection>

      <!-- 步骤5: Rerank Model (始终必需) -->
      <ConfigSection title="步骤5: 重排序模型配置" description="用于提升检索精度（必需配置）">
        <ModelConfig 
          v-model="systemConfig.Model_Config.Rerank.rerank_model"
          :testStatus="testStatus.rerank"
          modelType="rerank"
          @test="testModel('rerank', systemConfig.Model_Config.Rerank.rerank_model)"
        />
      </ConfigSection>

      <!-- 步骤6: OCR Config -->
      <ConfigSection title="步骤6: OCR 服务配置" description="用于文档解析和图片文字识别 (PaddleOCR)">
        <div class="space-y-4">
          <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <p class="text-sm text-yellow-700">
                  请前往 <a href="https://aistudio.baidu.com/paddleocr" target="_blank" class="font-medium underline hover:text-yellow-800">PaddleOCR 官网</a> 获取 API URL 和 Token。
                </p>
                <p class="text-sm text-yellow-700 mt-1">
                  测试说明：测试将使用项目中的 <code>PDF\attention is all you need.pdf</code> 进行测试。由于需要解析文档，测试过程可能持续 30-60 秒，请耐心等待。
                </p>
              </div>
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">解析器类型</label>
            <select v-model="systemConfig.OCR_Config.parser" 
                    class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm">
              <option value="paddle_ocr">PaddleOCR</option>
            </select>
          </div>

          <div v-if="systemConfig.OCR_Config.parser === 'paddle_ocr'" class="space-y-4 border-l-4 border-indigo-100 pl-4">
            <div>
              <label class="block text-sm font-medium text-gray-700">API URL *</label>
              <input 
                type="text" 
                v-model="systemConfig.OCR_Config.paddle_ocr.api_url"
                placeholder="https://..."
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
            </div>
             <div>
              <label class="block text-sm font-medium text-gray-700">API Token *</label>
              <input 
                type="text" 
                v-model="systemConfig.OCR_Config.paddle_ocr.api_token"
                placeholder="..."
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
            </div>
            <div>
              <label class="block text-sm font-medium text-gray-700">Timeout (秒)</label>
              <input 
                type="number" 
                v-model.number="systemConfig.OCR_Config.paddle_ocr.timeout"
                placeholder="300"
                class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              />
            </div>
            
            <!-- 测试按钮 -->
            <div class="flex items-center space-x-4 pt-2">
              <button 
                @click="testOCR"
                :disabled="testStatus.ocr.testing"
                class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none disabled:bg-indigo-400">
                <span v-if="testStatus.ocr.testing">
                  <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  测试连接中...
                </span>
                <span v-else>测试连接</span>
              </button>
              
              <span v-if="testStatus.ocr.message" 
                    :class="['text-sm', testStatus.ocr.success ? 'text-green-600' : 'text-red-600']">
                {{ testStatus.ocr.message }}
              </span>
            </div>

            <div v-if="testStatus.ocr.testing" class="text-xs text-gray-500 mt-1">
              注意: OCR测试需要上传并解析PDF文件，耗时较长 (可能超过 60 秒)，请耐心等待...
            </div>
          </div>
        </div>
      </ConfigSection>

      <!-- 配置状态总结 -->
      <div class="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
        <h3 class="font-medium text-indigo-900 mb-2">配置状态</h3>
        <div class="grid grid-cols-2 md:grid-cols-3 gap-2 text-sm">
          <div v-for="step in configSteps" :key="step.name" class="flex items-center">
            <span v-if="step.completed" class="text-green-600">✓</span>
            <span v-else class="text-gray-400">○</span>
            <span class="ml-2" :class="step.completed ? 'text-green-700' : 'text-gray-600'">
              {{ step.label }}
            </span>
          </div>
        </div>
      </div>

      <!-- 保存按钮 -->
      <div class="pt-5">
        <button 
          @click="saveConfiguration" 
          :disabled="!allTestsPassed || isSaving"
          class="w-full flex justify-center py-3 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white disabled:bg-gray-400 disabled:cursor-not-allowed"
          :class="allTestsPassed ? 'bg-indigo-600 hover:bg-indigo-700' : 'bg-gray-400'">
          <span v-if="isSaving">正在保存并激活系统...</span>
          <span v-else-if="allTestsPassed">✓ 保存配置并启动系统</span>
          <span v-else>请完成所有测试后保存</span>
        </button>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import api from '../services/api';
import ConfigSection from '../components/ConfigSection.vue';
import ModelConfig from '../components/ModelConfig.vue';

const router = useRouter();
const userId = ref(sessionStorage.getItem('userId') || '');

// --- 快速设置相关 ---
const PROVIDER_PRESETS = {
  dashscope: {
    name: '阿里云 DashScope (推荐)',
    apiKeyUrl: 'https://bailian.console.aliyun.com/cn-beijing/?tab=model#/api-key',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    models: {
      summary: 'qwen-flash',
      vision: 'qwen3-vl-flash',
      chat: [
        { name: 'qwen-plus', type: 'text-model', description: '文本对话模型 (高速)', temperature: 0.5, is_default: true },
        { name: 'qwen-vl-plus', type: 'multi-model', description: '多模态模型 (支持图片)', temperature: 0.5, is_default: false },
        { name: 'qwen3-max', type: 'reason-model', description: '推理/思考模型', temperature: 0.7, is_default: false }
      ],
      embedding: 'text-embedding-v4',
      rerank: 'gte-rerank-v2'
    },
    urls: {
      embedding: 'https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings',
      rerank: 'https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank'
    }
  },
  siliconflow: {
    name: 'SiliconFlow (硅基流动)',
    apiKeyUrl: 'https://cloud.siliconflow.cn/me/account/ak',
    base_url: 'https://api.siliconflow.cn/v1',
    models: {
      summary: 'Qwen/Qwen3-32B',
      vision: 'Qwen/Qwen3-VL-30B-A3B-Instruct',
      chat: [
        { name: 'Qwen/Qwen3-Next-80B-A3B-Instruct', type: 'text-model', description: '文本对话模型', temperature: 0.7, is_default: true },
        { name: 'Qwen/Qwen3-VL-235B-A22B-Instruct', type: 'multi-model', description: '多模态模型', temperature: 0.5, is_default: false },
        { name: 'Qwen/Qwen3-Next-80B-A3B-Thinking', type: 'reason-model', description: '推理模型 (需开启思考模式)', temperature: 0.7, is_default: false }
      ],
      embedding: 'Qwen/Qwen3-Embedding-8B',
      rerank: 'Qwen/Qwen3-Reranker-8B'
    },
    urls: {
      embedding: 'https://api.siliconflow.cn/v1/embeddings',
      rerank: 'https://api.siliconflow.cn/v1/rerank'
    }
  },
  openai: {
    name: 'OpenAI',
    apiKeyUrl: 'https://platform.openai.com/api-keys',
    base_url: 'https://api.openai.com/v1',
    models: {
      summary: 'gpt-4o-mini',
      vision: 'gpt-4o',
      chat: [
        { name: 'gpt-4o', type: 'text-model', description: '文本对话模型', temperature: 0.7, is_default: true },
        { name: 'gpt-4o', type: 'multi-model', description: '多模态模型', temperature: 0.7, is_default: false }
      ],
      embedding: 'text-embedding-3-small',
      rerank: '' // OpenAI 无 Rerank
    },
    urls: {
      embedding: 'https://api.openai.com/v1/embeddings',
      rerank: ''
    }
  },
  deepseek: {
    name: 'DeepSeek',
    apiKeyUrl: 'https://platform.deepseek.com/api_keys',
    base_url: 'https://api.deepseek.com',
    models: {
      summary: 'deepseek-chat',
      vision: '', 
      chat: [
        { name: 'deepseek-chat', type: 'text-model', description: 'DeepSeek V3', temperature: 0.7, is_default: true },
        { name: 'deepseek-reasoner', type: 'reason-model', description: 'DeepSeek R1 (推理)', temperature: 0.7, is_default: false }
      ],
      embedding: '',
      rerank: ''
    },
    urls: {
      embedding: '',
      rerank: ''
    }
  }
};

const quickSetup = reactive({
  provider: '',
  apiKey: ''
});

function applyQuickSetup() {
  const preset = PROVIDER_PRESETS[quickSetup.provider];
  if (!preset) return;

  const key = quickSetup.apiKey;
  const missingConfigs = [];

  // 1. Summary Model
  if (preset.models.summary) {
    systemConfig.Model_Config.LLM.summary_model.name = preset.models.summary;
    systemConfig.Model_Config.LLM.summary_model.base_url = preset.base_url;
    systemConfig.Model_Config.LLM.summary_model.api_key = key;
  } else {
    missingConfigs.push('摘要模型');
  }

  // 2. Vision Model
  if (preset.models.vision) {
    systemConfig.Model_Config.LLM.vision_model.name = preset.models.vision;
    systemConfig.Model_Config.LLM.vision_model.base_url = preset.base_url;
    systemConfig.Model_Config.LLM.vision_model.api_key = key;
  } else {
    missingConfigs.push('视觉模型 (Vision)');
  }

  // 3. Chat Models (支持多个推荐配置)
  if (preset.models.chat && Array.isArray(preset.models.chat)) {
    // 清空现有
    systemConfig.Model_Config.LLM.chat_model = [];
    testStatus.chat = [];

    preset.models.chat.forEach(m => {
      systemConfig.Model_Config.LLM.chat_model.push({
        name: m.name,
        type: m.type,
        base_url: preset.base_url,
        api_key: key,
        temperature: m.temperature,
        description: m.description,
        is_default: m.is_default || false
      });
      testStatus.chat.push({ testing: false, message: '', success: false });
    });
  }

  // 4. Embedding
  if (preset.models.embedding) {
    systemConfig.Model_Config.Embedding.embedding_model.name = preset.models.embedding;
    systemConfig.Model_Config.Embedding.embedding_model.base_url = preset.urls.embedding || preset.base_url;
    systemConfig.Model_Config.Embedding.embedding_model.api_key = key;
  } else {
     missingConfigs.push('Embedding 模型');
  }

  // 5. Rerank
  if (preset.models.rerank) {
    systemConfig.Model_Config.Rerank.rerank_model.name = preset.models.rerank;
    systemConfig.Model_Config.Rerank.rerank_model.base_url = preset.urls.rerank || preset.base_url;
    systemConfig.Model_Config.Rerank.rerank_model.api_key = key;
  } else {
    missingConfigs.push('Rerank 重排序模型');
  }
  
  let msg = `已应用配置预设: ${preset.name}。`;
  if (missingConfigs.length > 0) {
    msg += `\n\n注意：该厂商未提供以下服务，请手动配置其他厂商的模型：\n- ${missingConfigs.join('\n- ')}`;
  }
  msg += `\n\n请务必检查各项配置，并逐一点击"测试"按钮。`;
  
  alert(msg);
}

// --- End of 快速设置 ---

// 系统配置结构
const systemConfig = reactive({
  Basic_Config: {
    IS_ACTIVE: false
  },
  OCR_Config: {
    parser: 'paddle_ocr',
    paddle_ocr: {
      api_url: '',
      api_token: '',
      timeout: 300
    }
  },
  Model_Config: {
    LLM: {
      summary_model: {
        name: '',
        base_url: '',
        api_key: '',
        temperature: 0.4,
        description: '用于文本摘要、表格理解任务'
      },
      vision_model: {
        name: '',
        base_url: '',
        api_key: '',
        temperature: 0.3,
        description: '用于PDF中图像理解任务'
      },
      chat_model: [
        {
          name: '',
          type: 'text-model',  // 默认为文本模型
          base_url: '',
          api_key: '',
          temperature: 0.5,
          description: '标准对话问答模型',
          is_default: true
        }
      ]
    },
    Embedding: {
      embedding_model: {
        name: '',
        base_url: '',
        api_key: '',
        description: '用于文本向量化'
      }
    },
    Rerank: {
      rerank_model: {
        name: '',
        base_url: '',
        api_key: '',
        description: '用于检索结果重排序'
      }
    }
  }
});

// 测试状态
const testStatus = reactive({
  summary: { testing: false, message: '', success: false },
  vision: { testing: false, message: '', success: false },
  chat: [{ testing: false, message: '', success: false }],
  embedding: { testing: false, message: '', success: false },
  rerank: { testing: false, message: '', success: false },
  ocr: { testing: false, message: '', success: false }
});

const isSaving = ref(false);

// 配置步骤
const configSteps = computed(() => {
  const steps = [
    { name: 'summary', label: '摘要模型', completed: testStatus.summary.success },
    { name: 'vision', label: '视觉模型', completed: testStatus.vision.success },
    { name: 'chat', label: '对话模型', completed: testStatus.chat.every(s => s.success) },
    { name: 'embedding', label: '嵌入模型', completed: testStatus.embedding.success },
    { name: 'rerank', label: '重排序模型', completed: testStatus.rerank.success },
    { name: 'ocr', label: 'OCR服务', completed: testStatus.ocr.success }
  ];
  
  return steps;
});

// 所有测试是否通过
const allTestsPassed = computed(() => {
  // 必须所有配置步骤都完成
  const allStepsCompleted = configSteps.value.every(step => step.completed);
  
  // 必须所有对话模型都测试通过
  const allChatModelsTestd = testStatus.chat.length > 0 && testStatus.chat.every(s => s.success);
  
  return allStepsCompleted && allChatModelsTestd;
});

// 移除监听召回版本变化的逻辑，因为 rerank 始终必需

// 添加对话模型
function addChatModel() {
  systemConfig.Model_Config.LLM.chat_model.push({
    name: '',
    type: 'text-model',  // 默认为文本模型
    base_url: '',
    api_key: '',
    temperature: 0.5,
    description: '',
    is_default: false
  });
  // 同步添加测试状态
  testStatus.chat.push({ testing: false, message: '', success: false });
}

// 删除对话模型
function removeChatModel(index) {
  if (systemConfig.Model_Config.LLM.chat_model.length > 1) {
    systemConfig.Model_Config.LLM.chat_model.splice(index, 1);
    testStatus.chat.splice(index, 1);
  }
}

// 设置默认对话模型（单选逻辑）
function setDefaultChatModel(index) {
  // 取消所有模型的默认状态
  systemConfig.Model_Config.LLM.chat_model.forEach((model, i) => {
    model.is_default = (i === index);
  });
}

// 测试模型连接
async function testModel(type, modelConfig) {
  const statusKey = type.startsWith('chat_') ? 'chat' : type;
  const statusIndex = type.startsWith('chat_') ? parseInt(type.split('_')[1]) : null;
  const status = statusIndex !== null ? testStatus[statusKey][statusIndex] : testStatus[statusKey];
  
  status.testing = true;
  status.message = '';
  
  try {
    const payload = {
      model_name: modelConfig.name,
      base_url: modelConfig.base_url,
      api_key: modelConfig.api_key,
      model_type: statusKey
    };
    
    // 如果是聊天模型，添加 chat_model_type (text-model 或 multi-model)
    if (statusKey === 'chat') {
      payload.chat_model_type = modelConfig.type || 'text-model';
    }
    
    const response = await api.post('/api/test/model', payload);
    
    status.success = response.data.success;
    status.message = response.data.message;
  } catch (error) {
    status.success = false;
    status.message = error.response?.data?.message || '连接测试失败';
  } finally {
    status.testing = false;
  }
}

// 测试 OCR 连接
async function testOCR() {
  testStatus.ocr.testing = true;
  testStatus.ocr.message = '';
  
  try {
    const payload = {
      model_type: 'ocr',
      ...systemConfig.OCR_Config.paddle_ocr
    };
    
    // api/test/model 端点现在需要支持 model_type='ocr'
    const response = await api.post('/api/test/model', payload);
    
    testStatus.ocr.success = response.data.success;
    testStatus.ocr.message = response.data.message;
  } catch (error) {
    testStatus.ocr.success = false;
    testStatus.ocr.message = error.response?.data?.message || '连接测试失败';
  } finally {
    testStatus.ocr.testing = false;
  }
}

// 保存配置
async function saveConfiguration() {
  if (!allTestsPassed.value) {
    alert('请完成所有模型测试后再保存！');
    return;
  }
  
  isSaving.value = true;
  try {
    await api.post('/api/settings', {
      config: systemConfig,
      activate: true  // 请求激活系统
    });
    
    alert('配置已成功保存并激活！即将进入对话界面。');
    router.push({ name: 'Chat', query: { fromConfigSave: 'true' } });
  } catch (error) {
    alert('保存失败: ' + (error.response?.data?.detail || '未知错误'));
  } finally {
    isSaving.value = false;
  }
}

// 加载现有配置
onMounted(async () => {
  if (!userId.value) {
    router.push('/login');
    return;
  }
  
  try {
    const response = await api.get('/api/settings');
    if (response.data && Object.keys(response.data).length > 0) {
      Object.assign(systemConfig, response.data);
      
      // 同步 testStatus.chat 数组长度
      const chatModelCount = systemConfig.Model_Config?.LLM?.chat_model?.length || 1;
      testStatus.chat = Array.from({ length: chatModelCount }, () => ({ 
        testing: false, 
        message: '', 
        success: false 
      }));
    }
  } catch (error) {
    console.error("Failed to load settings:", error);
  }
});
</script>

<style scoped>
/* 添加必要的自定义样式 */
</style>
