"""PDF 解析：pdfplumber 主路径，pypdf 兜底。"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)


class PdfParseError(Exception):
    """PDF 无法解析或无可用文本。"""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def extract_text_from_pdf(pdf_bytes: bytes) -> tuple[str, int]:
    """从 PDF 字节提取文本。返回 (原始文本, 页数)。"""
    if not pdf_bytes:
        raise PdfParseError("INVALID_PDF", "空文件，无法解析")

    text, pages = _extract_with_pdfplumber(pdf_bytes)
    if not (text or "").strip():
        text, pages = _extract_with_pypdf(pdf_bytes)

    if not (text or "").strip():
        raise PdfParseError(
            "PDF_TEXT_EMPTY",
            "未能从 PDF 提取到文本，可能是扫描件/图片简历（暂不支持 OCR）",
        )
    return text, pages


def _extract_with_pdfplumber(pdf_bytes: bytes) -> tuple[str, int]:
    try:
        import pdfplumber
    except ImportError:
        logger.warning("pdfplumber not installed")
        return "", 0

    parts: list[str] = []
    page_count = 0
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    parts.append(page_text.strip())
    except Exception as exc:  # noqa: BLE001
        logger.warning("pdfplumber failed: %s", exc)
        return "", 0
    return "\n\n".join(parts), page_count


def _extract_with_pypdf(pdf_bytes: bytes) -> tuple[str, int]:
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("pypdf not installed")
        return "", 0

    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        page_count = len(reader.pages)
        parts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                parts.append(page_text.strip())
        return "\n\n".join(parts), page_count
    except Exception as exc:  # noqa: BLE001
        logger.warning("pypdf failed: %s", exc)
        return "", 0
