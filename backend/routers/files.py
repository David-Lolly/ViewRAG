"""
文件管理API路由

处理图片和文档的上传、查询、删除等操作
"""

import logging
import base64
from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from typing import Optional, List, Annotated
from services.storage import minio_storage
from crud import database as db
from services.session import SessionService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/v1/chat/send_message_with_images")
async def send_message_with_images(
    text: Annotated[str, Form()],
    images: Annotated[List[UploadFile], File()] = [],
    session_id: Annotated[str, Form()] = None,
    user_id: Annotated[str, Form()] = None
):
    """
    接收包含文本和多张图片的消息，并进行处理
    注意：images 参数是可选的，如果没有图片则为空列表
    """
    try:
        image_urls = []
        if images and minio_storage:
            for image_file in images:
                # 跳过空文件或无效文件
                if not image_file.filename or image_file.size == 0:
                    logger.debug(f"Skipped empty or invalid file")
                    continue
                    
                # 验证文件类型
                if image_file.content_type not in ["image/jpeg", "image/png", "image/webp", "image/gif"]:
                    logger.warning(f"Unsupported image type skipped: {image_file.filename} ({image_file.content_type})")
                    continue
                
                # V2性能优化：不再读取整个文件，直接传递UploadFile对象进行流式上传
                result = minio_storage.upload_image(
                    upload_file=image_file,  # 传递UploadFile对象
                    user_id=user_id,
                    session_id=session_id
                )
                image_urls.append(result['url'])
        
        # 将文本消息和图片URL列表存入数据库
        message_id = SessionService.add_user_message(
            session_id=session_id,
            content=text,
            image_urls=image_urls  # 传递一个URL列表
        )

        # TODO: 调用LLM服务进行处理
        # response = await llm_service.process_multimodal_message(text, image_urls)

        return {"message": "Success", "message_id": message_id, "text": text, "image_urls": image_urls}

    except Exception as e:
        logger.error(f"Error in send_message_with_images: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process message with images.")




@router.post("/api/files/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    user_id: str = Form(...)
):
    """
    上传文档文件（multipart上传）
    
    支持PDF、Word、TXT等格式
    
    Args:
        file: 上传的文件
        session_id: 会话ID
        user_id: 用户ID
    
    Returns:
        {
            'success': True,
            'file_id': str,
            'filename': str,
            'size': int,
            'url': str
        }
    """
    try:
        if not minio_storage:
            raise HTTPException(status_code=500, detail="MinIO存储服务未初始化")
        
        # 验证文件类型
        allowed_types = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'text/plain',
            'application/msword'
        ]
        
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file.content_type}。支持的类型: PDF, Word, TXT"
            )
        
        # 读取文件数据
        file_data = await file.read()
        
        # 验证文件大小（50MB限制）
        if len(file_data) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件大小不能超过50MB")
        
        # 上传到MinIO
        result = minio_storage.upload_document(
            file_data=file_data,
            user_id=user_id,
            session_id=session_id,
            filename=file.filename,
            content_type=file.content_type
        )
        
        # 保存文件记录到数据库
        file_record = {
            'file_id': result['file_id'],
            'session_id': session_id,
            'user_id': user_id,
            'file_type': 'document',
            'original_filename': file.filename,
            'storage_path': result['storage_path'],
            'file_size': str(result['file_size']),
            'mime_type': file.content_type,
            'minio_url': result['url'],
            'thumbnail_url': None,
            'message_id': None
        }
        
        # TODO: 保存到数据库
        # db.save_file_record(file_record)
        
        # TODO: 提取文本内容并生成向量
        # extract_and_vectorize_document(file_data, file_record)
        
        logger.info(f"文档上传成功: {result['file_id']}")
        
        return {
            'success': True,
            'file_id': result['file_id'],
            'filename': file.filename,
            'size': result['file_size'],
            'url': result['url']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传文档失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传文档失败: {str(e)}")


@router.get("/api/files/session/{session_id}")
async def get_session_files(session_id: str):
    """
    获取会话的所有文件
    
    Args:
        session_id: 会话ID
    
    Returns:
        {
            'success': True,
            'files': [...]
        }
    """
    try:
        # TODO: 从数据库查询
        # files = db.get_session_files(session_id)
        
        return {
            'success': True,
            'files': []
        }
        
    except Exception as e:
        logger.error(f"获取会话文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/files/{file_id}")
async def delete_file(file_id: str, user_id: str):
    """
    删除文件
    
    Args:
        file_id: 文件ID
        user_id: 用户ID（用于权限验证）
    
    Returns:
        {'success': True, 'message': '文件删除成功'}
    """
    try:
        if not minio_storage:
            raise HTTPException(status_code=500, detail="MinIO存储服务未初始化")
        
        # TODO: 从数据库查询文件信息
        # file_record = db.get_file_by_id(file_id)
        # 
        # if not file_record:
        #     raise HTTPException(status_code=404, detail="文件不存在")
        # 
        # # 验证权限
        # if file_record['user_id'] != user_id:
        #     raise HTTPException(status_code=403, detail="无权删除此文件")
        # 
        # # 删除MinIO中的文件
        # bucket = minio_storage.image_bucket if file_record['file_type'] == 'image' else minio_storage.doc_bucket
        # minio_storage.delete_file(bucket, file_record['storage_path'])
        # 
        # # 删除缩略图（如果有）
        # if file_record.get('thumbnail_path'):
        #     minio_storage.delete_file(minio_storage.thumb_bucket, file_record['thumbnail_path'])
        # 
        # # 删除数据库记录
        # db.delete_file_record(file_id)
        
        logger.info(f"文件删除成功: {file_id}")
        
        return {
            'success': True,
            'message': '文件删除成功'
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/storage/stats")
async def get_storage_stats(user_id: Optional[str] = None):
    """
    获取存储使用统计
    
    Args:
        user_id: 可选，指定用户ID
    
    Returns:
        存储统计信息
    """
    try:
        if not minio_storage:
            raise HTTPException(status_code=500, detail="MinIO存储服务未初始化")
        
        stats = minio_storage.get_storage_stats(user_id)
        
        return {
            'success': True,
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"获取存储统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
