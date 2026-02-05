import api from '../services/api';

// ==================== Mock 数据 ====================
const MOCK_ENABLED = true; // 开关：true 使用 Mock，false 调用真实后端

// Mock 知识库数据
const mockKnowledgeBases = [
  {
    id: 'kb-001',
    name: 'AI技术文档',
    description: '人工智能相关技术文档和论文',
    created_at: '2024-01-15T10:30:00Z',
    document_count: 5
  },
  {
    id: 'kb-002',
    name: '产品设计资料',
    description: '产品设计相关的文档和规范',
    created_at: '2024-02-20T14:20:00Z',
    document_count: 3
  }
];

// Mock 文档数据
const mockDocuments = {
  'kb-001': [
    {
      id: 'doc-001',
      kb_id: 'kb-001',
      file_name: '人工智能关键技术发展现状与趋势研究_NormalPdf.pdf',
      document_type: 'PDF',
      status: 'COMPLETED',
      created_at: '2024-10-15T08:00:00Z',
      progress: 100,
      current_step: '完成'
    },
    {
      id: 'doc-002',
      kb_id: 'kb-001',
      file_name: 'CNN深度学习教程.pdf',
      document_type: 'PDF',
      status: 'PROCESSING',
      created_at: '2024-11-10T09:30:00Z',
      progress: 60,
      current_step: '处理表格和图片'
    },
    {
      id: 'doc-003',
      kb_id: 'kb-001',
      file_name: '机器学习算法总结.docx',
      document_type: 'DOCX',
      status: 'PARSING',
      created_at: '2024-11-12T11:00:00Z',
      progress: 20,
      current_step: '解析中'
    },
    {
      id: 'doc-004',
      kb_id: 'kb-001',
      file_name: '自然语言处理基础.pdf',
      document_type: 'PDF',
      status: 'FAILED',
      created_at: '2024-11-13T14:20:00Z',
      error_message: '文档解析失败：格式不支持',
      progress: 0,
      current_step: '失败'
    },
    {
      id: 'doc-005',
      kb_id: 'kb-001',
      file_name: '计算机视觉应用案例.pdf',
      document_type: 'PDF',
      status: 'COMPLETED',
      created_at: '2024-11-14T16:45:00Z',
      progress: 100,
      current_step: '完成'
    }
  ],
  'kb-002': [
    {
      id: 'doc-006',
      kb_id: 'kb-002',
      file_name: '产品需求文档模板.docx',
      document_type: 'DOCX',
      status: 'COMPLETED',
      created_at: '2024-09-23T10:00:00Z',
      progress: 100,
      current_step: '完成'
    },
    {
      id: 'doc-007',
      kb_id: 'kb-002',
      file_name: 'UI设计规范.pdf',
      document_type: 'PDF',
      status: 'COMPLETED',
      created_at: '2024-10-05T15:30:00Z',
      progress: 100,
      current_step: '完成'
    },
    {
      id: 'doc-008',
      kb_id: 'kb-002',
      file_name: '用户体验研究报告.pdf',
      document_type: 'PDF',
      status: 'PROCESSING',
      created_at: '2024-11-14T09:00:00Z',
      progress: 40,
      current_step: '分段中'
    }
  ]
};

// 文档处理状态到进度的映射
export const STATUS_PROGRESS_MAP = {
  'UPLOADING': { progress: 0, step: '上传中' },
  'PARSING': { progress: 20, step: '解析中' },
  'CHUNKING': { progress: 40, step: '分段中' },
  'PROCESSING': { progress: 60, step: '处理表格和图片' },
  'EMBEDDING': { progress: 80, step: '向量化嵌入' },
  'COMPLETED': { progress: 100, step: '完成' },
  'FAILED': { progress: 0, step: '失败' }
};

// ==================== 辅助函数 ====================
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// ==================== API 方法 ====================

/**
 * 获取用户的所有知识库列表
 * @param {string} userId - 用户ID
 * @returns {Promise<Array>} 知识库列表
 */
