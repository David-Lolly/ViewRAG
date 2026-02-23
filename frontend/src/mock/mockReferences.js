/**
 * Mock ReferenceItem 数据
 * 模拟后端返回的引用数据，覆盖 TEXT、IMAGE、TABLE 三种 Chunk 类型
 * 场景：关于 "Transformer 注意力机制" 的问答
 */

/**
 * @typedef {Object} ChunkBbox
 * @property {number} page - PDF 页码
 * @property {number[]} bbox - [x0, y0, x1, y1] PDF 坐标
 */

/**
 * @typedef {Object} ReferenceItem
 * @property {number} ref_id - 引用编号，从 1 开始
 * @property {string} chunk_id - Chunk UUID
 * @property {string} chunk_type - TEXT / IMAGE / TABLE
 * @property {string} content - 原始内容
 * @property {string} retrieval_text - 检索用文本
 * @property {string} doc_id - 文档 ID
 * @property {string} file_name - 文件名
 * @property {ChunkBbox[]} chunk_bboxes - 位置信息数组
 * @property {string|null} image_alias - 图片别名，如 "图片1"
 * @property {string|null} image_url - 图片完整 URL
 */

const MOCK_DOC_ID = 'doc-001-attention'
const MOCK_FILE_NAME = 'attention is all you need.pdf'
const MOCK_DOC_ID_2 = 'doc-002-bert'
const MOCK_FILE_NAME_2 = 'BERT Pre-training of Deep Bidirectional Transformers.pdf'

/**
 * Mock 召回文档列表（后端返回的本次回答参考了哪些文档及摘要）
 * @type {Array<{doc_id: string, file_name: string, file_type: string, summary: string, owner: string}>}
 */
export const mockRetrievedDocuments = [
    {
        doc_id: MOCK_DOC_ID,
        file_name: MOCK_FILE_NAME,
        file_type: 'PDF',
        summary: 'Transformer 模型的开创性论文，提出了完全基于注意力机制的序列转换模型架构，摒弃了传统的循环和卷积结构，在机器翻译任务上取得了最优结果。',
        owner: '@user'
    },
    {
        doc_id: MOCK_DOC_ID_2,
        file_name: MOCK_FILE_NAME_2,
        file_type: 'PDF',
        summary: '本文综述了人工智能（AI）关键技术的最新发展现状与趋势，包括AI芯片、芯片使能、大模型、云智一体等关键技术的最新发展和趋势。',
        owner: '@user'
    },
    {
        doc_id: 'doc-003-gpt',
        file_name: '摩通传动校招简章-湖北工业大学.pdf',
        file_type: 'PDF',
        summary: '摩通传动与控制(深圳)有限公司是专注先进制造核心零部件的国家高新技术企业，产品广泛应用于工业自动化领域。',
        owner: '@user'
    }
]

/**
 * Mock ReferenceItem 列表
 * - ref_id=1: TEXT 类型，P3，描述注意力函数
 * - ref_id=2: IMAGE 类型，P2，Transformer 架构图
 * - ref_id=3: TEXT 类型，跨 P3-P4，描述多头注意力（跨页场景）
 * - ref_id=4: TABLE 类型，P5，性能对比表格
 */
