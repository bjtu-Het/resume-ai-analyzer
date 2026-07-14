"""通义千问 Plus 客户端（OpenAI 兼容模式）。"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.config import Settings


class QwenClient:
    """DashScope 兼容模式：POST /chat/completions，模型 qwen-plus。"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._base = settings.qwen_base_url.rstrip("/")
        self._model = settings.qwen_model
        self._api_key = settings.qwen_api_key

    @property
    def enabled(self) -> bool:
        return bool(self._api_key) and not self._api_key.startswith("sk-xxxx")

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        response_format_json: bool = False,
    ) -> str:
        if not self.enabled:
            raise RuntimeError("QWEN_API_KEY is not configured")

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format_json:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self._base}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
    ) -> dict[str, Any]:
        content = await self.chat(
            messages,
            temperature=temperature,
            response_format_json=True,
        )
        return _loads_json(content)


def _loads_json(content: str) -> dict[str, Any]:
    content = (content or "").strip()
    if content.startswith("```"):
        lines = content.split("\n")
        # 去掉首尾 fence
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()
    return json.loads(content)
