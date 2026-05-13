from __future__ import annotations

import asyncio
import logging
import uvloop
from pathlib import Path
from msgspec.json import decode as msg_decode
from discord.flags import (
    Intents,
    MemberCacheFlags
)
from discord.mentions import AllowedMentions
from discord.ext.commands import Bot
from models.config import config
from utils.logger import setup as log_setup
from utils.webhook import setup as webhook_setup
from utils.ratelimit import apilimiter
import discord.http

async def v4_http(
    self,
    route, **kwargs
):
    if not hasattr(self, "fast_limiter"):
        session = getattr(
            self,
            "_HTTPClient__session",
            getattr(self, "_session", None)
        )
        self.fast_limiter = apilimiter(session)
    
    headers = kwargs.pop("headers", {})
    if self.token:
        headers["Authorization"] = f"Bot {self.token}"
        
    reason = kwargs.pop("reason", None)
    if reason:
        from urllib.parse import quote
        headers["X-Audit-Log-Reason"] = quote(reason, safe="/ ")
        
    kwargs.pop("locale", None)
        
    url = route.url if route.url.startswith("http") else f"https://discord.com/api/v10{route.url}"
    res = await self.fast_limiter.request(
        route.method,
        route.bucket,
        url,
        headers=headers,
        **kwargs
    )
    
    if res.status in (204, 304):
        return None
        
    try:
        data = await res.json()
    except Exception:
        data = await res.text()
        
    if 300 > res.status >= 200:
        return data
        
    import discord.errors
    if res.status == 401:
        raise discord.errors.LoginFailure("improper token has been passed.")
    elif res.status == 403:
        raise discord.errors.Forbidden(res, data)
    elif res.status == 404:
        raise discord.errors.NotFound(res, data)
    else:
        raise discord.errors.HTTPException(res, data)

discord.http.HTTPClient.request = v4_http

class v4(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cfg = None

    async def on_ready(self):
        logging.info(f"logged in as {self.user}")
        for cmd in self.application_commands:
            logging.info(f"synced command: /{cmd.name}")

def main():
    uvloop.install()
    asyncio.set_event_loop(asyncio.new_event_loop())
    log_setup()
    data = Path("config.json").read_bytes()
    cfg = msg_decode(
        data,
        type=config
    )
    intents = Intents.default()
    intents.members = True
    client = v4(
        command_prefix="!",
        intents=intents,
        member_cache_flags=MemberCacheFlags.none(),
        chunk_guilds_at_startup=False,
        max_messages=0,
        compress="zstd-stream",
        allowed_mentions=AllowedMentions.all()
    )
    client.cfg = cfg
    webhook_setup(client)
    for path in Path("commands").glob("*.py"):
        client.load_extension(f"commands.{path.stem}")
    client.run(cfg.token)

if __name__ == "__main__":
    main()
