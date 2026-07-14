"""岗位匹配与评分：规则分 + 通义千问 Plus。"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.resume import JobKeywords, MatchResult, ResumeProfile
from app.services.qwen_client import QwenClient

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "match_score.txt"

# 常见技术/岗位关键词，用于规则抽 JD
_TECH_LEXICON = {
    "python", "java", "javascript", "typescript", "go", "golang", "rust", "c++", "c#",
    "fastapi", "django", "flask", "spring", "springboot", "redis", "mysql", "postgresql",
    "mongodb", "kafka", "rabbitmq", "docker", "kubernetes", "k8s", "linux", "git",
    "vue", "react", "angular", "nodejs", "node.js", "rpc", "grpc", "http", "rest",
    "微服务", "分布式", "高并发", "算法", "数据结构", "机器学习", "深度学习", "nlp",
    "llm", "pytorch", "tensorflow", "hadoop", "spark", "flink", "elasticsearch",
    "nginx", "ci/cd", "devops", "aws", "阿里云", "azure", "gcp", "html", "css",
    "sql", "nosql", "pandas", "numpy", "爬虫", "测试", "pytest", "unittest",
}

_YEARS_RE = re.compile(
    r"(?:(?:要求|具备|至少)?\s*)(\d+(?:\.\d+)?)\s*年(?:以上)?(?:工作|相关|开发)?经验",
    re.I,
)
_EDU_RE = re.compile(r"(博士|硕士|研究生|本科|大专|专科)")
_SPLIT = re.compile(r"[,，、/|；;\s]+")


class ResumeMatcher:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.qwen = QwenClient(settings)
        self._prompt = _load_prompt()
        self.rule_weight = 0.4
        self.ai_weight = 0.6

    async def extract_job_keywords(self, job_description: str) -> JobKeywords:
        rule_job = _extract_job_by_rules(job_description)
        if not self.qwen.enabled:
            return rule_job
        try:
            ai_job = await self._ai_job_and_score(
                job_description,
                profile=ResumeProfile(),
                cleaned_text="",
                score_only=False,
            )
            # 合并关键词
            keywords = _unique(rule_job.keywords + ai_job.get("keywords", []))
            skills = _unique(rule_job.required_skills + ai_job.get("required_skills", []))
            return JobKeywords(
                keywords=keywords or rule_job.keywords,
                summary=str(ai_job.get("summary") or rule_job.summary),
                required_skills=skills or rule_job.required_skills,
                required_years=ai_job.get("required_years")
                if ai_job.get("required_years") is not None
                else rule_job.required_years,
                required_education=str(
                    ai_job.get("required_education") or rule_job.required_education
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("AI JD extract failed: %s", exc)
            return rule_job

    async def match(
        self,
        profile: ResumeProfile,
        cleaned_text: str,
        job_description: str,
        job: JobKeywords | None = None,
    ) -> tuple[JobKeywords, MatchResult]:
        jd = (job_description or "").strip()
        if not jd:
            raise ValueError("job_description is empty")

        job = job or _extract_job_by_rules(jd)
        rule_match = _score_by_rules(profile, cleaned_text, job, jd)

        ai_payload: dict[str, Any] | None = None
        if self.qwen.enabled:
            try:
                ai_payload = await self._ai_job_and_score(
                    jd, profile=profile, cleaned_text=cleaned_text, score_only=True
                )
                # 用 AI 补强 JD
                job = JobKeywords(
                    keywords=_unique(job.keywords + (ai_payload.get("keywords") or [])),
                    summary=str(ai_payload.get("summary") or job.summary),
                    required_skills=_unique(
                        job.required_skills + (ai_payload.get("required_skills") or [])
                    ),
                    required_years=(
                        ai_payload.get("required_years")
                        if ai_payload.get("required_years") is not None
                        else job.required_years
                    ),
                    required_education=str(
                        ai_payload.get("required_education") or job.required_education
                    ),
                )
                # AI 补强后重算规则分（技能列表更全）
                rule_match = _score_by_rules(profile, cleaned_text, job, jd)
            except Exception as exc:  # noqa: BLE001
                logger.warning("AI match failed: %s", exc)
                ai_payload = None

        ai_score = None
        if ai_payload is not None:
            raw = ai_payload.get("ai_score", ai_payload.get("score"))
            try:
                ai_score = float(raw) if raw is not None else None
            except (TypeError, ValueError):
                ai_score = None

        if ai_score is not None:
            final = round(
                self.rule_weight * rule_match.score + self.ai_weight * ai_score,
                2,
            )
            reasons = _unique(rule_match.reasons + list(ai_payload.get("reasons") or []))
            missing = _unique(
                rule_match.missing_keywords + list(ai_payload.get("missing_keywords") or [])
            )
            skill_rate = _clamp01(
                max(
                    rule_match.skill_match_rate,
                    _safe_float(ai_payload.get("skill_match_rate"), rule_match.skill_match_rate),
                )
            )
            exp_rel = _clamp01(
                max(
                    rule_match.experience_relevance,
                    _safe_float(
                        ai_payload.get("experience_relevance"),
                        rule_match.experience_relevance,
                    ),
                )
            )
            return job, MatchResult(
                score=final,
                skill_match_rate=round(skill_rate, 4),
                experience_relevance=round(exp_rel, 4),
                ai_score=round(ai_score, 2),
                reasons=reasons[:8],
                missing_keywords=missing[:20],
            )

        return job, rule_match

    async def _ai_job_and_score(
        self,
        job_description: str,
        *,
        profile: ResumeProfile,
        cleaned_text: str,
        score_only: bool,
    ) -> dict[str, Any]:
        resume_brief = {
            "profile": profile.model_dump(),
            "resume_excerpt": (cleaned_text or "")[:8000],
        }
        user = (
            f"岗位 JD：\n{job_description[:6000]}\n\n"
            f"候选人信息：\n{json.dumps(resume_brief, ensure_ascii=False)}"
        )
        messages = [
            {"role": "system", "content": self._prompt},
            {"role": "user", "content": user},
        ]
        try:
            data = await self.qwen.chat_json(messages, temperature=0.2)
        except Exception:
            content = await self.qwen.chat(messages, temperature=0.2)
            data = _parse_json(content)
        return data if isinstance(data, dict) else {}


def _extract_job_by_rules(jd: str) -> JobKeywords:
    text = jd.strip()
    lower = text.lower()

    skills: list[str] = []
    for token in _TECH_LEXICON:
        if token.lower() in lower or token in text:
            skills.append(token)

    # 额外从「要求：xxx」片段切词
    for m in re.finditer(r"(?:技能|要求|加分|熟悉|掌握)[:：]([^\n]{2,120})", text):
        for part in _SPLIT.split(m.group(1)):
            part = part.strip().strip("。.;；")
            if 1 < len(part) <= 24:
                skills.append(part)

    skills = _unique(skills)
    years = None
    ym = _YEARS_RE.search(text)
    if ym:
        try:
            years = float(ym.group(1))
        except ValueError:
            years = None

    edu = ""
    em = _EDU_RE.search(text)
    if em:
        edu = em.group(1)

    summary = text.split("\n")[0].strip()[:80] if text else ""
    return JobKeywords(
        keywords=skills[:30],
        summary=summary,
        required_skills=skills[:20],
        required_years=years,
        required_education=edu,
    )


def _score_by_rules(
    profile: ResumeProfile,
    cleaned_text: str,
    job: JobKeywords,
    jd: str,
) -> MatchResult:
    corpus = " ".join(
        [
            cleaned_text or "",
            " ".join(profile.skills or []),
            profile.job_intention or "",
            " ".join(
                " ".join(p.tech_stack) + " " + p.description
                for p in (profile.projects or [])
            ),
        ]
    ).lower()

    required = job.required_skills or job.keywords
    required = _unique(required)
    hit: list[str] = []
    missing: list[str] = []
    for sk in required:
        if sk.lower() in corpus or sk in corpus:
            hit.append(sk)
        else:
            missing.append(sk)

    skill_rate = (len(hit) / len(required)) if required else 0.5

    # 经验相关度
    exp_rel = 0.5
    reasons: list[str] = []
    if job.required_years is not None:
        cand = profile.work_years
        if cand is None:
            # 文本里再猜一次
            m = re.search(r"(\d+(?:\.\d+)?)\s*年", cleaned_text or "")
            cand = float(m.group(1)) if m else None
        if cand is None:
            exp_rel = 0.4
            reasons.append("简历未明确工作年限，经验相关度按保守估计")
        elif cand >= job.required_years:
            exp_rel = min(1.0, 0.7 + 0.1 * (cand - job.required_years))
            reasons.append(f"工作年限 {cand} 年，满足岗位要求 {job.required_years} 年")
        else:
            exp_rel = max(0.1, cand / job.required_years * 0.7)
            reasons.append(f"工作年限 {cand} 年，低于要求 {job.required_years} 年")
    else:
        reasons.append("JD 未明确年限要求，经验相关度中性计分")

    # 学历粗评（小权重并入经验）
    if job.required_education:
        edu_text = " ".join(
            f"{e.degree}{e.school}" for e in (profile.education or [])
        ) + (cleaned_text or "")
        if job.required_education in edu_text:
            exp_rel = min(1.0, exp_rel + 0.1)
            reasons.append(f"学历信息匹配「{job.required_education}」")
        else:
            reasons.append(f"未明确看到「{job.required_education}」学历信息")

    if required:
        reasons.insert(0, f"技能命中 {len(hit)}/{len(required)}")

    # 综合分：技能 60% + 经验 40%
    score = round((0.6 * skill_rate + 0.4 * exp_rel) * 100, 2)
    return MatchResult(
        score=score,
        skill_match_rate=round(skill_rate, 4),
        experience_relevance=round(_clamp01(exp_rel), 4),
        ai_score=None,
        reasons=reasons[:8],
        missing_keywords=missing[:20],
    )


def _load_prompt() -> str:
    if _PROMPT_PATH.exists():
        return _PROMPT_PATH.read_text(encoding="utf-8")
    return "请输出岗位匹配 JSON。"


def _parse_json(content: str) -> dict[str, Any]:
    content = (content or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if fence:
        content = fence.group(1).strip()
    return json.loads(content)


def _unique(items: list[Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        s = str(x).strip()
        if not s:
            continue
        key = s.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _safe_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default
