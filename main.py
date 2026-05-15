from __future__ import annotations
import asyncio
import logging
import uvloop
from pathlib import Path
from contextlib import suppress
from msgspec.json import decode as msg_decode
from discord.flags import (
    Intents,
    MemberCacheFlags
)
from discord.mentions import AllowedMentions
from discord.ext.commands import Bot
from models.config import config
from models.blacklist import blacklistdata
from utils.logger import setup as log_setup
from utils.webhook import setup as webhook_setup
from utils.ratelimit import apilimiter
from utils.responses import setup as responses_setup
from utils.bio import update_bio
from utils.db import db
import discord.http
import discord.errors
from urllib.parse import quote

async def v4_http(
    self,
    route, **kwargs
):
    if not hasattr(self, "fast_limiter"):
        self.fast_limiter = apilimiter(self)
        
    if getattr(self, "_session", None) is None:
        import aiohttp
        self._session = aiohttp.ClientSession(
            connector=self.connector,
            ws_response_class=discord.http.DiscordClientWebSocketResponse
        )
    
    headers = kwargs.pop("headers", {})
    if self.token:
        headers["Authorization"] = f"Bot {self.token}"
        
    reason = kwargs.pop("reason", None)
    if reason:
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

    async def setup_hook(self):
        self.blacklist = blacklistdata()
        self.loop.create_task(self._refresh_blacklist())

    async def _refresh_blacklist(self):
        while not self.is_closed():
            self.blacklist = await db.get(0, blacklistdata, ttl=None)
            await asyncio.sleep(15)

    async def on_ready(self):
        logging.info(f"logged in as {self.user}")
        await update_bio(self)
        for cmd in self.application_commands:
            logging.info(f"synced command: /{cmd.name}")

def main():
    uvloop.install()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    data = Path("config.json").read_bytes()
    cfg = msg_decode(
        data,
        type=config
    )
    
    responses_setup()
    log_setup()
    from utils.db import db
    loop.run_until_complete(db.setup(cfg.database_key))
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
    
    @client.event
    async def on_interaction(itx: discord.Interaction):
        if itx.type == discord.InteractionType.component:
            if itx.custom_id == "v4:ui:ok":
                with suppress(Exception):
                    await itx.response.edit_message(view=None)
                    await itx.delete_original_response()
                    return

        bl = getattr(client, "blacklist", None)
        if bl and itx.type != discord.InteractionType.auto_complete:
            if itx.user and itx.user.id in bl.users:
                return await itx.error("SON YOU ARE BLACKLISTED")
            if itx.guild_id and itx.guild_id in bl.servers:
                return await itx.error("SON THIS SERVER IS BLACKLISTED")

        await client.process_application_commands(itx)

    client.run(cfg.token)

if __name__ == "__main__":
    main()
