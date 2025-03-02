from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import os

from app.core.config import settings
from app.core.middleware import verify_api_key_middleware
from app.core.logger import logger
from app.api.v1 import chat, files, models
from app.models.manager import model_manager

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specific domains should be set
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add API key validation middleware
app.middleware("http")(verify_api_key_middleware)

# Register routes
app.include_router(
    chat.router,
    prefix=settings.API_V1_STR,
    tags=["chat"]
)

app.include_router(
    files.router,
    prefix=settings.API_V1_STR,
    tags=["files"]
)

app.include_router(
    models.router,
    prefix=settings.API_V1_STR,
    tags=["models"]
)

# 添加请求处理时间中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )

@app.on_event("startup")
async def startup_event():
    """
    Application startup handler.
    """
    logger.info(f"Starting {settings.APP_NAME}")
    logger.info(f"Debug mode: {settings.DEBUG}")
    logger.info(f"API Key validation: {'enabled' if settings.ENABLE_API_KEY else 'disabled'}")
    
    # Auto-discover and load models
    model_manager.discover_models()
    logger.info(f"Loaded models: {list(model_manager.list_models().keys())}")

    # 确保模型目录存在
    os.makedirs(settings.MODELS_DIR, exist_ok=True)
    
    # 将所有模型描述添加到向量存储
    model_manager.add_models_to_vector_store()
    logger.info("Model descriptions added to vector store")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown handler.
    """
    logger.info(f"Shutting down {settings.APP_NAME}")

@app.get("/")
async def root():
    """
    Root route, returns application information.
    """
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "description": "A flexible interface management system based on Model Context Protocol (MCP)",
        "models": list(model_manager.list_models().keys())
    } 