export const mockReferenceItems = [
{
      "ref_id": 1,
      "chunk_id": "e167ae74-b810-445e-994b-5c054290572c",
      "chunk_type": "IMAGE",
      "content": "http://127.0.0.1:9000/viewrag-documents/kbs/2ca6ad14-5c5d-48b3-b258-3cde4a1f6be8/images/dc99aaf6-fecb-4637-bbec-d20c93f9fe31/ea671144ff1d.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=xll%2F20260208%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260208T023256Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=038828059e942c7e723339077f143dc417c172c2031b4b97b6c7824843fbff66",
      "retrieval_text": "[ANALYZE]\n\nTopic: 图解说明了缩放点积注意力机制与多头注意力机制。\n\nKey Points:\n1. **左侧图（缩放点积注意力）**：\n   - 展示了缩放点积注意力的计算流程，包括输入矩阵Q、K、V。\n   - 计算过程依次为：首先进行矩阵乘法（MatMul），然后对结果进行缩放（Scale），接着应用掩码（Mask，可选），最后通过SoftMax函数处理。\n   - 最终输出为经过SoftMax处理后的结果。\n\n2. **右侧图（多头注意力）**：\n   - 描述了多头注意力机制，由多个并行的缩放点积注意力层组成。\n   - 每个注意力层接收相同的输入矩阵Q、K、V，并分别通过线性变换（Linear）处理。\n   - 各个注意力层的输出通过拼接（Concat）操作合并，最终形成多头注意力的输出。\n\nConclusion: 该图清晰地展示了缩放点积注意力和多头注意力机制的结构与计算流程，有助于理解这些在深度学习模型中的关键组件。",
      "doc_id": "dc99aaf6-fecb-4637-bbec-d20c93f9fe31",
      "file_name": "attention is all you need.pdf",
      "chunk_bboxes": [
        {
          "page": 3,
          "bbox": [
            170.5,
            69.0,
            467.5,
            242.0
          ]
        }
      ],
      "image_alias": "图片1",
      "image_url": "http://127.0.0.1:9000/viewrag-documents/kbs/2ca6ad14-5c5d-48b3-b258-3cde4a1f6be8/images/dc99aaf6-fecb-4637-bbec-d20c93f9fe31/ea671144ff1d.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=xll%2F20260208%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260208T023256Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=038828059e942c7e723339077f143dc417c172c2031b4b97b6c7824843fbff66"
    },
    {
      "ref_id": 2,
      "chunk_id": "f305c260-e6a5-444a-90b7-4fa99788d72d",
      "chunk_type": "TEXT",
      "content": "Self-attention, sometimes called intra-attention is an attention mechanism relating different positions of a single sequence in order to compute a representation of the sequence. Self-attention has been used successfully in a variety of tasks including reading comprehension, abstractive summarization, textual entailment and learning task-independent sentence representations  $ [4, 27, 28, 22] $.\nEnd-to-end memory networks are based on a recurrent attention mechanism instead of sequence-aligned recurrence and have been shown to perform well on simple-language question answering and language modeling tasks  $ [34] $.\nTo the best of our knowledge, however, the Transformer is the first transduction model relying entirely on self-attention to compute representations of its input and output without using sequence-aligned RNNs or convolution. In the following sections, we will describe the Transformer, motivate self-attention and discuss its advantages over models such as  $ [17, 18] $ and  $ [9] $.",
      "retrieval_text": "Self-attention, sometimes called intra-attention is an attention mechanism relating different positions of a single sequence in order to compute a representation of the sequence. Self-attention has been used successfully in a variety of tasks including reading comprehension, abstractive summarization, textual entailment and learning task-independent sentence representations  $ [4, 27, 28, 22] $.\nEnd-to-end memory networks are based on a recurrent attention mechanism instead of sequence-aligned recurrence and have been shown to perform well on simple-language question answering and language modeling tasks  $ [34] $.\nTo the best of our knowledge, however, the Transformer is the first transduction model relying entirely on self-attention to compute representations of its input and output without using sequence-aligned RNNs or convolution. In the following sections, we will describe the Transformer, motivate self-attention and discuss its advantages over models such as  $ [17, 18] $ and  $ [9] $.",
      "doc_id": "dc99aaf6-fecb-4637-bbec-d20c93f9fe31",
      "file_name": "attention is all you need.pdf",
      "chunk_bboxes": [
        {
          "page": 1,
          "bbox": [
            105.0,
            492.0,
            506.0,
            537.0
          ]
        },
        {
          "page": 1,
          "bbox": [
            105.0,
            541.0,
            506.5,
            575.0
          ]
        },
        {
          "page": 1,
          "bbox": [
            104.5,
            579.0,
            506.5,
            624.0
          ]
        }
      ],
      "image_alias": null,
      "image_url": null
    },
    {
      "ref_id": 3,
      "chunk_id": "9fcc8650-ee53-4659-a55f-cec45312446f",
      "chunk_type": "IMAGE",
      "content": "http://127.0.0.1:9000/viewrag-documents/kbs/2ca6ad14-5c5d-48b3-b258-3cde4a1f6be8/images/dc99aaf6-fecb-4637-bbec-d20c93f9fe31/dc16cf2680b8.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=xll%2F20260208%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260208T023256Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=feea4fc51ce39ab0116f26bf527200b3f8211c73e3a7698330025f671d420482",
      "retrieval_text": "[ANALYZE] \n\nTopic: An example of the attention mechanism in a neural network layer focusing on the word \"making\".\n\nKey Points:\n1. The image illustrates the attention mechanism in layer 5 of 6, specifically highlighting how different attention heads focus on the word \"making\".\n2. Multiple colored lines (each representing a different attention head) show connections to various words in the sentence, such as \"more\" and \"difficult\", indicating long-distance dependencies.\n3. The phrase \"making...more difficult\" is completed by these attention heads, demonstrating how the model captures the relationship between distant words in the sentence.\n\nConclusion: The image effectively visualizes how an attention mechanism in a neural network can track and connect long-distance dependencies, particularly around the verb \"making\", to understand the full context of a sentence.\n\n",
      "doc_id": "dc99aaf6-fecb-4637-bbec-d20c93f9fe31",
      "file_name": "attention is all you need.pdf",
      "chunk_bboxes": [
        {
          "page": 12,
          "bbox": [
            116.5,
            100.0,
            504.0,
            300.5
          ]
        }
      ],
      "image_alias": "图片2",
      "image_url": "http://127.0.0.1:9000/viewrag-documents/kbs/2ca6ad14-5c5d-48b3-b258-3cde4a1f6be8/images/dc99aaf6-fecb-4637-bbec-d20c93f9fe31/dc16cf2680b8.jpg?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=xll%2F20260208%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260208T023256Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=feea4fc51ce39ab0116f26bf527200b3f8211c73e3a7698330025f671d420482"
    },
    {
      "ref_id": 4,
      "chunk_id": "06666c0c-d979-4889-9841-5a43071d49db",
      "chunk_type": "TEXT",
      "content": "3.2.3 Applications of Attention in our Model\n\nThe Transformer uses multi-head attention in three different ways:\n• In \"encoder-decoder attention\" layers, the queries come from the previous decoder layer, and the memory keys and values come from the output of the encoder. This allows every position in the decoder to attend over all positions in the input sequence. This mimics the typical encoder-decoder attention mechanisms in sequence-to-sequence models such as [38, 2, 9].\n• The encoder contains self-attention layers. In a self-attention layer all of the keys, values and queries come from the same place, in this case, the output of the previous layer in the encoder. Each position in the encoder can attend to all positions in the previous layer of the encoder.",
      "retrieval_text": "3.2.3 Applications of Attention in our Model\n\nThe Transformer uses multi-head attention in three different ways:\n• In \"encoder-decoder attention\" layers, the queries come from the previous decoder layer, and the memory keys and values come from the output of the encoder. This allows every position in the decoder to attend over all positions in the input sequence. This mimics the typical encoder-decoder attention mechanisms in sequence-to-sequence models such as [38, 2, 9].\n• The encoder contains self-attention layers. In a self-attention layer all of the keys, values and queries come from the same place, in this case, the output of the previous layer in the encoder. Each position in the encoder can attend to all positions in the previous layer of the encoder.",
      "doc_id": "dc99aaf6-fecb-4637-bbec-d20c93f9fe31",
      "file_name": "attention is all you need.pdf",
      "chunk_bboxes": [
        {
          "page": 4,
          "bbox": [
            105.5,
            279.0,
            305.0,
            291.0
          ]
        },
        {
          "page": 4,
          "bbox": [
            105.0,
            298.0,
            374.0,
            310.0
          ]
        },
        {
          "page": 4,
          "bbox": [
            132.5,
            319.5,
            506.0,
            374.5
          ]
        },
        {
          "page": 4,
          "bbox": [
            133.0,
            378.5,
            505.5,
            422.5
          ]
        }
      ],
      "image_alias": null,
      "image_url": null
    },
    {
      "ref_id": 5,
      "chunk_id": "bcdebe87-8cdc-4c26-985c-8495bfee18e1",
      "chunk_type": "TEXT",
      "content": "The Transformer follows this overall architecture using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder, shown in the left and right halves of Figure 1, respectively.",
      "retrieval_text": "The Transformer follows this overall architecture using stacked self-attention and point-wise, fully connected layers for both the encoder and decoder, shown in the left and right halves of Figure 1, respectively.",
      "doc_id": "dc99aaf6-fecb-4637-bbec-d20c93f9fe31",
      "file_name": "attention is all you need.pdf",
      "chunk_bboxes": [
        {
          "page": 2,
          "bbox": [
            104.5,
            435.5,
            506.5,
            469.5
          ]
        }
      ],
      "image_alias": null,
      "image_url": null
    }
]

