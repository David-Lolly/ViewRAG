"""知识库轨道PDF处理器"""

import logging
from typing import List, Dict, Any
from .base import BaseDocumentProcessor
from models.models import DocumentStatus, ChunkType

logger = logging.getLogger(__name__)


class KBPDFProcessor(BaseDocumentProcessor):
    """
    知识库轨道PDF处理器（简化版）
    
    处理流程：
    1. 高质量解析（外部微服务）
    2. 结构化分离（图/表/文）
    3. 两阶段切分（仅文本）
    4. LLM内容增强（图片描述、表格摘要）
    5. 向量化
    6. 批量入库（Chunk 表）
    """
    
    async def process(self):
        """执行知识库轨道的PDF处理流程"""
        import time
        from crud.document_crud import ChunkCRUD
        
        try:
            start_time = time.time()
            logger.info(f"开始处理 | doc_id={self.doc_id} | 轨道=知识库")
            
            # 获取文档信息
            document = self.crud.get_document_by_id(self.db, self.doc_id)
            if not document:
                logger.error(f"文档不存在: {self.doc_id}")
                return
            
            # ========== 阶段1: 高质量解析 ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | QUEUED -> PARSING")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.PARSING
            )
            
            md_text = await self.parser.parse_document(
                document.file_path,
                document.document_type.value,
                self.minio,
                track='kb',
                kb_id=document.kb_id,
                doc_id=self.doc_id
            )

            if not md_text:
                error_msg = "高质量解析失败，未提取到Markdown"
                self.crud.update_document_status(
                    self.db, self.doc_id, DocumentStatus.FAILED, error_msg
                )
                logger.error(f"[{self.doc_id}] {error_msg}")
                return
            
            self._log_status(
                "解析完成", 
                f"Markdown长度: {len(md_text)}"
            )
            
            # ========== 阶段2: 结构化分离 ==========
            self._log_status("开始结构化分离")
            
            # 使用MarkdownProcessor分离图、表、文
            units = self.md_processor.parse_markdown_to_units(md_text)
            
            figure_units = [u for u in units if u['type'] == 'figure_unit']
            table_units = [u for u in units if u['type'] == 'table_unit']
            paragraph_units = [u for u in units if u['type'] == 'paragraph']
            
            self._log_status(
                "结构化分离完成",
                f"图: {len(figure_units)}, 表: {len(table_units)}, 文: {len(paragraph_units)}"
            )
            
            # ========== 阶段3: 两阶段切分（仅文本） ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | PARSING -> CHUNKING")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.CHUNKING
            )
            
            text_chunks = []
            if paragraph_units:
                paragraph_text = paragraph_units[0]['content']
                text_chunks = self.chunker.chunk_text(paragraph_text)
            
            self._log_status(
                "切分完成",
                f"文本块数: {len(text_chunks)}"
            )
            
            # ========== 阶段4: 内容增强（LLM） ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | CHUNKING -> ENRICHING")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.ENRICHING
            )
            
            logger.info(f"开始内容增强 | 图={len(figure_units)} | 表={len(table_units)}")
            
            # 增强图片 - 返回纯文本描述（过滤无意义图片）
            figure_data = []
            skipped_figures = 0
            for fig in figure_units:
                description = await self.enhancer.enhance_figure(
                    fig['path'],
                    fig.get('caption', '')
                )
                # 跳过无意义图片（LLM返回空字符串表示应跳过）
                if not description:
                    skipped_figures += 1
                    continue
                figure_data.append({
                    'path': fig['path'],
                    'caption': fig.get('caption', ''),
                    'description': description
                })
            
            if skipped_figures > 0:
                logger.info(f"图片过滤 | 跳过无意义图片={skipped_figures} | 保留={len(figure_data)}")
            
            # 增强表格 - 返回纯文本摘要
            table_data = []
            for tbl in table_units:
                summary = await self.enhancer.enhance_table(
                    tbl['markdown'],
                    tbl.get('caption', '')
                )
                table_data.append({
                    'markdown': tbl['markdown'],
                    'caption': tbl.get('caption', ''),
                    'summary': summary
                })
            
            # TODO: 文档摘要功能暂时禁用，后续按需启用
            # # 生成文档摘要（用于文档路由）
            # all_retrieval_texts = []
            # for fig in figure_data:
            #     all_retrieval_texts.append(fig['description'])
            # for tbl in table_data:
            #     all_retrieval_texts.append(tbl['summary'])
            # for chunk in text_chunks:
            #     all_retrieval_texts.append(chunk['content'][:200])
            # 
            # doc_summary = await self.enhancer.summarize_document(
            #     all_retrieval_texts[:10],  # 取前10个用于生成摘要
            #     document.file_name
            # )
            # 
            # self._log_status(
            #     "内容增强完成",
            #     f"文档摘要长度: {len(doc_summary)}"
            # )
            
            self._log_status("内容增强完成")
            
            # ========== 阶段5: 向量化 ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | ENRICHING -> VECTORIZING")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.VECTORIZING
            )
            
            # 准备所有需要向量化的文本
            texts_to_embed = []
            chunk_mapping = []  # 记录每个文本对应的 Chunk 数据
            
            # TODO: 文档摘要向量化暂时禁用
            # # 1. 文档摘要（用于更新 Document 表）
            # texts_to_embed.append(doc_summary)
            # chunk_mapping.append({'type': 'doc_summary'})
            
            # 2. 图片 - retrieval_text 为 LLM 描述
            for fig in figure_data:
                texts_to_embed.append(fig['description'])
                chunk_mapping.append({
                    'type': 'IMAGE',
                    'content': fig['path'],
                    'retrieval_text': fig['description'],
                    'metadata': {'caption': fig['caption']}
                })
            
            # 3. 表格 - retrieval_text 为 LLM 摘要
            for tbl in table_data:
                texts_to_embed.append(tbl['summary'])
                chunk_mapping.append({
                    'type': 'TABLE',
                    'content': tbl['markdown'],
                    'retrieval_text': tbl['summary'],
                    'metadata': {'caption': tbl['caption']}
                })
            
            # 4. 文本块 - content 和 retrieval_text 相同
            for chunk in text_chunks:
                texts_to_embed.append(chunk['content'])
                chunk_mapping.append({
                    'type': 'TEXT',
                    'content': chunk['content'],
                    'retrieval_text': chunk['content'],
                    'metadata': {'heading_path': chunk.get('heading_path', [])}
                })
            
            # 批量向量化
            total_chunks = len(figure_data) + len(table_data) + len(text_chunks)
            logger.info(f"开始批量向量化 | 文本数={len(texts_to_embed)} (chunks={total_chunks})")
            vectors = self.vectorizer.get_embeddings(texts_to_embed)
            
            # ========== 阶段6: 入库 ==========
            logger.info(f"开始入库 | doc_id={self.doc_id}")
            
            # TODO: 文档摘要入库暂时禁用
            # # 提取文档摘要向量并更新 Document 表
            # doc_summary_vector = vectors[0] if vectors[0] else None
            # if doc_summary or doc_summary_vector:
            #     document.summary = doc_summary
            #     if doc_summary_vector:
            #         document.summary_vector = doc_summary_vector
            #     self.db.commit()
            
            # 构建 chunks_data
            chunks_data = []
            
            for i in range(len(vectors)):
                vector = vectors[i]
                mapping = chunk_mapping[i]
                
                if vector is None:
                    logger.warning(f"跳过向量化失败的单元: {i}")
                    continue
                
                if mapping['type'] == 'doc_summary':
                    continue
                
                chunks_data.append({
                    'chunk_type': mapping['type'],
                    'content': mapping['content'],
                    'retrieval_text': mapping['retrieval_text'],
                    'content_vector': vector,
                    'metadata': mapping.get('metadata')
                })
            
            # 批量保存到 Chunk 表
            success = ChunkCRUD.save_chunks(
                self.db,
                self.doc_id,
                document.kb_id,
                chunks_data
            )
            
            if not success:
                error_msg = "数据入库失败"
                self.crud.update_document_status(
                    self.db, self.doc_id, DocumentStatus.FAILED, error_msg
                )
                logger.error(f"[{self.doc_id}] {error_msg}")
                return
            
            logger.info(f"入库完成 | doc_id={self.doc_id} | Chunk数={len(chunks_data)}")
            
            # ========== 阶段7: 完成 ==========
            logger.info(f"状态变更 | doc_id={self.doc_id} | VECTORIZING -> COMPLETED")
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.COMPLETED
            )
            
            duration = time.time() - start_time
            logger.info(f"处理完成 | doc_id={self.doc_id} | 总耗时={duration:.2f}s | ✓")
            
        except Exception as e:
            error_msg = f"处理异常: {str(e)}"
            logger.error(f"处理失败 | doc_id={self.doc_id} | 错误={error_msg}", exc_info=True)
            self.crud.update_document_status(
                self.db, self.doc_id, DocumentStatus.FAILED, error_msg
            )

