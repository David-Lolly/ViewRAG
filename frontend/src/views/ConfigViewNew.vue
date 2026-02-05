<template>
  <div class="min-h-screen bg-gray-50 p-4 sm:p-8">
    <div class="max-w-5xl w-full bg-white shadow-lg rounded-lg p-8 space-y-8 mx-auto">
      <div class="text-center">
        <h1 class="text-3xl font-bold text-gray-800">系统配置向导</h1>
        <p class="text-gray-500 mt-2">请按步骤完成所有模型配置，所有测试通过后才能保存</p>
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

      <!-- 步骤1: 基础配置 -->
      <ConfigSection title="步骤1: 基础配置" description="选择召回版本和质量">
        <div class="mt-4 space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">召回版本</label>
            <div class="space-y-2">
              <div class="flex items-center">
                <input id="retrieval_v2" name="retrieval_version" type="radio" value="v2" 
                       v-model="systemConfig.Basic_Config.RETRIEVAL_VERSION" 
                       class="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300">
                <label for="retrieval_v2" class="ml-3 block text-sm font-medium text-gray-700">
                  V2 模式 (推荐) - 更智能的检索策略
                </label>
              </div>
              <div class="flex items-center">
                <input id="retrieval_v1" name="retrieval_version" type="radio" value="v1" 
                       v-model="systemConfig.Basic_Config.RETRIEVAL_VERSION" 
                       class="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300">
                <label for="retrieval_v1" class="ml-3 block text-sm font-medium text-gray-700">
                  V1 模式 (高级) - 需要配置 Rerank 模型
                </label>
              </div>
            </div>
          </div>

          <div class="mt-4">
            <label for="retrieval_quality" class="block text-sm font-medium text-gray-700">召回质量</label>
            <select id="retrieval_quality" v-model="systemConfig.Basic_Config.RETRIEVAL_QUALITY" 
                    class="mt-1 block w-full bg-white border border-gray-300 rounded-md py-2 px-4 text-sm shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500">
              <option value="high">High - 高质量</option>
              <option value="medium">Medium - 中等质量</option>
              <option value="low">Low - 快速响应</option>
            </select>
          </div>
        </div>
      </ConfigSection>

      <!-- 步骤2: Summary Model -->
      <ConfigSection title="步骤2: 摘要模型配置" description="用于文本摘要、表格理解等任务">
        <ModelConfig 
          v-model="systemConfig.Model_Config.LLM.summary_model"
          :testStatus="testStatus.summary"
          modelType="summary"
          @test="testModel('summary', systemConfig.Model_Config.LLM.summary_model)"
        />
      </ConfigSection>

      <!-- 步骤3: Vision Model -->
      <ConfigSection title="步骤3: 视觉模型配置" description="用于图像理解任务">
        <ModelConfig 
          v-model="systemConfig.Model_Config.LLM.vision_model"
          :testStatus="testStatus.vision"
          modelType="vision"
          @test="testModel('vision', systemConfig.Model_Config.LLM.vision_model)"
        />
      </ConfigSection>

      <!-- 步骤4: Chat Models (支持多个) -->
      <ConfigSection title="步骤4: 对话模型配置" description="用户可选择的对话模型，至少配置一个">
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

      <!-- 步骤5: Embedding Model -->
      <ConfigSection title="步骤5: 嵌入模型配置" description="用于文本向量化和语义搜索">
        <ModelConfig 
          v-model="systemConfig.Model_Config.Embedding.embedding_model"
          :testStatus="testStatus.embedding"
          modelType="embedding"
          @test="testModel('embedding', systemConfig.Model_Config.Embedding.embedding_model)"
        />
      </ConfigSection>

      <!-- 步骤6: Rerank Model (始终必需) -->
      <ConfigSection title="步骤6: 重排序模型配置" description="用于提升检索精度（必需配置）">
        <ModelConfig 
          v-model="systemConfig.Model_Config.Rerank.rerank_model"
          :testStatus="testStatus.rerank"
          modelType="rerank"
          @test="testModel('rerank', systemConfig.Model_Config.Rerank.rerank_model)"
        />
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

// 系统配置结构
const systemConfig = reactive({
  Basic_Config: {
    RETRIEVAL_VERSION: 'v2',
    RETRIEVAL_QUALITY: 'high',
    IS_ACTIVE: false
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
        description: '用于图像理解任务'
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
  rerank: { testing: false, message: '', success: false }
});

const isSaving = ref(false);

// 配置步骤
const configSteps = computed(() => {
  const steps = [
    { name: 'basic', label: '基础配置', completed: true },
    { name: 'summary', label: '摘要模型', completed: testStatus.summary.success },
    { name: 'vision', label: '视觉模型', completed: testStatus.vision.success },
    { name: 'chat', label: '对话模型', completed: testStatus.chat.every(s => s.success) },
    { name: 'embedding', label: '嵌入模型', completed: testStatus.embedding.success },
    { name: 'rerank', label: '重排序模型', completed: testStatus.rerank.success }  // 始终必需
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
