"""Celery应用实例"""

from celery import Celery
from core.celery_config import CELERY_CONFIG

# 创建Celery应用
celery = Celery('tinyaisearch')

# 加载配置
celery.config_from_object(CELERY_CONFIG)

# 自动发现任务
celery.autodiscover_tasks(['celery_tasks'])

