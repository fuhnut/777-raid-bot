import aiolibsql
import asyncio
import logging
from typing import Any
from pathlib import Path
from msgspec.json import encode, decode
from utils.cache import diskstore

class db:
    path = Path("data/jsonb/data.jsonb")
    cache = None
    _conn = None

    @classmethod
    async def setup(cls, encryption_key: str):
        cls.path.parent.mkdir(
            parents=True,
            exist_ok=True
        )
        cls.cache = diskstore(
            filepath="db_cache.bin",
            limit=10000,
            mode="lru"
        )
        cls._conn = await aiolibsql.connect(
            str(cls.path),
            autocommit=1,
            encryption_key=encryption_key
        )
        await cls._conn.execute("PRAGMA journal_mode = WAL")
        await cls._conn.execute("PRAGMA mmap_size = 2147483648")
        await cls._conn.execute("PRAGMA synchronous = NORMAL")
        await cls._conn.execute("CREATE TABLE IF NOT EXISTS store (id INTEGER PRIMARY KEY, data BLOB)")
        logging.info("huh")

    @classmethod
    async def get(
        cls,
        user_id: int,
        type_ref: Any = dict,
        ttl: float | None = 60.0
    ) -> Any:
        if not cls._conn:
            await cls.setup()
        
        cache_key = f"u:{user_id}"
        if ttl is not None:
            cached = await cls.cache.get(
                cache_key,
                type_ref
            )
            if cached is not None:
                return cached

        cur = await cls._conn.execute(
            "SELECT json(data) FROM store WHERE id = ?",
            (user_id,)
        )
        row = await cur.fetchone()
        
        if not row or not row[0]:
            return type_ref() if callable(type_ref) else {}
        
        data = decode(
            row[0].encode(),
            type=type_ref
        )
        if ttl is not None:
            await cls.cache.set(
                cache_key,
                data,
                ttl
            )
        return data

    @classmethod
    async def set(
        cls,
        user_id: int,
        data: Any
    ):
        if not cls._conn:
            await cls.setup()
        await cls.cache.set(
            f"u:{user_id}",
            data,
            60.0
        )
        
        # Convert to JSON text first, then SQLite's jsonb() converts to binary BLOB
        payload = encode(data).decode()
        await cls._conn.execute(
            "INSERT OR REPLACE INTO store (id, data) VALUES (?, jsonb(?))",
            (user_id, payload)
        )

    @classmethod
    async def delete(
        cls,
        user_id: int
    ):
        if not cls._conn:
            await cls.setup()
        await cls.cache.delete(f"u:{user_id}")
        await cls._conn.execute(
            "DELETE FROM store WHERE id = ?",
            (user_id,)
        )
