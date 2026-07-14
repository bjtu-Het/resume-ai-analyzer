"""REST 路由。"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from app import __version__
from app.config import get_settings
from app.deps import get_cache_service, get_resume_service
from app.schemas.common import ApiResponse, HealthData, Meta
from app.schemas.resume import (
    AnalyzeResult,
    MatchRequest,
    MatchResult,
    ParseResult,
    ResumeProfile,
)
from app.services.resume_service import ResumeServiceError

router = APIRouter(prefix="/api/v1")


def _meta(cache_hit: bool = False) -> Meta:
    return Meta(request_id=uuid.uuid4().hex, cache_hit=cache_hit)


def _error_response(exc: ResumeServiceError) -> JSONResponse:
    body = ApiResponse[None](
        code=exc.code,
        message=exc.message,
        data=None,
        meta=_meta(),
    )
    return JSONResponse(status_code=exc.http_status, content=body.model_dump())


@router.post("/resumes/parse", response_model=ApiResponse[ParseResult])
async def parse_resume(file: UploadFile = File(...)):
    """上传单个 PDF，解析并提取关键信息。"""
    service = get_resume_service()
    try:
        result, cache_hit = await service.parse_upload(file)
    except ResumeServiceError as exc:
        return _error_response(exc)
    return ApiResponse(data=result, meta=_meta(cache_hit))


@router.post("/resumes/analyze", response_model=ApiResponse[AnalyzeResult])
async def analyze_resume(
    file: UploadFile = File(...),
    job_description: str = Form(...),
):
    """一站式：解析 + 提取 + 与岗位 JD 匹配评分。"""
    service = get_resume_service()
    try:
        result, cache_hit = await service.analyze_upload(file, job_description)
    except ResumeServiceError as exc:
        return _error_response(exc)
    return ApiResponse(data=result, meta=_meta(cache_hit))


@router.post("/match", response_model=ApiResponse[MatchResult])
async def match_resume(body: MatchRequest):
    """仅对已有简历文本/结构化信息与 JD 打分。"""
    service = get_resume_service()
    try:
        _job, match, cache_hit = await service.match_text(
            job_description=body.job_description,
            cleaned_text=body.resume_text or "",
            profile=body.profile or ResumeProfile(),
            resume_id=body.resume_id or "",
        )
    except ResumeServiceError as exc:
        return _error_response(exc)
    return ApiResponse(data=match, meta=_meta(cache_hit))


def build_health_data() -> HealthData:
    settings = get_settings()
    try:
        redis_status = get_cache_service().status()
    except Exception:  # noqa: BLE001
        redis_status = "unknown"
    return HealthData(
        status="ok",
        version=__version__,
        llm_model=settings.qwen_model,
        redis=redis_status,
    )
