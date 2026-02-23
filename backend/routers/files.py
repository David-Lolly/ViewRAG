"""
文件管理API路由

处理图片上传等操作
"""

import json
import logging
from fastapi import APIRouter, HTTPException, Form, UploadFile, File
from typing import List, Annotated, Optional
from services.storage import minio_storage
from services.session import SessionService
from crud.document_crud import DocumentCRUD
from crud.database import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/v1/chat/send_message_with_images")
async def send_message_with_images(
    text: Annotated[str, Form()],
    images: Annotated[List[UploadFile], File()] = [],
    session_id: Annotated[str, Form()] = None,
    user_id: Annotated[str, Form()] = None,
    doc_ids: Annotated[Optional[str], Form()] = None  # JSON字符串格式的文档ID列表
):
    """
    接收包含文本和多张图片的消息，并进行处理
    注意：images 参数是可选的，如果没有图片则为空列表
    doc_ids: 可选，JSON字符串格式的文档ID列表，用于绑定文档到该消息
    """
    try:
        image_urls = []
        if images and minio_storage:
            for image_file in images:
                # 跳过空文件或无效文件
                if not image_file.filename or image_file.size == 0:
                    logger.debug("Skipped empty or invalid file")
                    continue

                # 验证文件类型
                if image_file.content_type not in ["image/jpeg", "image/png", "image/webp", "image/gif"]:
                    logger.warning(f"Unsupported image type skipped: {image_file.filename} ({image_file.content_type})")
                    continue

                # 流式上传到 MinIO
                result = minio_storage.upload_image(
                    upload_file=image_file,
                    user_id=user_id,
                    session_id=session_id
                )
                image_urls.append(result['url'])

        # 将文本消息和图片URL列表存入数据库（存储原始 MinIO URL）
        message_id = SessionService.add_user_message(
            session_id=session_id,
            content=text,
            image_urls=image_urls
        )

        # 如果有文档ID，绑定文档到该消息
        if doc_ids and message_id and session_id:
            try:
                doc_id_list = json.loads(doc_ids)
                if isinstance(doc_id_list, list) and len(doc_id_list) > 0:
                    with SessionLocal() as db_session:
                        DocumentCRUD.bind_documents_to_message(
                            session=db_session,
                            doc_ids=doc_id_list,
                            message_id=message_id,
                            session_id=session_id
                        )
                    logger.info(f"已绑定 {len(doc_id_list)} 个文档到消息 {message_id}")
            except json.JSONDecodeError:
                logger.warning(f"doc_ids 解析失败: {doc_ids}")

        # 返回给前端的 URL 转为代理路径
        proxy_urls = []
        if minio_storage:
            for url in image_urls:
                proxy_path = minio_storage.minio_url_to_proxy_path(url)
                proxy_urls.append(proxy_path if proxy_path else url)
        else:
            proxy_urls = image_urls

        return {"message": "Success", "message_id": message_id, "text": text, "image_urls": proxy_urls}

    except Exception as e:
        logger.error(f"Error in send_message_with_images: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to process message with images.")
