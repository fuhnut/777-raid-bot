from __future__ import annotations

import mmap
import os
from asyncio import Lock, create_task, sleep, to_thread
from collections import OrderedDict
from pathlib import Path
from time import time
from typing import Any

from utils.encoders import decode, encode


class diskstore:
    __slots__ = (
        "path",
        "limit",
        "cache",
        "lock",
        "sync_lock",
        "sync_count",
        "loop_task",
    )

    def __init__(self, filepath: str, limit: int, mode: str):
        if not filepath.startswith("data/cache/"):
            filepath = f"data/cache/{filepath}"
        self.path = Path(filepath)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.limit = limit
        self.cache: OrderedDict[str, tuple[float, bytes]] = OrderedDict()
        self.lock = Lock()
        self.sync_lock = Lock()
        self.sync_count = 0
        self.loop_task = None
        self._load()

    async def _ensure_loop(self):
        if not self.loop_task:
            try:
                self.loop_task = create_task(self._flush_loop())
            except RuntimeError:
                pass

    async def _flush_loop(self):
        while True:
            await sleep(10.0)
            async with self.lock:
                now = time()
                expired = [k for k, v in self.cache.items() if v[0] < now]
                for k in expired:
                    self.cache.pop(k, None)
            await self._sync()

    def _load(self):
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        try:
            fd = os.open(self.path, os.O_RDONLY)
            try:
                with mmap.mmap(fd, 0, access=mmap.ACCESS_READ) as mm:
                    data = decode(mm, type=dict[str, tuple[float, bytes]])
                    self.cache.update(data)
            finally:
                os.close(fd)
        except Exception:
            self.cache = OrderedDict()

    async def _sync(self):
        async with self.sync_lock:
            self.sync_count += 1
            temp_path = self.path.with_suffix(
                f".{os.getpid()}.{id(self)}.{self.sync_count}.tmp"
            )
            async with self.lock:
                data = encode(self.cache)

            def _write():
                with open(temp_path, "wb") as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, self.path)

            await to_thread(_write)

    async def set(self, key: str, value: Any, ttl: float) -> None:
        await self._ensure_loop()
        async with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = (time() + ttl, encode(value))
            if len(self.cache) > self.limit:
                self.cache.popitem(last=False)
        create_task(self._sync())

    async def get(self, key: str, type_ref: Any) -> Any:
        await self._ensure_loop()
        async with self.lock:
            val = self.cache.get(key)
            if not val:
                return None
            expires, data = val
            if time() > expires:
                self.cache.pop(key, None)
                return None
            self.cache.move_to_end(key)
            return decode(data, type=type_ref)

    async def get_all(self, type_ref: Any) -> list[Any]:
        await self._ensure_loop()
        now = time()
        async with self.lock:
            return [
                decode(v[1], type=type_ref) for v in self.cache.values() if v[0] > now
            ]

    async def delete(self, key: str) -> None:
        await self._ensure_loop()
        async with self.lock:
            self.cache.pop(key, None)
        create_task(self._sync())

    async def clear(self) -> None:
        await self._ensure_loop()
        async with self.lock:
            self.cache.clear()

            def _unlink():
                self.path.unlink(missing_ok=True)

            await to_thread(_unlink)
