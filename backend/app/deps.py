"""服务层依赖装配（懒加载，避免导入时连 Redis）。"""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings


@lru_cache
def get_cache_service():
    from app.services.cache import CacheService

    return CacheService(get_settings())


@lru_cache
def get_qwen_client():
    from app.services.qwen_client import QwenClient

    return QwenClient(get_settings())


@lru_cache
def get_extractor():
    from app.services.extractor import ResumeExtractor

    return ResumeExtractor(get_settings())


@lru_cache
def get_matcher():
    from app.services.matcher import ResumeMatcher

    return ResumeMatcher(get_settings())


@lru_cache
def get_resume_service():
    from app.services.resume_service import ResumeService

    return ResumeService(
        settings=get_settings(),
        cache=get_cache_service(),
        extractor=get_extractor(),
        matcher=get_matcher(),
    )


def reset_services() -> None:
    """测试或热重载时可清空单例。"""
    get_cache_service.cache_clear()
    get_qwen_client.cache_clear()
    get_extractor.cache_clear()
    get_matcher.cache_clear()
    get_resume_service.cache_clear()