export const getKnowledgeBases = async (userId) => {
  if (MOCK_ENABLED) {
    await delay(300); // 模拟网络延迟
    return {
      data: {
        knowledge_bases: mockKnowledgeBases.map(kb => ({
          ...kb,
          document_count: mockDocuments[kb.id]?.length || 0
        }))
      }
    };
  }
  
  // 真实 API 调用
  return api.get('/api/v1/kb', {
    params: { user_id: userId }
  });
};

/**
 * 创建新知识库
 * @param {string} userId - 用户ID
 * @param {string} name - 知识库名称
 * @param {string} description - 知识库描述
 * @returns {Promise<Object>} 新创建的知识库
 */
export const createKnowledgeBase = async (userId, name, description) => {
  if (MOCK_ENABLED) {
    await delay(500);
    const newKb = {
      id: `kb-${Date.now()}`,
      name,
      description,
      created_at: new Date().toISOString(),
      document_count: 0
    };
    mockKnowledgeBases.push(newKb);
    mockDocuments[newKb.id] = [];
    return { data: newKb };
  }
  
  return api.post('/api/v1/kb', {
    user_id: userId,
    name,
    description
  });
};

/**
 * 删除知识库
 * @param {string} kbId - 知识库ID
 * @returns {Promise<void>}
 */
export const deleteKnowledgeBase = async (kbId) => {
  if (MOCK_ENABLED) {
    await delay(300);
    const index = mockKnowledgeBases.findIndex(kb => kb.id === kbId);
    if (index !== -1) {
      mockKnowledgeBases.splice(index, 1);
      delete mockDocuments[kbId];
    }
    return { data: { success: true } };
  }
  
  return api.delete(`/api/v1/kb/${kbId}`);
};

/**
 * 获取知识库详情
 * @param {string} kbId - 知识库ID
 * @returns {Promise<Object>} 知识库详情
 */
export const getKnowledgeBaseDetail = async (kbId) => {
  if (MOCK_ENABLED) {
    await delay(200);
    const kb = mockKnowledgeBases.find(k => k.id === kbId);
    if (!kb) {
      throw new Error('知识库不存在');
    }
    return {
      data: {
        ...kb,
        document_count: mockDocuments[kbId]?.length || 0
      }
    };
  }
  
  return api.get(`/api/v1/kb/${kbId}`);
};

/**
 * 获取知识库下的所有文档
 * @param {string} kbId - 知识库ID
 * @returns {Promise<Array>} 文档列表
 */
export const getDocuments = async (kbId) => {
  if (MOCK_ENABLED) {
    await delay(300);
    return {
      data: {
        documents: mockDocuments[kbId] || []
      }
    };
  }
  
  return api.get(`/api/v1/kb/${kbId}/documents`);
};

/**
 * 上传文档到知识库（支持批量）
 * @param {string} kbId - 知识库ID
 * @param {FileList} files - 文件列表
 * @param {Function} onProgress - 上传进度回调
 * @returns {Promise<Array>} 上传结果
 */
