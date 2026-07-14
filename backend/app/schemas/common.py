from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Meta(BaseModel):
    request_id: str = ""
    cache_hit: bool = False


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None
    meta: Meta = Field(default_factory=Meta)


class HealthData(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    llm_model: str = "qwen-plus"
    redis: str = "unknown"


class ErrorDetail(BaseModel):
    detail: Any = None
