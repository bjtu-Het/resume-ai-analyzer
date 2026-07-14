"""FastAPI 应用入口（本地 uvicorn / 阿里云 FC 均可复用）。"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import build_health_data, router
from app.config import get_settings
from app.schemas.common import ApiResponse

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="AI 赋能的智能简历分析系统 API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health", response_model=ApiResponse)
async def health() -> ApiResponse:
    return ApiResponse(data=build_health_data().model_dump())


# 阿里云函数计算（ASGI）适配；本地可不依赖 mangum
try:
    from mangum import Mangum

    handler = Mangum(app, lifespan="off")
except ImportError:  # pragma: no cover
    handler = None