export const uploadDocuments = async (kbId, files, onProgress) => {
  if (MOCK_ENABLED) {
    // 模拟批量上传
    const uploadedDocs = [];
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      await delay(500); // 模拟上传延迟
      
      const newDoc = {
        id: `doc-${Date.now()}-${i}`,
        kb_id: kbId,
        file_name: file.name,
        document_type: getDocumentType(file.name),
        status: 'UPLOADING',
        created_at: new Date().toISOString(),
        progress: 0,
        current_step: '上传中'
      };
      
      if (!mockDocuments[kbId]) {
        mockDocuments[kbId] = [];
      }
      mockDocuments[kbId].push(newDoc);
      uploadedDocs.push(newDoc);
      
      // 回调进度
      if (onProgress) {
        onProgress({
          current: i + 1,
          total: files.length,
          currentFile: file.name
        });
      }
      
      // 模拟自动开始处理
      simulateDocumentProcessing(newDoc.id, kbId);
    }
    
    return { data: { documents: uploadedDocs } };
  }
  
  // 真实 API 调用
  const formData = new FormData();
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }
  
  return api.post(`/api/v1/kb/${kbId}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress({
          percent: percentCompleted,
          loaded: progressEvent.loaded,
          total: progressEvent.total
        });
      }
    }
  });
};

/**
 * 删除文档
 * @param {string} kbId - 知识库ID
 * @param {string} docId - 文档ID
 * @returns {Promise<void>}
 */
export const deleteDocument = async (kbId, docId) => {
  if (MOCK_ENABLED) {
    await delay(300);
    const docs = mockDocuments[kbId];
    if (docs) {
      const index = docs.findIndex(doc => doc.id === docId);
      if (index !== -1) {
        docs.splice(index, 1);
      }
    }
    return { data: { success: true } };
  }
  
  return api.delete(`/api/v1/kb/${kbId}/documents/${docId}`);
};

/**
 * 获取文档处理状态
 * @param {string} docId - 文档ID
 * @returns {Promise<Object>} 文档状态
 */
export const getDocumentStatus = async (docId) => {
  if (MOCK_ENABLED) {
    await delay(100);
    // 在所有知识库中查找文档
    for (const kbId in mockDocuments) {
      const doc = mockDocuments[kbId].find(d => d.id === docId);
      if (doc) {
        return { data: doc };
      }
    }
    throw new Error('文档不存在');
  }
  
  return api.get(`/api/v1/documents/${docId}/status`);
};

// ==================== Mock 辅助函数 ====================

/**
 * 根据文件名获取文档类型
 */
function getDocumentType(fileName) {
  const ext = fileName.split('.').pop().toUpperCase();
  const typeMap = {
    'PDF': 'PDF',
    'DOCX': 'DOCX',
    'DOC': 'DOCX',
    'TXT': 'TXT',
    'MD': 'MARKDOWN',
    'PPTX': 'PPTX',
    'PPT': 'PPTX',
    'PNG': 'IMAGE',
    'JPG': 'IMAGE',
    'JPEG': 'IMAGE'
  };
  return typeMap[ext] || 'PDF';
}

/**
 * 模拟文档处理流程
 * 按照关键节点自动更新文档状态
 */
function simulateDocumentProcessing(docId, kbId) {
  const steps = [
    { status: 'PARSING', delay: 2000 },      // 2秒后开始解析
    { status: 'CHUNKING', delay: 3000 },     // 3秒后开始分段
    { status: 'PROCESSING', delay: 4000 },   // 4秒后处理表格图片
    { status: 'EMBEDDING', delay: 3000 },    // 3秒后向量化
    { status: 'COMPLETED', delay: 2000 }     // 2秒后完成
  ];
  
  let currentStepIndex = 0;
  
  const processNextStep = () => {
    if (currentStepIndex >= steps.length) return;
    
    const step = steps[currentStepIndex];
    
    setTimeout(() => {
      const docs = mockDocuments[kbId];
      if (!docs) return;
      
      const doc = docs.find(d => d.id === docId);
      if (!doc) return;
      
      // 更新文档状态
      doc.status = step.status;
      const statusInfo = STATUS_PROGRESS_MAP[step.status];
      doc.progress = statusInfo.progress;
      doc.current_step = statusInfo.step;
      
      console.log(`[Mock] 文档 ${docId} 状态更新: ${step.status} (${statusInfo.progress}%)`);
      
      currentStepIndex++;
      processNextStep();
    }, step.delay);
  };
  
  processNextStep();
}

export default {
  getKnowledgeBases,
  createKnowledgeBase,
  deleteKnowledgeBase,
  getKnowledgeBaseDetail,
  getDocuments,
  uploadDocuments,
  deleteDocument,
  getDocumentStatus,
  STATUS_PROGRESS_MAP
};

