import logging
import os
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routers import files

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

import crud.database as db
from crud.config_manager import config
from routers.auth import router as auth_router
from routers.session import router as session_router
from routers.llm import router as llm_router
from routers.settings import router as settings_router
from routers.session_documents import router as session_docs_router
from routers.knowledge_base import router as kb_router
# 设置日志
dir_path = './logs'
file_name = 'app.log'
file_path = os.path.join(dir_path, file_name)
if not os.path.exists(dir_path):
    os.makedirs(dir_path)
if not os.path.exists(file_path):
    with open(file_path, 'w') as f:
        f.write('')

def setup_logging():
    logging.basicConfig(
        format='%(levelname)s (%(asctime)s): %(message)s (Line: %(lineno)d [%(filename)s])',
        datefmt='%Y-%m-%d %H:%M:%S',
        filename='./logs/app.log',
        encoding='utf-8',
        filemode='a',
        level=logging.INFO
    )

    # 添加控制台处理器以输出到终端
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.INFO)
    # console_formatter = logging.Formatter('%(levelname)s (%(asctime)s): %(message)s')
    # console_handler.setFormatter(console_formatter)
    # logging.getLogger().addHandler(console_handler)

    third_party_loggers = [
        'duckduckgo_search',
        'httpx',
        'requests',
        'urllib3',
        'openai',
        'langchain',
        'langchain_core',
        'baidusearch',
        'uvicorn',
        'fastapi',         
    ]

    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore
    db.create_tables()
    logger.info("数据库表已检查/创建完成。")
    config.initialize_config()
    logger.info("配置管理器已初始化。")
    yield

# 创建FastAPI应用
app = FastAPI(
    title="TinyAI Search API",
    description="TinyAI Search Backend API",
    version="2.0.0",
    lifespan=lifespan
)

# 请求监控中间件
@app.middleware("http")
async def request_monitoring_middleware(request: Request, call_next):
    start_time = datetime.now()
    client_ip = request.client.host if request.client else "unknown"
    path = request.url.path
    method = request.method
    
    response = await call_next(request)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    status_code = response.status_code
    success = status_code < 400
    
    logger.info(f"请求监控 - 时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}, 客户端IP: {client_ip}, 接口: {method} {path}, 状态码: {status_code}, 成功: {success}, 耗时: {duration:.2f}s")
    print(f"请求监控 - 时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}, 客户端IP: {client_ip}, 接口: {method} {path}, 状态码: {status_code}, 成功: {success}, 耗时: {duration:.2f}s")
    
    return response

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加资源监控中间件
# app.middleware("http")(resource_metrics_middleware)

# 注册路由
app.include_router(auth_router, tags=["登录认证"])
app.include_router(session_router, tags=["会话管理"])
app.include_router(llm_router, tags=["LLM调用"])
app.include_router(settings_router, tags=["配置信息填写与测试"])
app.include_router(files.router) 

app.include_router(session_docs_router, tags=["会话文档"])
app.include_router(kb_router, tags=["知识库"])

@app.get("/")
async def root():
    """根路径"""
    return {"message": "TinyAI Search API v2.0", "status": "running"}

if __name__ == '__main__':
    uvicorn.run("main:app", host='localhost', port=5001, reload=False, access_log=False)
