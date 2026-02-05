import axios from 'axios';

const API_BASE_URL = '/backend';
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2分钟超时
});



// 响应拦截器
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.data);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.status, error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// --- Custom Methods ---

// 获取用户会话列表
api.getSessions = (userId) => {
  return api.get('/sessions', {
    params: { user_id: userId }
  });
};

// 获取指定会话的消息列表
api.getMessages = (sessionId) => {
  return api.get(`/sessions/${sessionId}/messages`);
};

// 创建新会话
api.createSession = (userId, title) => {
  return api.post('/session', {
    user_id: userId,
    title: title
  });
};

// 用户注册
api.register = (userId, password) => {
  return api.post('/register', {
    user_id: userId,
    password: password
  });
};

// 用户登录
api.login = (userId, password) => {
  return api.post('/login', {
    user_id: userId,
    password: password
  });
};

// 获取可用的对话模型列表
api.getChatModels = () => {
  return api.get('/api/settings/chat-models');
};

// 发送包含文本和图片的消息
api.sendMessageWithImages = async (formData) => {
  // Note: We use fetch directly for FormData to avoid issues with Axios content-type headers
  const response = await fetch(`${API_BASE_URL}/v1/chat/send_message_with_images`, {
    method: 'POST',
    body: formData,
    // Headers are not set, browser will automatically set 'Content-Type' to 'multipart/form-data' with the correct boundary
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Server returned an error' }));
    throw new Error(`Message send failed: ${errorData.detail || response.statusText}`);
  }

  return response.json();
};

// 流式搜索 - 根据use_web参数选择不同的接口
api.searchStream = async (payload, onChunk, onComplete, onError, signal) => {
  try {
    // 根据use_web参数选择接口
    const endpoint = payload.use_web ? '/llm/search' : '/llm/direct';
    console.log(`Calling ${endpoint} with payload:`, payload);
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/x-json-stream',
        'Cache-Control': 'no-cache',
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      if (chunk) {
        onChunk && onChunk(chunk);
      }
    }

    onComplete && onComplete();
  } catch (error) {
    console.error(`Error calling ${payload.use_web ? '/llm/search' : '/llm/direct'}:`, error);
    onError && onError(error);
  }
};

// 编辑重试 - 从任意消息节点重新生成对话
api.regenerateStream = async (payload, onChunk, onComplete, onError, signal) => {
  try {
    console.log('Calling /llm/regenerate with payload:', payload);
    
    const response = await fetch(`${API_BASE_URL}/llm/regenerate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/x-json-stream',
        'Cache-Control': 'no-cache',
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      if (chunk) {
        onChunk && onChunk(chunk);
      }
    }

    onComplete && onComplete();
  } catch (error) {
    console.error('Error calling /llm/regenerate:', error);
    onError && onError(error);
  }
};

export default api;