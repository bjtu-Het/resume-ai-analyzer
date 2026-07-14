"""简历文本清洗。"""

from __future__ import annotations

import re
import unicodedata

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_MULTI_SPACE = re.compile(r"[ \t\f\v]+")
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_SOFT_HYPHEN = re.compile(r"(\w)-\n(\w)")


def clean_resume_text(raw_text: str) -> str:
    """清洗简历文本：去控制字符、冗余空白，保留合理分段。"""
    if not raw_text:
        return ""

    text = unicodedata.normalize("NFKC", raw_text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CTRL.sub("", text)
    text = _SOFT_HYPHEN.sub(r"\1\2", text)

    lines: list[str] = []
    for line in text.split("\n"):
        line = _MULTI_SPACE.sub(" ", line).strip()
        lines.append(line)

    # 去掉连续空行，并过滤超短重复页眉页脚（简单启发式）
    lines = _drop_repeated_headers(lines)

    cleaned = "\n".join(lines)
    cleaned = _MULTI_NEWLINE.sub("\n\n", cleaned)
    return cleaned.strip()


def _drop_repeated_headers(lines: list[str]) -> list[str]:
    """去掉出现次数过高的短行（常见页眉/页脚）。"""
    from collections import Counter

    short = [ln for ln in lines if 0 < len(ln) <= 20]
    counts = Counter(short)
    noise = {ln for ln, c in counts.items() if c >= 3}

    result: list[str] = []
    prev_blank = False
    for ln in lines:
        if ln in noise:
            continue
        if not ln:
            if prev_blank:
                continue
            prev_blank = True
            result.append("")
            continue
        prev_blank = False
        result.append(ln)
    return result
