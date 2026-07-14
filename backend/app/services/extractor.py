"""基于通义千问 Plus + 规则兜底的关键信息提取。"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from app.config import Settings
from app.schemas.resume import EducationItem, ProjectItem, ResumeProfile
from app.services.qwen_client import QwenClient
from app.services.rule_extractor import extract_by_rules, merge_profiles

logger = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "extract_profile.txt"


class ResumeExtractor:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.qwen = QwenClient(settings)
        self._system_prompt = _load_prompt()

    async def extract(self, cleaned_text: str) -> ResumeProfile:
        rules_profile = extract_by_rules(cleaned_text)
        if not cleaned_text.strip():
            return rules_profile

        if not self.qwen.enabled:
            logger.info("Qwen disabled, use rule extractor only")
            return rules_profile

        try:
            llm_profile = await self._extract_with_llm(cleaned_text)
            return merge_profiles(llm_profile, rules_profile)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM extract failed, fallback to rules: %s", exc)
            return rules_profile

    async def _extract_with_llm(self, cleaned_text: str) -> ResumeProfile:
        # 控制 token：过长文本截断
        text = cleaned_text if len(cleaned_text) <= 12000 else cleaned_text[:12000]
        messages = [
            {"role": "system", "content": self._system_prompt},
            {"role": "user", "content": f"简历文本如下：\n\n{text}"},
        ]
        try:
            data = await self.qwen.chat_json(messages, temperature=0.1)
        except Exception:
            # 兼容部分模型不支持 response_format
            content = await self.qwen.chat(messages, temperature=0.1)
            data = _parse_json_content(content)
        return _dict_to_profile(data)


def _load_prompt() -> str:
    if _PROMPT_PATH.exists():
        return _PROMPT_PATH.read_text(encoding="utf-8")
    return "请从简历文本提取结构化 JSON 字段。"


def _parse_json_content(content: str) -> dict[str, Any]:
    content = content.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
    if fence:
        content = fence.group(1).strip()
    return json.loads(content)


def _dict_to_profile(data: dict[str, Any]) -> ResumeProfile:
    education = []
    for item in data.get("education") or []:
        if isinstance(item, dict):
            education.append(EducationItem.model_validate(item))

    projects = []
    for item in data.get("projects") or []:
        if isinstance(item, dict):
            projects.append(ProjectItem.model_validate(item))

    skills = data.get("skills") or []
    if isinstance(skills, str):
        skills = [s.strip() for s in re.split(r"[,，/、;；]", skills) if s.strip()]

    work_years = data.get("work_years")
    if isinstance(work_years, str):
        m = re.search(r"(\d+(?:\.\d+)?)", work_years)
        work_years = float(m.group(1)) if m else None

    return ResumeProfile(
        name=str(data.get("name") or ""),
        phone=str(data.get("phone") or ""),
        email=str(data.get("email") or ""),
        address=str(data.get("address") or ""),
        job_intention=str(data.get("job_intention") or ""),
        expected_salary=str(data.get("expected_salary") or ""),
        work_years=work_years if work_years is None or isinstance(work_years, (int, float)) else None,
        education=education,
        projects=projects,
        skills=[str(s) for s in skills],
    )
