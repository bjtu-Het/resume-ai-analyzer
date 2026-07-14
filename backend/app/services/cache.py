"""Redis 缓存（Docker / 自建），不可用时降级为进程内 LRU。"""

from __future__ import annotations

import json
import logging
from collections import OrderedDict
from typing import Any, Optional

from app.config import Settings

logger = logging.getLogger(__name__)


class _MemoryLRU:
    def __init__(self, capacity: int = 256) -> None:
        self.capacity = capacity
        self._data: OrderedDict[str, str] = OrderedDict()

    def get(self, key: str) -> Optional[str]:
        if key not in self._data:
            return None
        self._data.move_to_end(key)
        return self._data[key]

    def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self._data[key] = value
        self._data.move_to_end(key)
        if len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def ping(self) -> bool:
        return True


class CacheService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._redis = None
        self._memory = _MemoryLRU()
        self.backend = "memory"
        self._connect()

    def _connect(self) -> None:
        try:
            import redis

            client = redis.Redis(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                password=self.settings.redis_password or None,
                db=self.settings.redis_db,
                ssl=self.settings.redis_ssl,
                socket_connect_timeout=2,
                socket_timeout=2,
                decode_responses=True,
            )
            client.ping()
            self._redis = client
            self.backend = "redis"
            logger.info("Redis connected: %s:%s", self.settings.redis_host, self.settings.redis_port)
        except Exception as exc:  # noqa: BLE001
            self._redis = None
            self.backend = "memory"
            logger.warning("Redis unavailable, fallback to memory LRU: %s", exc)

    def get_json(self, key: str) -> Optional[dict[str, Any]]:
        raw = self._get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return None

    def set_json(self, key: str, value: dict[str, Any], ttl: int) -> None:
        self._set(key, json.dumps(value, ensure_ascii=False), ttl)

    def _get(self, key: str) -> Optional[str]:
        if self._redis is not None:
            try:
                return self._redis.get(key)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Redis get failed, use memory: %s", exc)
        return self._memory.get(key)

    def _set(self, key: str, value: str, ttl: int) -> None:
        if self._redis is not None:
            try:
                self._redis.setex(key, ttl, value)
                return
            except Exception as exc:  # noqa: BLE001
                logger.warning("Redis set failed, use memory: %s", exc)
        self._memory.set(key, value, ttl)

    def status(self) -> str:
        if self._redis is not None:
            try:
                self._redis.ping()
                return "redis"
            except Exception:  # noqa: BLE001
                return "redis_error"
        return "memory"
