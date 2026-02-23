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

// 触发生成会话标题（LLM 摘要）
api.generateSessionTitle = (sessionId) => {
  return api.post(`/sessions/${sessionId}/generate_title`);
};

// 获取会话标题
api.getSessionTitle = (sessionId) => {
  return api.get(`/sessions/${sessionId}/title`);
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

// 流式搜索 - 发送聊天消息
api.searchStream = async (payload, onChunk, onComplete, onError, signal) => {
  try {
    const endpoint = '/chat/send';
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
    console.error('Error calling /chat/send:', error);
    onError && onError(error);
  }
};

// 编辑重试 - 从任意消息节点重新生成对话
api.regenerateStream = async (payload, onChunk, onComplete, onError, signal) => {
  try {
    console.log('Calling /chat/regenerate with payload:', payload);

    const response = await fetch(`${API_BASE_URL}/chat/regenerate`, {
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
    console.error('Error calling /chat/regenerate:', error);
    onError && onError(error);
  }
};

// 上传文档到会话
api.uploadSessionDocument = async (sessionId, file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const fileSizeMB = (file.size / 1024 / 1024).toFixed(2);
  console.log(`[Upload] 开始上传 | 文件: ${file.name} | 大小: ${fileSizeMB}MB | session: ${sessionId}`);
  const uploadStart = performance.now();
  let uploadDoneTime = null;

  const response = await api.post(`/api/v1/session/${sessionId}/upload_document`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
    onUploadProgress: (progressEvent) => {
      if (progressEvent.loaded === progressEvent.total && !uploadDoneTime) {
        uploadDoneTime = performance.now();
        const uploadElapsed = ((uploadDoneTime - uploadStart) / 1000).toFixed(2);
        console.log(`[Upload] 浏览器上传完成 | 文件: ${file.name} | 上传耗时: ${uploadElapsed}s`);
      }
      if (onProgress) onProgress(progressEvent);
    },
  });

  const totalElapsed = ((performance.now() - uploadStart) / 1000).toFixed(2);
  const serverProcessTime = uploadDoneTime
    ? (((performance.now() - uploadDoneTime) / 1000).toFixed(2))
    : 'N/A';
  console.log(`[Upload] 接口返回 | 文件: ${file.name} | 总耗时: ${totalElapsed}s | 上传后等待服务端: ${serverProcessTime}s | 状态: ${response.status}`);

  return response.data;
};

// 查询单个文档处理状态
api.getDocumentStatus = async (docId) => {
  const response = await api.get(`/api/v1/documents/${docId}/status`);
  return response.data;
};

// 获取会话的文档列表
api.getSessionDocuments = (sessionId) => {
  return api.get(`/api/v1/session/${sessionId}/documents`);
};

// 删除会话文档
api.deleteSessionDocument = (sessionId, docId) => {
  return api.delete(`/api/v1/session/${sessionId}/document/${docId}`);
};

/**
 * 建立 SSE 连接处理文档并接收进度更新
 * @param {string} docId - 文档ID
 * @param {string} track - 轨道类型，'session' 或 'kb'
 * @param {function} onProgress - 进度回调函数，接收 {status, progress, step, error_message}
 * @param {function} onComplete - 完成回调函数
 * @param {function} onError - 错误回调函数
 * @returns {EventSource} SSE 连接对象，可用于关闭连接
 */
api.processDocumentSSE = (docId, track = 'session', onProgress, onComplete, onError) => {
  const baseURL = api.defaults.baseURL || '';
  // 注意：JS 参数可以接收 undefined，这里做参数校验
  const validTrack = track || 'session';
  const url = `${baseURL}/api/v1/documents/${docId}/process?track=${validTrack}`;

  console.log(`[SSE] 建立连接 | doc_id: ${docId} | track: ${validTrack} | url: ${url}`);

  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      console.log(`[SSE] 收到状态更新 | doc_id: ${docId} | status: ${data.status} | progress: ${data.progress}% | step: ${data.step}`);

      if (onProgress) {
        onProgress(data);
      }

      // 终态：关闭连接
      if (data.status === 'COMPLETED' || data.status === 'FAILED') {
        console.log(`[SSE] 处理完成 | doc_id: ${docId} | 最终状态: ${data.status}`);
        eventSource.close();
        if (onComplete) {
          onComplete(data);
        }
      }
    } catch (e) {
      console.error(`[SSE] 解析数据失败 | doc_id: ${docId} | 错误: ${e.message}`);
    }
  };

  eventSource.onerror = (error) => {
    console.error(`[SSE] 连接错误 | doc_id: ${docId}`, error);
    eventSource.close();
    if (onError) {
      onError(error);
    }
  };

  return eventSource;
};

export default api;