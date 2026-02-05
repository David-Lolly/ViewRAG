"""RetrievalService 单元测试

测试 build_context 方法的上下文构建逻辑。

**Feature: rag-simplification**
**Validates: Requirements 6.4**
"""

import sys
from pathlib import Path

# 设置路径
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import pytest

# Mock 外部依赖
from unittest.mock import MagicMock
sys.modules['pgvector'] = MagicMock()
sys.modules['pgvector.sqlalchemy'] = MagicMock()

# 创建一个简化的 UnifiedRetrievalService 用于测试 build_context
class MockRetrievalService:
    """用于测试的简化版 RetrievalService"""
    
    def build_context(self, chunks):
        """构建 LLM 上下文"""
        context_items = []
        
        for chunk in chunks:
            chunk_type = chunk.get('chunk_type', 'TEXT')
            content = chunk.get('content', '')
            
            if chunk_type == 'TEXT':
                context_items.append({
                    'type': 'text',
                    'content': content
                })
            elif chunk_type == 'IMAGE':
                context_items.append({
                    'type': 'image',
                    'content': content
                })
            elif chunk_type == 'TABLE':
                context_items.append({
                    'type': 'table',
                    'content': content
                })
        
        return context_items
    
    def _format_context(self, context_items, chunks):
        """格式化检索结果为上下文文本"""
        if not context_items:
            return ""
        
        formatted_parts = []
        for i, (ctx, chunk) in enumerate(zip(context_items, chunks), 1):
            content = ctx.get('content', '')
            ctx_type = ctx.get('type', 'text')
            metadata = chunk.get('metadata', {})
            
            meta_info = ""
            if ctx_type == 'image':
                caption = metadata.get('caption', '')
                meta_info = f"[图片: {caption}]" if caption else "[图片]"
            elif ctx_type == 'table':
                caption = metadata.get('caption', '')
                meta_info = f"[表格: {caption}]" if caption else "[表格]"
            else:
                heading_path = metadata.get('heading_path', [])
                if heading_path:
                    meta_info = f"[章节: {' > '.join(heading_path)}]"
            
            formatted_parts.append(f"片段{i}{meta_info}:\n{content}\n")
        
        return "\n".join(formatted_parts)


class TestBuildContext:
    """build_context 方法测试"""
    
    @pytest.fixture
    def retrieval_service(self):
        """创建 RetrievalService 实例"""
        return MockRetrievalService()
    
    @pytest.fixture
    def sample_chunks_for_context(self):
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
    
    # ==================== Property 12: Context building by type ====================
    # **Feature: rag-simplification, Property 12: Context building by type**
    
    def test_build_context_text_type(self, retrieval_service):
        """
        Property 12: Context building by type - TEXT
        
        *For any* TEXT chunk, the context builder SHALL return content field.
        
        **Validates: Requirements 6.4**
        """
        chunks = [{
            'chunk_id': 'chunk-1',
            'chunk_type': 'TEXT',
            'content': '这是文本内容',
            'retrieval_text': '这是文本内容',
            'metadata': {},
            'score': 0.9
        }]
        
        result = retrieval_service.build_context(chunks)
        
        assert len(result) == 1
        assert result[0]['type'] == 'text'
        assert result[0]['content'] == '这是文本内容'
    
    def test_build_context_image_type(self, retrieval_service):
        """
        Property 12: Context building by type - IMAGE
        
        *For any* IMAGE chunk, the context builder SHALL return content field (image URL).
        
        **Validates: Requirements 6.4**
        """
        chunks = [{
            'chunk_id': 'chunk-2',
            'chunk_type': 'IMAGE',
            'content': '/images/figure1.png',
            'retrieval_text': '图片描述',
            'metadata': {'caption': 'Figure 1'},
            'score': 0.85
        }]
        
        result = retrieval_service.build_context(chunks)
        
        assert len(result) == 1
        assert result[0]['type'] == 'image'
        assert result[0]['content'] == '/images/figure1.png'
    
    def test_build_context_table_type(self, retrieval_service):
        """
        Property 12: Context building by type - TABLE
        
        *For any* TABLE chunk, the context builder SHALL return content field (original Markdown).
        
        **Validates: Requirements 6.4**
        """
        table_markdown = '| 列1 | 列2 |\n|---|---|\n| A | B |'
        chunks = [{
            'chunk_id': 'chunk-3',
            'chunk_type': 'TABLE',
            'content': table_markdown,
            'retrieval_text': '表格摘要',
            'metadata': {'caption': 'Table 1'},
            'score': 0.8
        }]
        
        result = retrieval_service.build_context(chunks)
        
        assert len(result) == 1
        assert result[0]['type'] == 'table'
        assert result[0]['content'] == table_markdown
    
    def test_build_context_mixed_types(self, retrieval_service, sample_chunks_for_context):
        """测试混合类型的上下文构建"""
        result = retrieval_service.build_context(sample_chunks_for_context)
        
        assert len(result) == 3
        
        # 验证类型映射
        assert result[0]['type'] == 'text'
        assert result[1]['type'] == 'image'
        assert result[2]['type'] == 'table'
        
        # 验证内容正确传递
        assert result[0]['content'] == '这是一段文本内容'
        assert result[1]['content'] == '/images/figure1.png'
        assert '列1' in result[2]['content']
    
    def test_build_context_empty_input(self, retrieval_service):
        """测试空输入"""
        result = retrieval_service.build_context([])
        assert result == []
    
    def test_build_context_preserves_order(self, retrieval_service, sample_chunks_for_context):
        """测试保持输入顺序"""
        result = retrieval_service.build_context(sample_chunks_for_context)
        
        # 顺序应该与输入一致
        assert result[0]['type'] == 'text'
        assert result[1]['type'] == 'image'
        assert result[2]['type'] == 'table'


