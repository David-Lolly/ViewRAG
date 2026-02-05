"""共享测试 fixtures"""

import sys
from pathlib import Path

# 添加 backend 目录到 Python 路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Mock pgvector 以避免导入错误
from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

import pytest


@pytest.fixture
def sample_markdown_with_headers():
    """带标题的 Markdown 示例"""
    return """# 第一章 引言

这是引言部分的内容，介绍了文档的背景和目的。

## 1.1 背景

在当今数字化时代，文档处理变得越来越重要。本节将详细介绍相关背景知识。

## 1.2 目的

本文档旨在说明 RAG 系统的简化重构方案。

# 第二章 方法

本章介绍具体的实现方法。

## 2.1 数据模型

我们采用扁平化的 Chunk 模型来存储文档内容。

### 2.1.1 Chunk 表结构

Chunk 表包含以下字段：id, doc_id, kb_id, chunk_type, content, retrieval_text 等。
"""


@pytest.fixture
def sample_long_markdown():
    """超长文本示例（用于测试二次切分）"""
    long_paragraph = "这是一段很长的文本内容。" * 100  # 约 1200 字符
    return f"""# 长文档测试

## 第一节

{long_paragraph}

## 第二节

这是第二节的内容，相对较短。
"""


@pytest.fixture
def sample_short_chunks_markdown():
    """包含短内容的 Markdown（用于测试最小长度过滤）"""
    return """# 标题

短

## 小节

这是一段足够长的内容，应该被保留下来。

### 子节

x
"""


@pytest.fixture
def sample_chunks_for_context():
    """用于测试 build_context 的 chunk 数据"""
    return [
        {
            'chunk_id': 'chunk-1',
            'chunk_type': 'TEXT',
            'content': '这是一段文本内容',
            'retrieval_text': '这是一段文本内容',
            'metadata': {'heading_path': ['第一章', '1.1 背景']},
            'score': 0.95
        },
        {
            'chunk_id': 'chunk-2',
            'chunk_type': 'IMAGE',
            'content': '/images/figure1.png',
            'retrieval_text': '这是一张系统架构图',
            'metadata': {'caption': 'Figure 1: 系统架构'},
            'score': 0.85
        },
        {
            'chunk_id': 'chunk-3',
            'chunk_type': 'TABLE',
            'content': '| 列1 | 列2 |\n|---|---|\n| A | B |',
            'retrieval_text': '这是一个性能对比表格',
            'metadata': {'caption': 'Table 1: 性能对比'},
            'score': 0.80
        }
    ]
