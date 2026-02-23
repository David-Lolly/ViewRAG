"""
分块模块

提供 Block 分块和递归分块两种策略。
"""

from .types import (
    Chunk,
    MergedDocument,
    DEFAULT_MAX_CHUNK_SIZE,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_SEPARATORS,
    STANDALONE_TYPES,
)
from .recursive_chunker import chunk_by_recursive
from .block_chunker import chunk_by_block

__all__ = [
    "Chunk",
    "MergedDocument",
    "DEFAULT_MAX_CHUNK_SIZE",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_SEPARATORS",
    "STANDALONE_TYPES",
    "chunk_by_recursive",
    "chunk_by_block",
]
