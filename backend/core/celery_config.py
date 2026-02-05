"""Celery配置"""

CELERY_CONFIG = {
    # Broker和Backend
    'broker_url': 'redis://localhost:6379/0',
    'result_backend': 'redis://localhost:6379/0',
    
    # 序列化
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    
    # 时区
    'timezone': 'Asia/Shanghai',
    'enable_utc': True,
    
    # 任务路由（不同轨道使用不同队列）
    'task_routes': {
        'backend.celery_tasks.document_processing.process_session_document': {
            'queue': 'session_tasks'
        },
        'backend.celery_tasks.document_processing.process_kb_document': {
            'queue': 'kb_tasks'
        },
    },
    
    # 任务执行限制
    'task_time_limit': 3600,  # 1小时硬限制
    'task_soft_time_limit': 3300,  # 55分钟软限制
    
    # Worker配置
    'worker_prefetch_multiplier': 1,  # 一次只取一个任务
    'worker_max_tasks_per_child': 100,  # Worker处理100个任务后重启
    
    # 结果过期时间
    'result_expires': 86400,  # 24小时
}






