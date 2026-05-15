import os
import mmap
import logging
from typing import Any
import msgspec.msgpack as msgpack
from utils.cache import diskstore

class db:
    base_path = "data/jsonb"
    cache = None
    
    @classmethod
    async def setup(cls):
        if not os.path.exists(cls.base_path):
            os.makedirs(cls.base_path, exist_ok=True)
            
        cls.cache = diskstore(
            filepath="db_cache.bin",
            limit=5000,
            mode="lru"
        )
        logging.info(f"{cls.base_path}")

    @classmethod
    async def get(
        cls,
        user_id: int,
        type_ref: Any = dict,
        ttl: float | None = 60.0
    ) -> Any:
        if not cls.cache:
            await cls.setup()
            
        cache_key = f"u:{user_id}"
        if ttl is not None:
            # Note: cache stores raw dicts or objects, 
            # we must ensure type_ref is respected if returning from cache
            cached = await cls.cache.get(cache_key, type_ref)
            if cached is not None:
                return cached

        path = f"{cls.base_path}/{user_id}.jsonb"
        if not os.path.exists(path):
            return type_ref() if callable(type_ref) else {}
            
        try:
            with open(path, "rb") as f:
                size = os.path.getsize(path)
                if size == 0:
                    return type_ref() if callable(type_ref) else {}
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    data = msgpack.decode(mm[:], type=type_ref)
                    if ttl is not None:
                        await cls.cache.set(cache_key, data, ttl)
                    return data
        except Exception as e:
            logging.error(f"v4store get error for {user_id}: {e}")
            return type_ref() if callable(type_ref) else {}

    @classmethod
    async def set(
        cls,
        user_id: int,
        data: Any
    ):
        if not cls.cache:
            await cls.setup()

        # update cache
        await cls.cache.set(f"u:{user_id}", data, 60.0)
        
        path = f"{cls.base_path}/{user_id}.jsonb"
        temp_path = f"{path}.tmp"
        
        try:
            payload = msgpack.encode(data)
            with open(temp_path, "wb") as f:
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, path)
        except Exception as e:
            logging.error(f"v4store set error for {user_id}: {e}")
            if os.path.exists(temp_path):
                os.remove(temp_path)

    @classmethod
    async def delete(
        cls,
        user_id: int
    ):
        if not cls.cache:
            await cls.setup()
            
        await cls.cache.delete(f"u:{user_id}")
        path = f"{cls.base_path}/{user_id}.jsonb"
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logging.error(f"v4store delete error for {user_id}: {e}")

    @staticmethod
    def pack(obj: Any) -> bytes:
        return msgpack.encode(obj)

    @staticmethod
    def unpack(
        data: bytes,
        type_ref: Any
    ) -> Any:
        return msgpack.decode(
            data,
            type=type_ref
        )