/**
 * Mock token 流内容（完整文本，将被拆分为 token 发送）
 */
export const mockStreamContent = `Transformer 模型的核心机制是自注意力（self-attention）和多头注意力（multi-head attention），其设计彻底摒弃了传统的序列对齐的循环神经网络（RNN）或卷积结构，完全依赖注意力机制来捕捉输入与输出之间的关系 [2]。\n\n### 1. 缩放点积注意力机制\n缩放点积注意力是 Transformer 中最基本的操作单元，其计算流程如下图所示：\n\n![缩放点积注意力机制](image:图片1)\n\n- 输入包含三个矩阵：查询（Query, Q）、键（Key, K）和值（Value, V）。\n- 首先进行矩阵乘法（MatMul），得到注意力分数；\n- 然后对结果进行缩放（Scale），以防止梯度消失或爆炸；\n- 可选地应用掩码（Mask），用于屏蔽无效位置（如填充部分）；\n- 最后通过 SoftMax 函数归一化，得到注意力权重；\n- 将加权后的值矩阵求和，得到最终输出。\n\n该机制使得模型能够动态地关注输入序列中不同位置的相关性，尤其在处理长距离依赖时表现出色。\n\n---\n\n### 2. 多头注意力机制\n为了增强模型的表达能力，Transformer 引入了多头注意力机制。如下图所示：\n\n![多头注意力机制](image:图片1)\n\n- 多个并行的缩放点积注意力层同时运行，每个头都接收相同的输入矩阵 $ Q $、$ K $、$ V $；\n- 每个头通过独立的线性变换（Linear Projection）将输入映射到不同的子空间；\n- 各个头的输出被拼接（Concat）在一起，并通过一个最终的线性变换得到多头注意力的输出；\n- 这种设计允许模型在不同表示子空间中并行学习多种类型的依赖关系。\n\n多头注意力不仅提升了模型容量，还增强了对复杂语义结构的建模能力。\n\n---\n\n### 3. 注意力机制的实际效果：捕捉长距离依赖\n在实际应用中，注意力机制能有效识别句子中远距离词语之间的关联。例如，在第5层（共6层）的注意力可视化中，当处理单词“making”时，多个注意力头分别连接到“more”和“difficult”，从而完整理解短语 “making...more difficult” 的含义：\n\n![注意力头聚焦于“making”](image:图片2)\n\n这表明模型能够跨越多个词的距离，准确捕捉上下文语义，克服传统 RNN 在长序列中难以保留远距离信息的问题。\n\n---\n\n### 4. 多头注意力在 Transformer 中的应用场景\n根据论文描述，多头注意力在 Transformer 中有三种使用方式：\n\n| 类型 | 输入来源 | 功能 |\n|------|----------|------|\n| **编码器中的自注意力** | 来自前一层的输出 | 每个位置可关注编码器内所有位置，实现全局上下文建模 |\n| **解码器中的自注意力** | 来自前一层解码器输出 | 使解码器在生成每个词时能参考之前生成的内容 |\n| **编码器-解码器注意力** | 查询来自解码器，键/值来自编码器 | 解码器中的每个位置可关注整个输入序列，实现跨序列信息融合 |\n\n这一架构使得 Transformer 能够高效地建模输入与输出之间的复杂关系，成为现代自然语言处理任务的基础模型。\n\n---\n\n### 总结\n通过引入缩放点积注意力和多头注意力机制，Transformer 实现了无需序列对齐的端到端建模，显著提升了训练效率与性能。其核心优势在于：\n- 并行计算能力强，避免 RNN 的串行依赖；\n- 能够有效捕捉长距离依赖；\n- 多头机制提升表达多样性。\n\n这些特性共同推动了从 BERT 到 GPT 等大规模语言模型的发展，奠定了当代深度学习自然语言处理的基础。`

