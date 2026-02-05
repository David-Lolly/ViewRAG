"""remove_old_rag_tables

Revision ID: remove_old_rag_tables
Revises: add_chunks_table
Create Date: 2026-01-19

注意：此迁移脚本用于删除旧的 L1/L2 分层架构相关表。
在执行此迁移前，请确保：
1. 已完成数据迁移（如需要）
2. 已备份重要数据
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'remove_old_rag_tables'
down_revision: Union[str, Sequence[str], None] = 'add_chunks_table'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - 删除旧的 RAG 表"""
    
    # 1. 删除 retrieval_index 表（先删除，因为它依赖 content_units）
    op.drop_table('retrieval_index')
    
    # 2. 删除 content_units 表
    op.drop_table('content_units')
    
    # 3. 删除 unit_type 枚举类型
    op.execute('DROP TYPE IF EXISTS unit_type')


def downgrade() -> None:
    """Downgrade schema - 重新创建旧的 RAG 表"""
    
    # 1. 重新创建 unit_type 枚举
    op.execute("""
        CREATE TYPE unit_type AS ENUM (
            'TEXT_CHUNK', 'TEXT_SPLIT', 'IMAGE', 'TABLE'
        )
    """)
    
    # 2. 重新创建 content_units 表
    op.create_table(
        'content_units',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('doc_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('parent_id', sa.String(36), sa.ForeignKey('content_units.id', ondelete='SET NULL'), nullable=True),
        sa.Column('unit_type', sa.Enum('TEXT_CHUNK', 'TEXT_SPLIT', 'IMAGE', 'TABLE', name='unit_type'), nullable=False),
        sa.Column('content', sa.Text, nullable=True),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('metadata', sa.JSON, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_content_units_doc_id', 'content_units', ['doc_id'])
    op.create_index('ix_content_units_parent_id', 'content_units', ['parent_id'])
    
    # 3. 重新创建 retrieval_index 表
    op.create_table(
        'retrieval_index',
        sa.Column('unit_id', sa.String(36), sa.ForeignKey('content_units.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('doc_id', sa.String(36), nullable=False),
        sa.Column('session_id', sa.String(255), nullable=True),
        sa.Column('kb_id', sa.String(36), nullable=True),
        sa.Column('parent_id', sa.String(36), nullable=True),
        sa.Column('retrieval_text', sa.Text, nullable=False),
        sa.Column('text_vector', Vector(1024), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_retrieval_index_doc_id', 'retrieval_index', ['doc_id'])
    op.create_index('ix_retrieval_index_session_id', 'retrieval_index', ['session_id'], postgresql_where=sa.text('session_id IS NOT NULL'))
    op.create_index('ix_retrieval_index_kb_id', 'retrieval_index', ['kb_id'], postgresql_where=sa.text('kb_id IS NOT NULL'))
    op.create_index('ix_retrieval_index_parent_id', 'retrieval_index', ['parent_id'])
    
    # 重新创建向量索引
    op.execute("""
        CREATE INDEX retrieval_vector_idx ON retrieval_index 
        USING ivfflat (text_vector vector_l2_ops)
    """)
