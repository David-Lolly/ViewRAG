"""add_rag_tables_for_document_qa_and_kb

Revision ID: 5be004f351fa
Revises: 
Create Date: 2025-11-17 10:19:57.787158

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '5be004f351fa'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    # 1. 创建pgvector扩展（如果还没有创建）
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # 2. 创建枚举类型
    op.execute("""
        CREATE TYPE document_type AS ENUM (
            'PDF', 'DOCX', 'TXT', 'MARKDOWN', 'IMAGE', 'PPTX'
        )
    """)
    
    op.execute("""
        CREATE TYPE document_status AS ENUM (
            'QUEUED', 'PARSING', 'CHUNKING', 'ENRICHING', 'VECTORIZING', 'COMPLETED', 'FAILED'
        )
    """)
    
    op.execute("""
        CREATE TYPE unit_type AS ENUM (
            'TEXT_CHUNK', 'TEXT_SPLIT', 'IMAGE', 'TABLE'
        )
    """)
    
    # 3. 创建knowledge_bases表
    op.create_table(
        'knowledge_bases',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(255), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False)
    )
    op.create_index('ix_knowledge_bases_user_id', 'knowledge_bases', ['user_id'])
    
    # 4. 创建documents表
    op.create_table(
        'documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('session_id', sa.String(255), sa.ForeignKey('sessions.session_id', ondelete='CASCADE'), nullable=True),
        sa.Column('kb_id', sa.String(36), sa.ForeignKey('knowledge_bases.id', ondelete='CASCADE'), nullable=True),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.Text, nullable=False),
        sa.Column('document_type', sa.Enum('PDF', 'DOCX', 'TXT', 'MARKDOWN', 'IMAGE', 'PPTX', name='document_type'), nullable=False),
        sa.Column('status', sa.Enum('QUEUED', 'PARSING', 'CHUNKING', 'ENRICHING', 'VECTORIZING', 'COMPLETED', 'FAILED', name='document_status'), nullable=False, server_default='QUEUED'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('summary_vector', Vector(1024), nullable=True),
        sa.CheckConstraint(
            '(session_id IS NOT NULL AND kb_id IS NULL) OR (session_id IS NULL AND kb_id IS NOT NULL)',
            name='chk_document_owner'
        )
    )
    op.create_index('ix_documents_session_id', 'documents', ['session_id'])
    op.create_index('ix_documents_kb_id', 'documents', ['kb_id'])
    op.execute("""
        CREATE INDEX doc_summary_vector_idx ON documents 
        USING ivfflat (summary_vector vector_l2_ops) 
        WHERE kb_id IS NOT NULL
    """)
    
    # 5. 创建content_units表
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
    
    # 6. 创建retrieval_index表
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
    
    # 核心向量索引（使用IVFFlat）
    op.execute("""
        CREATE INDEX retrieval_vector_idx ON retrieval_index 
        USING ivfflat (text_vector vector_l2_ops)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    
    # 删除表（按依赖顺序逆序删除）
    op.drop_table('retrieval_index')
    op.drop_table('content_units')
    op.drop_table('documents')
    op.drop_table('knowledge_bases')
    
    # 删除枚举类型
    op.execute('DROP TYPE IF EXISTS unit_type')
    op.execute('DROP TYPE IF EXISTS document_status')
    op.execute('DROP TYPE IF EXISTS document_type')
