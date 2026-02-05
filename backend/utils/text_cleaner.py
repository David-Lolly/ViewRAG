"""文本清洗工具"""

import re
import logging

logger = logging.getLogger(__name__)


def clean_markdown(text: str) -> str:
    """
    清洗pymupdf4llm解析出的Markdown文本
    
    主要清洗内容：
    1. 移除乱码字符
    2. 清理格式混乱的公式
    3. 移除多余的空白行
    4. 统一换行符
    
    Args:
        text: 原始Markdown文本
        
    Returns:
        清洗后的文本
    """
    if not text:
        return ""
    
    try:
        # 1. 统一换行符为\n
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # 2. 移除明显的乱码（连续的特殊字符）
        # 例如: ��� 或者 □□□
        text = re.sub(r'[\u25a0\u25a1\ufffd]{3,}', '', text)
        
        # 3. 清理格式混乱的公式（简单版本，后续可完善）
        # 移除包含大量特殊符号且没有空格的行
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # 如果一行中特殊字符占比超过50%且长度超过20，可能是乱码
            if len(line) > 20:
                special_count = len(re.findall(r'[^\w\s\u4e00-\u9fff]', line))
                if special_count / len(line) > 0.5:
                    logger.debug(f"跳过疑似乱码行: {line[:50]}...")
                    continue
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # 4. 移除过多的连续空行（保留最多2个）
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        
        # 5. 移除行首行尾的空白字符
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        logger.info(f"文本清洗完成，原长度: {len(text)}")
        return text
        
    except Exception as e:
        logger.error(f"文本清洗失败: {e}")
        return text  # 清洗失败则返回原文本


def is_text_empty(text: str, min_length: int = 50) -> bool:
    """
    判断文本是否为空或内容过少
    
    Args:
        text: 待检查的文本
        min_length: 最小有效长度
        
    Returns:
        是否为空
    """
    if not text:
        return True
    
    # 移除空白字符后检查
    stripped = text.strip()
    if len(stripped) < min_length:
        return True
    
    # 检查是否全是特殊字符
    alphanumeric = re.sub(r'[^\w\u4e00-\u9fff]', '', stripped)
    if len(alphanumeric) < min_length * 0.3:  # 至少30%是有效字符
        return True
    
    return False






