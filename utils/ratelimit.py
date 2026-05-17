from __future__ import annotations
import logging
import asyncio
import os
import mmap
from time import time
from asyncio import sleep, Lock, to_thread
from aiohttp import ClientSession, ClientResponse
from typing import Any
from pathlib import Path
from msgspec.msgpack import encode, decode
from models.ratelimit import routebucket

class apilimiter:
    __slots__ = (
        "http",
        "buckets",
        "locks",
        "global_lock",
        "total_lock",
        "history",
        "path",
        "loop_task"
    )

    @property
    def session(self) -> ClientSession:
        return getattr(
            self.http, 
            "_HTTPClient__session", 
            getattr(self.http, "_session", None)
        )

    def __init__(self, http: Any):
        self.http = http
        self.path = Path("data/cache/ratelimits.bin")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.buckets: dict[str, routebucket] = {}
        self._load_mmap()
        self.locks: dict[str, Lock] = {}
        self.global_lock = Lock()
        self.total_lock = Lock()
        self.history: list[float] = []
        self.loop_task = None

    async def _flush_loop(self):
        while True:
            await sleep(5.0)
            await self._sync_to_disk()

    def _load_mmap(self):
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        try:
            fd = os.open(self.path, os.O_RDONLY)
            try:
                with mmap.mmap(fd, 0, access=mmap.ACCESS_READ) as mm:
                    data = decode(mm, type=dict[str, routebucket])
                    self.buckets.update(data)
            finally:
                os.close(fd)
        except Exception:
            pass

    async def _sync_to_disk(self):
        try:
            temp_path = self.path.with_suffix(f".{os.getpid()}.tmp")
            data = encode(self.buckets)
            def _write():
                with open(temp_path, "wb") as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, self.path)
            await to_thread(_write)
        except Exception:
            pass

    def _get_lock(self, route: str) -> Lock:
        if route not in self.locks:
            self.locks[route] = Lock()
        return self.locks[route]

    async def _handle_429(
        self,
        b: routebucket,
        route: str,
        res: ClientResponse
    ) -> None:
        try:
            data = await res.json()
            retry = data.get("retry_after", res.headers.get("retry-after"))
        except Exception:
            retry = res.headers.get("retry-after")
            
        is_global = res.headers.get("x-ratelimit-global")
        logging.warning(f"429 | route: {route} | global: {is_global} | retry: {retry}s")
        delay = float(retry) if retry else 2.5
        b.limit = max(1, b.limit - 1)
        b.remaining = 0
        new_reset = time() + delay
        if new_reset > b.reset:
            b.reset = new_reset
        if is_global:
            async with self.global_lock:
                await sleep(delay + 0.3)

    async def request(
        self,
        method: str,
        route: str,
        url: str,
        **kwargs: Any
    ) -> ClientResponse:
        if not self.loop_task:
            self.loop_task = asyncio.create_task(self._flush_loop())
            
        lock = self._get_lock(route)
        while True:
            async with self.total_lock:
                now = time()
                self.history = [t for t in self.history if now - t < 1.0]
                if len(self.history) >= 45:
                    await sleep(max(0.01, 1.1 - (now - self.history[0])))
                    continue
                self.history.append(now)

            sleep_time = 0.0
            async with lock:
                b = self.buckets.get(route)
                if not b:
                    init_limit = 4 if route.startswith("webhooks") else 1
                    b = routebucket(limit=init_limit, remaining=init_limit, reset=0.0)
                    self.buckets[route] = b
                
                now = time()
                if now >= b.reset:
                    b.remaining = b.limit
                    b.reset = now + (2.5 if route.startswith("webhooks") else 1.1)

                if b.remaining <= 0:
                    sleep_time = max(0.0, b.reset - now) + 0.3
                else:
                    b.remaining -= 1
                    b.last_req = time()

            if sleep_time > 0:
                await sleep(sleep_time)
                continue

            async with self.global_lock:
                pass

            res = await self.session.request(method, url, **kwargs)
            
            lim = res.headers.get("x-ratelimit-limit")
            rem = res.headers.get("x-ratelimit-remaining")
            after = res.headers.get("x-ratelimit-reset-after")
            
            if lim or rem or after or res.status == 429:
                async with lock:
                    if lim:
                        b.limit = int(lim) - (1 if route.startswith("webhooks") else 0)
                    if rem:
                        new_rem = int(rem)
                        if new_rem < b.remaining:
                            b.remaining = new_rem
                    if after:
                        new_reset = time() + float(after) + 0.25
                        if new_reset > b.reset:
                            b.reset = new_reset

                    if res.status == 429:
                        await self._handle_429(b, route, res)
            
            if res.status == 429:
                continue
                
            return res

    async def close(self):
        if self.loop_task:
            self.loop_task.cancel()
        await self._sync_to_disk()

