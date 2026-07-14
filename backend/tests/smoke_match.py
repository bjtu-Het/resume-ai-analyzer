"""匹配评分冒烟（无需千问亦可跑通规则分）。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import Settings
from app.schemas.resume import ResumeProfile
from app.services.cache import CacheService
from app.services.extractor import ResumeExtractor
from app.services.matcher import ResumeMatcher
from app.services.resume_service import ResumeService


async def main() -> None:
    settings = Settings(qwen_api_key="", redis_host="127.0.0.1")
    service = ResumeService(
        settings,
        CacheService(settings),
        ResumeExtractor(settings),
        ResumeMatcher(settings),
    )

    profile = ResumeProfile(
        name="张三",
        skills=["Python", "FastAPI", "Redis"],
        work_years=3,
        job_intention="后端开发",
    )
    text = "熟悉 Python FastAPI Redis MySQL，3年后端开发经验"
    jd = "招聘 Python 后端工程师，要求熟悉 FastAPI、Redis，具备 2 年以上工作经验，本科。"

    job, match, hit1 = await service.match_text(
        job_description=jd,
        cleaned_text=text,
        profile=profile,
        resume_id="smoke-candidate",
    )
    print("job keywords:", job.keywords)
    print("score:", match.score)
    print("skill_match_rate:", match.skill_match_rate)
    print("experience_relevance:", match.experience_relevance)
    print("reasons:", match.reasons)
    print("missing:", match.missing_keywords)

    _, _, hit2 = await service.match_text(
        job_description=jd,
        cleaned_text=text,
        profile=profile,
        resume_id="smoke-candidate",
    )
    print("cache_hit:", hit1, "->", hit2)
    assert hit2 is True
    assert match.score > 0
    print("OK")


if __name__ == "__main__":
    asyncio.run(main())