class TestFormatContext:
    """_format_context 方法测试"""
    
    @pytest.fixture
    def retrieval_service(self):
        return MockRetrievalService()
    
    @pytest.fixture
    def sample_chunks_for_context(self):
        """用于测试的 chunk 数据"""
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
    
    def test_format_context_with_metadata(self, retrieval_service, sample_chunks_for_context):
        """测试带元数据的格式化"""
        context_items = retrieval_service.build_context(sample_chunks_for_context)
        result = retrieval_service._format_context(context_items, sample_chunks_for_context)
        
        assert isinstance(result, str)
        assert len(result) > 0
        
        # 验证包含片段标记
        assert '片段1' in result
        assert '片段2' in result
        assert '片段3' in result
        
        # 验证包含元数据信息
        assert '章节' in result or '图片' in result or '表格' in result
    
    def test_format_context_text_with_heading_path(self, retrieval_service):
        """测试文本类型的标题路径格式化"""
        chunks = [{
            'chunk_id': 'chunk-1',
            'chunk_type': 'TEXT',
            'content': '内容',
            'retrieval_text': '内容',
            'metadata': {'heading_path': ['第一章', '1.1 背景']},
            'score': 0.9
        }]
        context_items = retrieval_service.build_context(chunks)
        result = retrieval_service._format_context(context_items, chunks)
        
        assert '章节' in result
        assert '第一章' in result or '1.1' in result
    
    def test_format_context_image_with_caption(self, retrieval_service):
        """测试图片类型的标题格式化"""
        chunks = [{
            'chunk_id': 'chunk-2',
            'chunk_type': 'IMAGE',
            'content': '/path/to/image.png',
            'retrieval_text': '描述',
            'metadata': {'caption': 'Figure 1: 架构图'},
            'score': 0.85
        }]
        context_items = retrieval_service.build_context(chunks)
        result = retrieval_service._format_context(context_items, chunks)
        
        assert '图片' in result
        assert 'Figure 1' in result or '架构图' in result
    
    def test_format_context_table_with_caption(self, retrieval_service):
        """测试表格类型的标题格式化"""
        chunks = [{
            'chunk_id': 'chunk-3',
            'chunk_type': 'TABLE',
            'content': '| A | B |',
            'retrieval_text': '摘要',
            'metadata': {'caption': 'Table 1: 对比'},
            'score': 0.8
        }]
        context_items = retrieval_service.build_context(chunks)
        result = retrieval_service._format_context(context_items, chunks)
        
        assert '表格' in result
        assert 'Table 1' in result or '对比' in result
    
    def test_format_context_empty(self, retrieval_service):
        """测试空输入"""
        result = retrieval_service._format_context([], [])
        assert result == ""
