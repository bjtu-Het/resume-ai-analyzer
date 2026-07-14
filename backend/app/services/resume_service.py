"""简历解析 / 匹配编排服务。"""

from __future__ import annotations

import hashlib
import logging

from fastapi import UploadFile

from app.config import Settings
from app.schemas.resume import (
    AnalyzeResult,
    JobKeywords,
    MatchResult,
    ParseResult,
    ResumeProfile,
)
from app.services.cache import CacheService
from app.services.extractor import ResumeExtractor
from app.services.matcher import ResumeMatcher
from app.services.pdf_parser import PdfParseError, extract_text_from_pdf
from app.services.text_cleaner import clean_resume_text

logger = logging.getLogger(__name__)

PARSE_CACHE = "parse:v1"
MATCH_CACHE = "match:v1"


class ResumeServiceError(Exception):
    def __init__(self, http_status: int, code: int, message: str) -> None:
        self.http_status = http_status
        self.code = code
        self.message = message
        super().__init__(message)


class ResumeService:
    def __init__(
        self,
        settings: Settings,
        cache: CacheService,
        extractor: ResumeExtractor,
        matcher: ResumeMatcher,
    ) -> None:
        self.settings = settings
        self.cache = cache
        self.extractor = extractor
        self.matcher = matcher

    async def read_pdf_upload(self, file: UploadFile) -> tuple[bytes, str]:
        filename = (file.filename or "").lower()
        content_type = (file.content_type or "").lower()
        if not filename.endswith(".pdf") and "pdf" not in content_type:
            raise ResumeServiceError(400, 4001, "仅支持 PDF 格式简历")

        pdf_bytes = await file.read()
        if not pdf_bytes:
            raise ResumeServiceError(400, 4002, "上传文件为空")
        if len(pdf_bytes) > self.settings.max_upload_bytes:
            raise ResumeServiceError(
                400,
                4003,
                f"文件过大，限制 {self.settings.max_upload_mb}MB",
            )
        resume_id = hashlib.sha256(pdf_bytes).hexdigest()
        return pdf_bytes, resume_id

    async def parse_bytes(
        self, pdf_bytes: bytes, resume_id: str | None = None
    ) -> tuple[ParseResult, bool]:
        resume_id = resume_id or hashlib.sha256(pdf_bytes).hexdigest()
        cache_key = f"{PARSE_CACHE}:{resume_id}"

        cached = self.cache.get_json(cache_key)
        if cached:
            try:
                return ParseResult.model_validate(cached), True
            except Exception:  # noqa: BLE001
                logger.warning("invalid parse cache for %s", resume_id)

        try:
            raw_text, page_count = extract_text_from_pdf(pdf_bytes)
        except PdfParseError as exc:
            code = 4004 if exc.code == "PDF_TEXT_EMPTY" else 4005
            raise ResumeServiceError(400, code, exc.message) from exc

        cleaned = clean_resume_text(raw_text)
        profile = await self.extractor.extract(cleaned)

        result = ParseResult(
            resume_id=resume_id,
            page_count=page_count,
            raw_text=raw_text,
            cleaned_text=cleaned,
            profile=profile,
        )
        self.cache.set_json(
            cache_key,
            result.model_dump(),
            self.settings.cache_ttl_parse,
        )
        return result, False

    async def parse_upload(self, file: UploadFile) -> tuple[ParseResult, bool]:
        pdf_bytes, resume_id = await self.read_pdf_upload(file)
        return await self.parse_bytes(pdf_bytes, resume_id)

    async def match_text(
        self,
        *,
        job_description: str,
        cleaned_text: str = "",
        profile: ResumeProfile | None = None,
        resume_id: str = "",
    ) -> tuple[JobKeywords, MatchResult, bool]:
        jd = (job_description or "").strip()
        if not jd:
            raise ResumeServiceError(400, 4006, "岗位需求描述不能为空")

        profile = profile or ResumeProfile()
        text = cleaned_text or ""
        if not text and not any(
            [profile.skills, profile.name, profile.job_intention, profile.projects]
        ):
            raise ResumeServiceError(400, 4007, "请提供 resume_text 或 profile")

        rid = resume_id or hashlib.sha256(text.encode("utf-8")).hexdigest()
        jd_hash = hashlib.sha256(jd.encode("utf-8")).hexdigest()
        cache_key = f"{MATCH_CACHE}:{rid}:{jd_hash}"

        cached = self.cache.get_json(cache_key)
        if cached:
            try:
                job = JobKeywords.model_validate(cached.get("job") or {})
                match = MatchResult.model_validate(cached.get("match") or {})
                return job, match, True
            except Exception:  # noqa: BLE001
                logger.warning("invalid match cache for %s", cache_key)

        job, match = await self.matcher.match(profile, text, jd)
        self.cache.set_json(
            cache_key,
            {"job": job.model_dump(), "match": match.model_dump()},
            self.settings.cache_ttl_match,
        )
        return job, match, False

    async def analyze_upload(
        self, file: UploadFile, job_description: str
    ) -> tuple[AnalyzeResult, bool]:
        jd = (job_description or "").strip()
        if not jd:
            raise ResumeServiceError(400, 4006, "岗位需求描述不能为空")

        pdf_bytes, resume_id = await self.read_pdf_upload(file)
        parsed, parse_hit = await self.parse_bytes(pdf_bytes, resume_id)
        job, match, match_hit = await self.match_text(
            job_description=jd,
            cleaned_text=parsed.cleaned_text,
            profile=parsed.profile,
            resume_id=parsed.resume_id,
        )
        result = AnalyzeResult(
            resume_id=parsed.resume_id,
            page_count=parsed.page_count,
            raw_text=parsed.raw_text,
            cleaned_text=parsed.cleaned_text,
            profile=parsed.profile,
            job=job,
            match=match,
        )
        return result, parse_hit and match_hit
