from __future__ import annotations
from time import time
from typing import Any
from asyncio import to_thread, Lock
from pathlib import Path
from msgspec.msgpack import encode, decode

class diskstore:
    def __init__(
        self,
        filepath: str,
        limit: int,
        mode: str
    ):
        self.path = Path(filepath)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cache: dict[str, tuple[float, bytes]] = {}
        self.lock = Lock()
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                data = self.path.read_bytes()
                self.cache = decode(data, type=dict[str, tuple[float, bytes]])
            except Exception:
                self.cache = {}

    async def set(
        self,
        key: str,
        value: Any,
        ttl: float
    ) -> None:
        async with self.lock:
            self.cache[key] = (time() + ttl, encode(value))
            data = encode(self.cache)
            await to_thread(self.path.write_bytes, data)

    async def get(
        self,
        key: str,
        type_ref: Any
    ) -> Any:
        val = self.cache.get(key)
        if not val:
            return None
            
        expires, data = val
        if time() > expires:
            async with self.lock:
                self.cache.pop(key, None)
                await to_thread(self.path.write_bytes, encode(self.cache))
            return None
            
        return decode(data, type=type_ref)

    async def get_all(
        self,
        type_ref: Any
    ) -> list[Any]:
        now = time()
        return [
            decode(v[1], type=type_ref) for v in self.cache.values()
            if v[0] > now
        ]

    async def delete(self, key: str) -> None:
        async with self.lock:
            if key in self.cache:
                del self.cache[key]
                await to_thread(self.path.write_bytes, encode(self.cache))

    async def clear(self) -> None:
        async with self.lock:
            self.cache.clear()
            await to_thread(self.path.write_bytes, encode(self.cache))
