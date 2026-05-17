import asyncio
import logging
from typing import Any
from pathlib import Path
from time import time
from msgspec.msgpack import (
    encode,
    decode
)
from utils.cache import diskstore

class db:
    path = Path("data/jsonb/x.jsonb")
    cache_path = Path("data/cache/y.jsonb")
    cache = None
    _conn = None
    _cache_conn = None

    @classmethod
    async def setup(cls, encryption_key: str):
        cls.path.parent.mkdir(parents=True, exist_ok=True)
        cls.cache = diskstore(filepath="db_cache.bin", limit=10000, mode="lru")
        cls.history_store = diskstore(filepath="webhook_history.bin", limit=50000, mode="lru")
        cls.persistence = diskstore(filepath="persistence.bin", limit=100000, mode="lru")
        logging.info("ok")
        logging.info("ok")

    @classmethod
    async def close(cls):
        pass

    @classmethod
    async def track_message(cls, msg_id: str, app_id: str, token: str, channel_id: int, user_id: int):
        if not cls.history_store: return
        exp = time() + 900.0
        payload = {
            "id": msg_id,
            "app_id": app_id,
            "token": token,
            "channel_id": channel_id,
            "user_id": user_id,
            "expires": exp
        }
        await cls.history_store.set(msg_id, payload, 900.0)

    @classmethod
    async def get_webhook_history(cls, channel_id: int, user_id: int) -> list[dict]:
        if not cls.history_store: return []
        now = time()
        all_msg = await cls.history_store.get_all(dict)
        return [
            m for m in all_msg
            if m["channel_id"] == channel_id 
            and m["user_id"] == user_id
            and m["expires"] > now
        ]

    @classmethod
    async def clear_webhook_history(cls, msg_ids: list[str]):
        if not cls.history_store: return
        for mid in msg_ids:
            await cls.history_store.delete(mid)

    @classmethod
    async def get(
        cls,
        user_id: int,
        type_ref: Any = dict,
        ttl: float | None = 60.0
    ) -> Any:
        if not cls.persistence:
            return type_ref() if callable(type_ref) else {}
        
        cache_key = f"u:{user_id}"
        if ttl is not None:
            cached = await cls.cache.get(cache_key, type_ref)
            if cached is not None:
                return cached

        data = await cls.persistence.get(str(user_id), type_ref)
        if data is None:
            return type_ref() if callable(type_ref) else {}

        if ttl is not None:
            await cls.cache.set(cache_key, data, ttl)
        return data

    @classmethod
    async def set(
        cls,
        user_id: int,
        data: Any
    ):
        if not cls.persistence:
            return
        await cls.cache.set(f"u:{user_id}", data, 60.0)
        await cls.persistence.set(str(user_id), data, 86400.0 * 365) # 1 year

    @classmethod
    async def delete(
        cls,
        user_id: int
    ):
        if not cls.persistence:
            return
        await cls.cache.delete(f"u:{user_id}")
        await cls.persistence.delete(str(user_id))
