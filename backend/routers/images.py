"""
图片代理 API 路由

提供从 MinIO 获取图片的代理接口，支持：
1. 知识库文档图片: /api/images/kbs/{kb_id}/images/{doc_id}/{hash}.jpg
2. 聊天上传图片:   /api/images/chat/{user_id}/{session_id}/{filename}
"""

import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from io import BytesIO

from services.storage import minio_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["图片代理"])


@router.get("/{path:path}")
async def get_image(path: str):
    """
    图片代理接口
    
    从 MinIO 获取图片并返回流响应，支持浏览器缓存。
    根据路径前缀自动选择对应的 MinIO bucket：
    - chat/ 前缀 → image_bucket（聊天图片）
    - 其他 → doc_bucket（文档图片）
    """
    try:
        if not minio_storage:
            logger.error("MinIO 存储服务未初始化")
            raise HTTPException(status_code=500, detail="存储服务未初始化")
        
        # 验证路径格式，防止路径遍历攻击
        if ".." in path or path.startswith("/"):
            logger.warning(f"检测到非法路径访问尝试: {path}")
            raise HTTPException(status_code=400, detail="非法路径")
        
        # 根据路径前缀选择 bucket
        if path.startswith("chat/"):
            bucket = minio_storage.image_bucket
            object_path = path[len("chat/"):]  # 去掉 "chat/" 前缀
        else:
            bucket = minio_storage.doc_bucket
            object_path = path
        
        # 从 MinIO 下载图片
        logger.info(f"获取图片: {bucket}/{object_path}")
        image_data = await minio_storage.download_file_as_bytes(
            storage_path=object_path,
            bucket=bucket
        )
        
        # 根据文件扩展名确定 MIME 类型
        mime_type = _get_mime_type(path)
        
        # 获取文件名用于 Content-Disposition
        filename = path.split("/")[-1] if "/" in path else path
        
        return StreamingResponse(
            BytesIO(image_data),
            media_type=mime_type,
            headers={
                "Cache-Control": "public, max-age=31536000",  # 1 年缓存
                "Content-Disposition": f"inline; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取图片失败: {path}, 错误: {e}")
        raise HTTPException(status_code=404, detail="图片不存在")


def _get_mime_type(path: str) -> str:
    """
    根据文件扩展名获取 MIME 类型
    
    Args:
        path: 文件路径
        
    Returns:
        MIME 类型字符串
    """
    path_lower = path.lower()
    
    if path_lower.endswith(".png"):
        return "image/png"
    elif path_lower.endswith(".gif"):
        return "image/gif"
    elif path_lower.endswith(".webp"):
        return "image/webp"
    elif path_lower.endswith(".svg"):
        return "image/svg+xml"
    elif path_lower.endswith(".bmp"):
        return "image/bmp"
    else:
        # 默认返回 JPEG
        return "image/jpeg"