/**
 * 获取 Mock 历史消息数据
 * 返回包含 references 的历史消息数组，模拟从后端加载的历史对话
 * @returns {Array} 历史消息数组
 */
export function getMockHistoryMessages() {
    return [
        {
            message_id: 'history-msg-001',
            role: 'user',
            content: '请介绍一下 Transformer 的架构',
            timestamp: '2026-02-07T10:00:00Z',
            streamEnded: true
        },
        {
            message_id: 'history-msg-002',
            role: 'assistant',
            content: mockStreamContent,
            references: mockReferenceItems,
            retrieved_documents: mockRetrievedDocuments,
            streamEnded: true,
            isInteractive: true
        },
        {
            message_id: 'history-msg-003',
            role: 'user',
            content: '多头注意力和单头注意力有什么区别？',
            timestamp: '2026-02-07T10:05:00Z',
            streamEnded: true
        },
        {
            message_id: 'history-msg-004',
            role: 'assistant',
            content: '多头注意力机制相比单头注意力有以下关键区别[3]：\n\n1. **并行关注能力**：多头注意力允许模型同时关注不同位置的信息，而单头注意力只能关注一个位置。\n\n2. **子空间表示**：多头注意力将查询、键、值投影到多个不同的子空间中，每个头学习不同的表示模式。\n\n从性能对比来看[4]，使用多头注意力的 Transformer 在翻译任务上显著优于其他模型。',
            references: mockReferenceItems.filter(r => r.ref_id === 3 || r.ref_id === 4),
            retrieved_documents: mockRetrievedDocuments.slice(0, 2),
            streamEnded: true,
            isInteractive: true
        }
    ]
}
