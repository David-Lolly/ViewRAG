"""SQLAlchemy ORM table definitions for application data."""

from datetime import datetime
from typing import List, Optional
import enum

from sqlalchemy import DateTime, ForeignKey, String, Text, func, Enum, CheckConstraint, Index
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship
from pgvector.sqlalchemy import Vector


Base = declarative_base()


# ==================== 枚举类型定义 ====================

class DocumentType(str, enum.Enum):
    """文档类型枚举"""
    PDF = "PDF"
    DOCX = "DOCX"
    TXT = "TXT"
    MARKDOWN = "MARKDOWN"
    IMAGE = "IMAGE"
    PPTX = "PPTX"


class DocumentStatus(str, enum.Enum):
    """文档处理状态枚举"""
    QUEUED = "QUEUED"           # 已接收，在队列中等待处理
    PARSING = "PARSING"         # 正在解析
    CHUNKING = "CHUNKING"       # 正在分块
    ENRICHING = "ENRICHING"     # (仅KB) 正在调用LLM进行内容增强
    VECTORIZING = "VECTORIZING" # 正在向量化
    COMPLETED = "COMPLETED"     # 全部完成
    FAILED = "FAILED"           # 处理失败


class UnitType(str, enum.Enum):
    """内容单元类型枚举
    
    [DEPRECATED] 此枚举用于旧版 ContentUnit 表，当前已被 ChunkType 替代。
    保留以备后续分层检索扩展使用。
    """
    TEXT_CHUNK = "TEXT_CHUNK"   # L1 文本章节
    TEXT_SPLIT = "TEXT_SPLIT"   # L2 细粒度文本块
    IMAGE = "IMAGE"             # 图片单元
    TABLE = "TABLE"             # 表格单元


class ChunkType(str, enum.Enum):
    """Chunk 类型枚举 - 简化后的统一内容块类型"""
    TEXT = "TEXT"     # 文本块
    IMAGE = "IMAGE"   # 图片块
    TABLE = "TABLE"   # 表格块


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete",
        passive_deletes=True,
    )
    files: Mapped[List["ChatFile"]] = relationship(
        "ChatFile", back_populates="user", cascade="all, delete-orphan"
    )


class ChatSession(Base):
    __tablename__ = "sessions"

    session_id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Chat")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[Optional["User"]] = relationship("User", back_populates="sessions")
    messages: Mapped[List["Message"]] = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan"
    )
    files: Mapped[List["ChatFile"]] = relationship(
        "ChatFile", back_populates="session", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # 图片URL字段
    timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    files: Mapped[List["ChatFile"]] = relationship("ChatFile", back_populates="message", cascade="all, delete-orphan")


class ChatFile(Base):
    """聊天文件表 - 存储上传的图片和文档信息"""
    __tablename__ = "chat_files"
    
    file_id: Mapped[str] = mapped_column(String(255), primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("messages.message_id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'image' 或 'document'
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)  # MinIO存储路径
    file_size: Mapped[str] = mapped_column(String(20), nullable=False)  # 文件大小（字节）
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    minio_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # MinIO访问URL
    thumbnail_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)  # 缩略图URL
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="files")
    message: Mapped[Optional["Message"]] = relationship("Message", back_populates="files")
    user: Mapped["User"] = relationship("User", back_populates="files")


# ==================== RAG系统模型 ====================

class KnowledgeBase(Base):
    """知识库表"""
    __tablename__ = "knowledge_bases"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # KB路由用
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    user: Mapped["User"] = relationship("User", backref="knowledge_bases")
    documents: Mapped[List["Document"]] = relationship(
        "Document", back_populates="knowledge_base", cascade="all, delete-orphan"
    )


