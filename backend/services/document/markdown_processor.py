"""Markdown结构化处理器"""
# TODO：使用markdown文件进行测试
import re
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class MarkdownProcessor:
    """Markdown结构化处理类（基于用户提供的逻辑）"""
    
    # 正则表达式定义
    IMAGE_RE = re.compile(r'^\s*!\[.*?\]\(.*?\)\s*$')
    TABLE_RE = re.compile(r'^\s*<table.*?>.*?</table>\s*$', re.DOTALL)
    CAPTION_RE = re.compile(
        r'^\s*(?:Figure|Fig\.?|Table|Tab\.?|图|圖|如图|如圖|表|如表)\s*\d+[：:.\u3001、]?\s*',
        re.IGNORECASE
    )
    FIGURE_CAPTION_RE = re.compile(
        r'^\s*(?:Figure|Fig\.?|图|圖|如图|如圖)\s*\d+[：:.\u3001、]?\s*',
        re.IGNORECASE
    )
    TABLE_CAPTION_RE = re.compile(
        r'^\s*(?:Table|Tab\.?|表|如表)\s*\d+[：:.\u3001、]?\s*',
        re.IGNORECASE
    )
    REFERENCE_HEADER_RE = re.compile(
        r'^\s{0,3}#{1,6}\s*(?:参考文献|参考资料|参考来源|引用|references?)\b.*$',
        re.IGNORECASE | re.MULTILINE
    )
    PLAIN_REFERENCE_HEADER_RE = re.compile(
        r'^\s*(?:参考文献|参考资料|参考来源|引用|references?)\s*$',
        re.IGNORECASE | re.MULTILINE
    )
    REFERENCE_ITEM_RE = re.compile(r'^\s*\[\d+\]')
    
    @classmethod
    def classify_block(cls, block: str) -> str:
        """
        根据内容为文本块分类
        
        Args:
            block: 文本块
            
        Returns:
            块类型：'image', 'table', 'caption', 'paragraph'
        """
        if cls.IMAGE_RE.match(block):
            return 'image'
        if cls.TABLE_RE.match(block):
            return 'table'
        if cls.CAPTION_RE.match(block):
            return 'caption'
        return 'paragraph'
    
    @classmethod
    def parse_markdown_to_units(cls, markdown_text: str) -> List[Dict[str, str]]:
        """
        解析Markdown文件，将其转换为结构化的知识单元
        
        功能：
        1. 分离图片、表格、文本
        2. 关联图片/表格和其标题
        3. 合并剩余段落
        
        Args:
            markdown_text: Markdown文本内容
            
        Returns:
            处理后的单元列表 [
                {
                    'type': 'figure_unit',
                    'path': str,
                    'caption': str
                },
                {
                    'type': 'table_unit',
                    'markdown': str,
                    'caption': str
                },
                {
                    'type': 'paragraph',
                    'content': str
                }
            ]
        """
        markdown_text = cls._strip_reference_section(markdown_text)
        text_length = len(markdown_text) if markdown_text else 0
        logger.info(f"开始结构化解析 | Markdown长度={text_length}")
        
        if not markdown_text:
            logger.warning("Markdown文本为空，跳过解析")
            return []
        
        # 1. 按一个或多个空行分割文档为块
        raw_blocks = [
            block.strip() 
            for block in markdown_text.split('\n\n') 
            if block.strip()
        ]
        raw_blocks = cls._filter_reference_blocks(raw_blocks)
        
        logger.debug(f"初步分割 | 原始块数={len(raw_blocks)}")
        
        # 2. 对每个块进行分类
        classified_blocks = []
        for block_content in raw_blocks:
            block_type = cls.classify_block(block_content)
            classified_blocks.append({
                'type': block_type,
                'content': block_content,
                'used': False  # 标志用于跟踪描述是否已被关联
            })
        
        processed_units = []
        num_blocks = len(classified_blocks)
        
        # 3. 遍历并关联图片和表格
        for i, block in enumerate(classified_blocks):
            block_type = block['type']
            
            if block_type in ('image', 'table'):
                caption_content = ""
                caption_found = False
                
                # 目标描述类型
                # a. 向前查找描述（优先）
                if i + 1 < num_blocks:
                    next_block = classified_blocks[i + 1]
                    if next_block['type'] == 'caption' and cls._is_caption_for_type(next_block['content'], block_type):
                        caption_content = next_block['content']
                        next_block['used'] = True
                        caption_found = True
                
                # b. 如果向前没找到，则向后查找
                if not caption_found and i - 1 >= 0:
                    prev_block = classified_blocks[i - 1]
                    if prev_block['type'] == 'caption' and not prev_block['used']:
                        if cls._is_caption_for_type(prev_block['content'], block_type):
                            caption_content = prev_block['content']
                            prev_block['used'] = True
                            caption_found = True
                
                block['used'] = True  # 标记当前图/表块已处理
                
                # 创建独立的单元
                if block_type == 'image':
                    # 从图片Markdown中提取路径
                    path_match = re.search(r'\((.*?)\)', block['content'])
                    image_path = path_match.group(1) if path_match else block['content']
                    unit = {
                        'type': 'figure_unit',
                        'path': image_path,
                        'caption': caption_content
                    }
                else:  # table
                    unit = {
                        'type': 'table_unit',
                        'markdown': block['content'],
                        'caption': caption_content
                    }
                
                processed_units.append(unit)
        
        # 4. 合并所有剩余的、未被使用的块到paragraph中
        remaining_paragraphs = []
        for block in classified_blocks:
            # 如果一个块未被使用(既不是图/表，也不是被关联的caption)
            if not block['used']:
                remaining_paragraphs.append(block['content'])
        
        if remaining_paragraphs:
            processed_units.append({
                'type': 'paragraph',
                'content': '\n\n'.join(remaining_paragraphs)
            })
        
        # 统计结果
        figure_count = sum(1 for u in processed_units if u['type'] == 'figure_unit')
        table_count = sum(1 for u in processed_units if u['type'] == 'table_unit')
        paragraph_count = sum(1 for u in processed_units if u['type'] == 'paragraph')
        
        logger.info(f"结构化完成 | 图={figure_count} | 表={table_count} | 文={paragraph_count} | 总单元数={len(processed_units)}")
        
        # 记录详细信息
        for i, unit in enumerate(processed_units):
            if unit['type'] == 'figure_unit':
                logger.debug(f"图片单元 | 索引={i} | 路径={unit['path'][:80]}... | caption={unit.get('caption', '')[:50]}")
            elif unit['type'] == 'table_unit':
                rows = unit['markdown'].count('\n')
                logger.debug(f"表格单元 | 索引={i} | 行数≈{rows} | caption={unit.get('caption', '')[:50]}")
        
        return processed_units

    @classmethod
    def _strip_reference_section(cls, markdown_text: str) -> str:
        if not markdown_text:
            return markdown_text
        match = cls.REFERENCE_HEADER_RE.search(markdown_text)
        if not match:
            match = cls.PLAIN_REFERENCE_HEADER_RE.search(markdown_text)
        if match:
            logger.info("检测到参考文献章节，已移除该部分内容")
            return markdown_text[:match.start()].rstrip()
        return markdown_text

    @classmethod
    def _filter_reference_blocks(cls, blocks: List[str]) -> List[str]:
        cleaned_blocks = []
        removed = 0
        for block in blocks:
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            if lines and all(cls.REFERENCE_ITEM_RE.match(line) for line in lines):
                removed += 1
                continue
            cleaned_blocks.append(block)
        if removed:
            logger.info(f"过滤掉{removed}个参考文献条目块")
        return cleaned_blocks

    @classmethod
    def _is_caption_for_type(cls, caption_text: str, block_type: str) -> bool:
        if block_type == 'image':
            return bool(cls.FIGURE_CAPTION_RE.match(caption_text))
        if block_type == 'table':
            return bool(cls.TABLE_CAPTION_RE.match(caption_text))
        return False





