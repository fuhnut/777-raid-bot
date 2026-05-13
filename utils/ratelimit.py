from __future__ import annotations
import logging
from time import time
from asyncio import sleep, Lock
from aiohttp import ClientSession, ClientResponse
from typing import Any
from utils.cache import diskstore
from msgspec import Struct as struct

class routebucket(
    struct,
    kw_only=True
):
    remaining: int = 1
    reset: float = 0.0

class apilimiter:
    __slots__ = (
        "session",
        "store",
        "locks",
        "global_lock",
        "total_lock",
        "count",
        "last_sec"
    )

    def __init__(self, session: ClientSession):
        self.session = session
        self.store = diskstore(
            filepath="ratelimits.bin",
            limit=10000,
            mode="lru"
        )
        self.locks: dict[str, Lock] = {}
        self.global_lock = Lock()
        self.total_lock = Lock()
        self.count = 0
        self.last_sec = time()

    def _get_lock(self, route: str) -> Lock:
        if route not in self.locks:
            self.locks[route] = Lock()
        return self.locks[route]

    async def _handle_429(
        self,
        b: routebucket,
        route: str,
        res: ClientResponse,
        lock: Lock
    ) -> None:
        retry = res.headers.get("retry-after")
        is_global = res.headers.get("x-ratelimit-global")
        logging.warning(f"429 | route: {route} | global: {is_global} | retry: {retry}s")
        
        delay = float(retry) if retry else 1.0
        b.remaining = 0
        b.reset = time() + delay
        await self.store.set(route, b, 3600.0)
        
        if is_global:
            async with self.global_lock:
                await sleep(delay + 0.5)
        else:
            lock.release()
            await sleep(delay + 0.5)

    async def request(
        self,
        method: str,
        route: str,
        url: str,
        **kwargs: Any
    ) -> ClientResponse:
        lock = self._get_lock(route)
        
        while True:
            async with self.global_lock:
                pass

            async with self.total_lock:
                now = time()
                if now - self.last_sec > 1.0:
                    self.count = 0
                    self.last_sec = now
                
                if self.count >= 50:
                    await sleep(max(0.0, (self.last_sec + 1.0) - now))
                    self.count = 0
                    self.last_sec = time()
                
                self.count += 1
                
            await lock.acquire()
            b = await self.store.get(route, routebucket)
            if not b:
                b = routebucket()
                
            now = time()
            if b.remaining <= 0 and now < (b.reset + 0.5):
                lock.release()
                await sleep((b.reset + 0.5) - now)
                continue

            res = await self.session.request(method, url, **kwargs)
            
            rem = res.headers.get("x-ratelimit-remaining")
            after = res.headers.get("x-ratelimit-reset-after")
            
            if rem:
                b.remaining = int(rem)
            else:
                b.remaining -= 1
                
            if after:
                b.reset = time() + float(after)

            if res.status == 429:
                await self._handle_429(b, route, res, lock)
                continue

            await self.store.set(route, b, 3600.0)
            lock.release()
            return res