class Document(Base):
    """文档表 - 统一管理会话和知识库文档"""
    __tablename__ = "documents"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    
    # 核心：归属字段 (二选一)
    session_id: Mapped[Optional[str]] = mapped_column(
        String(255), ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=True, index=True
    )
    kb_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("knowledge_bases.id", ondelete="CASCADE"), nullable=True, index=True
    )
    
    # 元数据
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)  # MinIO 存储路径
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), nullable=False, default=DocumentStatus.QUEUED
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # (KB Track 专用) 文档路由字段
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary_vector: Mapped[Optional[Vector]] = mapped_column(Vector(1024), nullable=True)
    
    # 关系
    session: Mapped[Optional["ChatSession"]] = relationship("ChatSession", backref="documents")
    knowledge_base: Mapped[Optional["KnowledgeBase"]] = relationship("KnowledgeBase", back_populates="documents")
    content_units: Mapped[List["ContentUnit"]] = relationship(
        "ContentUnit", back_populates="document", cascade="all, delete-orphan"
    )
    chunks: Mapped[List["Chunk"]] = relationship(
        "Chunk", back_populates="document", cascade="all, delete-orphan"
    )
    
    # 约束：确保归属唯一
    __table_args__ = (
        CheckConstraint(
            "(session_id IS NOT NULL AND kb_id IS NULL) OR (session_id IS NULL AND kb_id IS NOT NULL)",
            name="chk_document_owner"
        ),
    )


class ContentUnit(Base):
    """内容单元表 - 存储所有粒度的内容块
    
    [DEPRECATED] 当前阶段已被简化的 Chunk 表替代。
    保留此表定义以备后续分层检索扩展使用（如需要 L1/L2 层级结构）。
    """
    __tablename__ = "content_units"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    doc_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("content_units.id", ondelete="SET NULL"), nullable=True, index=True
    )
    unit_type: Mapped[UnitType] = mapped_column(Enum(UnitType), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # L2 原始文本 / L1 Image URL/Table Markdown原文 / L1 原始段落
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # L1 LLM生成的摘要/描述
    meta_data: Mapped[Optional[dict]] = mapped_column(Text, nullable=True)     # JSON存储页码、标题等
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    document: Mapped["Document"] = relationship("Document", back_populates="content_units")
    retrieval_index: Mapped[Optional["RetrievalIndex"]] = relationship(
        "RetrievalIndex", back_populates="content_unit", cascade="all, delete-orphan", uselist=False
    )


class RetrievalIndex(Base):
    """检索索引表 - 专为RAG检索优化的瘦表
    
    [DEPRECATED] 当前阶段已被简化的 Chunk 表替代，向量直接存储在 Chunk.content_vector。
    保留此表定义以备后续分层检索扩展使用。
    """
    __tablename__ = "retrieval_index"
    
    unit_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("content_units.id", ondelete="CASCADE"), primary_key=True
    )
    
    # 冗余ID，用于快速过滤
    doc_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    kb_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)  # NULL 表示 L1
    
    retrieval_text: Mapped[str] = mapped_column(Text, nullable=False)         # L1用Summary, L2用Content
    text_vector: Mapped[Vector] = mapped_column(Vector(1024), nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    content_unit: Mapped["ContentUnit"] = relationship("ContentUnit", back_populates="retrieval_index")


class Chunk(Base):
    """统一内容块表 - 简化后的扁平化存储结构"""
    __tablename__ = "chunks"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    doc_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kb_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)  # 冗余字段，加速检索过滤
    
    chunk_type: Mapped[ChunkType] = mapped_column(Enum(ChunkType), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)           # 原始内容
    retrieval_text: Mapped[str] = mapped_column(Text, nullable=False)    # 检索用文本
    content_vector: Mapped[Vector] = mapped_column(Vector(1024), nullable=False)
    chunk_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON 格式元数据
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")


__all__ = [
    "Base", 
    "User", 
    "ChatSession", 
    "Message", 
    "ChatFile",
    "DocumentType",
    "DocumentStatus", 
    "UnitType",
    "ChunkType",
    "KnowledgeBase", 
    "Document", 
    "ContentUnit", 
    "RetrievalIndex",
    "Chunk"
]
