"""规则引擎：邮箱/手机/姓名等兜底提取。"""

from __future__ import annotations

import re

from app.schemas.resume import ResumeProfile

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(
    r"(?:(?:\+?86[\s-]?)?1[3-9]\d[\s-]?\d{4}[\s-]?\d{4})"
    r"|(?:0\d{2,3}[\s-]?\d{7,8})"
)
YEARS_RE = re.compile(r"(?:工作年限|从业|经验)[:：\s]*(\d+(?:\.\d+)?)\s*年?")
YEARS_RE2 = re.compile(r"(\d+(?:\.\d+)?)\s*年(?:以上)?(?:工作|开发|相关)?经验")
SALARY_RE = re.compile(
    r"(?:期望薪资|期望月薪|薪资要求|薪资)[:：\s]*([^\n，,。；;]{2,20})"
)
INTENTION_RE = re.compile(
    r"(?:求职意向|目标岗位|应聘岗位|期望职位|意向岗位|Job Intention|Objective)"
    r"[:：\s]*([^\n]{2,40})",
    re.I,
)
ADDRESS_HINT = re.compile(
    r"(?:现居|居住地|地址|所在地|籍贯)[:：\s]*([^\n]{2,40})"
)
NAME_LABEL = re.compile(r"(?:姓名|名字)[:：\s]*([^\n\s]{1,20})")

SKILL_SPLIT = re.compile(r"[,，/、|；;]\s*")


def extract_by_rules(text: str) -> ResumeProfile:
    profile = ResumeProfile()
    if not text:
        return profile

    email = EMAIL_RE.search(text)
    if email:
        profile.email = email.group(0)

    phone = PHONE_RE.search(text.replace(" ", ""))
    if phone:
        profile.phone = re.sub(r"[\s-]", "", phone.group(0))

    named = NAME_LABEL.search(text)
    if named:
        profile.name = named.group(1).strip()
    else:
        profile.name = _guess_name(text)

    addr = ADDRESS_HINT.search(text)
    if addr:
        profile.address = addr.group(1).strip()

    intention = INTENTION_RE.search(text)
    if intention:
        profile.job_intention = intention.group(1).strip()

    salary = SALARY_RE.search(text)
    if salary:
        profile.expected_salary = salary.group(1).strip()

    years = YEARS_RE.search(text) or YEARS_RE2.search(text)
    if years:
        try:
            profile.work_years = float(years.group(1))
        except ValueError:
            pass

    profile.skills = _guess_skills(text)
    return profile


def _guess_name(text: str) -> str:
    # 取前几行较短中文片段作为姓名候选
    for line in text.split("\n")[:8]:
        line = line.strip()
        if not line or "@" in line or re.search(r"\d{5,}", line):
            continue
        # 纯中文 2-4 字
        if re.fullmatch(r"[\u4e00-\u9fff]{2,4}", line):
            return line
        # 「姓名 xxx」已在外部处理；「张三 / Python」类
        m = re.match(r"^([\u4e00-\u9fff]{2,4})\s*[/|｜]", line)
        if m:
            return m.group(1)
    return ""


def _guess_skills(text: str) -> list[str]:
    markers = ("技能", "专业技能", "技术栈", "掌握", "擅长", "Skills", "Skill", "TECH")
    lines = text.split("\n")
    collected: list[str] = []
    for i, line in enumerate(lines):
        if any(m.lower() in line.lower() if m.isascii() else m in line for m in markers):
            chunk = line
            # 合并后续若干非空行
            for j in range(i + 1, min(i + 4, len(lines))):
                if not lines[j].strip():
                    break
                if any(h in lines[j] for h in ("教育", "工作经历", "项目经历", "自我评价", "Education", "Experience")):
                    break
                chunk += " " + lines[j]
            parts = SKILL_SPLIT.split(re.sub(r"(?i)^.*?skills\s*[:：]\s*", "", chunk, count=1))
            if parts == [chunk] or (len(parts) == 1 and ":" not in chunk and "：" not in chunk):
                parts = SKILL_SPLIT.split(re.sub(r"^[^:：]*[:：]", "", chunk))
            for p in parts:
                p = p.strip(" ·•-—\t")
                if re.match(r"(?i)^skills?$", p):
                    continue
                if 1 < len(p) <= 24:
                    collected.append(p)
            break
    # 去重保序
    seen: set[str] = set()
    result: list[str] = []
    for s in collected:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result[:30]


def merge_profiles(primary: ResumeProfile, fallback: ResumeProfile) -> ResumeProfile:
    """primary 优先，空字段用 fallback 补齐。"""
    data = primary.model_dump()
    fb = fallback.model_dump()
    for key, value in data.items():
        if value in ("", None, [], {}):
            data[key] = fb.get(key, value)
        elif key == "work_years" and value is None:
            data[key] = fb.get(key)
    return ResumeProfile.model_validate(data)
