"""本地冒烟：解析样例 PDF（无需 Redis / 千问亦可跑通规则提取）。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.services.cache import CacheService
from app.services.extractor import ResumeExtractor
from app.services.resume_service import ResumeService


async def main() -> None:
    pdf_path = Path(__file__).parent / "fixtures" / "sample_resume.pdf"
    pdf_bytes = pdf_path.read_bytes()

    settings = Settings(qwen_api_key="", redis_host="127.0.0.1")
    cache = CacheService(settings)
    extractor = ResumeExtractor(settings)
    service = ResumeService(settings, cache, extractor)

    result, cache_hit = await service.parse_bytes(pdf_bytes)
    print("cache_hit:", cache_hit)
    print("pages:", result.page_count)
    print("email:", result.profile.email)
    print("phone:", result.profile.phone)
    print("skills:", result.profile.skills)
    print("cleaned preview:\n", result.cleaned_text[:400])

    result2, cache_hit2 = await service.parse_bytes(pdf_bytes)
    print("second cache_hit:", cache_hit2)
    assert cache_hit2 is True
    print("OK")


if __name__ == "__main__":
    asyncio.run(main())
