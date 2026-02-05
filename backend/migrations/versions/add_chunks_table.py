"""add_chunks_table

Revision ID: add_chunks_table
Revises: 5be004f351fa
Create Date: 2026-01-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'add_chunks_table'
down_revision: Union[str, Sequence[str], None] = '5be004f351fa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - 创建 chunks 表"""
    
    # 1. 创建 chunk_type 枚举类型
    op.execute("""
        CREATE TYPE chunk_type AS ENUM ('TEXT', 'IMAGE', 'TABLE')
    """)
    
    # 2. 创建 chunks 表
    op.create_table(
        'chunks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('doc_id', sa.String(36), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('kb_id', sa.String(36), nullable=True),
        sa.Column('chunk_type', sa.Enum('TEXT', 'IMAGE', 'TABLE', name='chunk_type'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('retrieval_text', sa.Text, nullable=False),
        sa.Column('content_vector', Vector(1024), nullable=False),
        sa.Column('chunk_metadata', sa.Text, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    
    # 3. 创建索引
    op.create_index('ix_chunks_doc_id', 'chunks', ['doc_id'])
    op.create_index('ix_chunks_kb_id', 'chunks', ['kb_id'], postgresql_where=sa.text('kb_id IS NOT NULL'))
    
    # 4. 创建向量索引（使用 IVFFlat）
    op.execute("""
        CREATE INDEX chunks_vector_idx ON chunks 
        USING ivfflat (content_vector vector_l2_ops)
    """)


def downgrade() -> None:
    """Downgrade schema - 删除 chunks 表"""
    
    # 删除表
    op.drop_table('chunks')
    
    # 删除枚举类型
    op.execute('DROP TYPE IF EXISTS chunk_type')
