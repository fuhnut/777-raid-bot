from __future__ import annotations

import asyncio
import logging
import re
from contextlib import suppress
from pathlib import Path
from urllib.parse import quote

import uvloop
from discord import (
    ApplicationContext,
    Interaction,
    InteractionType,
    SeparatorSpacingSize,
)
from discord.errors import Forbidden, HTTPException, LoginFailure, NotFound
from discord.ext.commands import Bot
from discord.flags import Intents, MemberCacheFlags
from discord.gateway import DiscordClientWebSocketResponse
from discord.http import HTTPClient
from discord.mentions import AllowedMentions
from discord.ui import (
    Container,
    Section,
    Separator,
    TextDisplay,
    Thumbnail,
)

from models.blacklist import blacklistdata
from models.config import config
from models.config import config as cfg_type
from utils.bio import update_bio
from utils.db import db
from utils.jsonc import load as jsonc_load
from utils.log_webhook import send as log_send
from utils.logger import setup as log_setup
from utils.ratelimit import apilimiter
from utils.responses import setup as responses_setup
from utils.webhook import setup as webhook_setup

_link_re = re.compile(r"https?:\/\/[\w.-]+(?:\/[\w./?=&%-]*)?")


async def v4_http(self, route, **kwargs):
    if not hasattr(self, "fast_limiter"):
        self.fast_limiter = apilimiter(self)

    if getattr(self, "_HTTPClient__session", None) is None:
        import aiohttp

        self._HTTPClient__session = aiohttp.ClientSession(
            connector=self.connector,
            ws_response_class=DiscordClientWebSocketResponse,
            trust_env=True,
        )

    headers = kwargs.pop("headers", {})
    if self.token:
        headers["Authorization"] = f"Bot {self.token}"

    reason = kwargs.pop("reason", None)
    if reason:
        headers["X-Audit-Log-Reason"] = quote(reason, safe="/ ")

    kwargs.pop("locale", None)

    url = (
        route.url
        if route.url.startswith("http")
        else f"https://discord.com/api/v10{route.url}"
    )
    res = await self.fast_limiter.request(
        route.method, route.bucket, url, headers=headers, **kwargs
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
        raise LoginFailure("wrong token nigga!")
    elif res.status == 403:
        raise Forbidden(res, data)
    elif res.status == 404:
        raise NotFound(res, data)
    else:
        raise HTTPException(res, data)


HTTPClient.request = v4_http


class __67__(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cfg = None

    async def close(self):
        if hasattr(self.http, "fast_limiter"):
            await self.http.fast_limiter.close()
        if (
            hasattr(self.http, "_HTTPClient__session")
            and self.http._HTTPClient__session
        ):
            await self.http._HTTPClient__session.close()
        await db.close()
        await super().close()

    async def setup_hook(self):
        self.blacklist = blacklistdata()
        self.loop.create_task(self._refresh_blacklist())

    async def _refresh_blacklist(self):
        while not self.is_closed():
            self.blacklist = await db.get(0, blacklistdata, ttl=None)
            await asyncio.sleep(2.5)  # should be higher?

    async def on_ready(self):
        logging.info(f"logged in as {self.user}")
        invite_url = f"https://discord.com/oauth2/authorize?client_id={self.user.id}"
        logging.info(f"invite: {invite_url}")
        await update_bio(self)

        from utils.member_cache import cachedmember
        from utils.member_cache import get as get_member_cache

        if db.persistence:
            get_member_cache().bind_store(db.persistence)

        if self.cfg and self.cfg.required_server_id:
            g = self.get_guild(self.cfg.required_server_id)
            if g:
                cache = get_member_cache()
                try:
                    async for member in g.fetch_members(limit=None):
                        m = cachedmember(
                            user_id=member.id,
                            role_ids=[r.id for r in member.roles],
                        )
                        cache.add(m)
                        await cache.save(m)
                    logging.info(
                        f"membercache: preloaded {g.name} ({g.member_count} members)"
                    )
                except Exception as e:
                    logging.warning(f"membercache: failed to preload {g.name}: {e}")

        for cmd in self.application_commands:
            logging.info(f"synced command: /{cmd.name}")


async def main():
    cfg = jsonc_load("config.json", cfg_type)

    responses_setup()
    log_setup()

    await db.setup("")

    intents = Intents.default()
    intents.guilds = True
    intents.members = True
    intents.voice_states = False
    intents.presences = False
    intents.messages = False
    intents.message_content = False
    client = __67__(
        command_prefix="!",
        intents=intents,
        chunk_guilds_at_startup=False,
        max_messages=0,
        compress="zstd-stream",
        member_cache_flags=MemberCacheFlags.none(),
        allowed_mentions=AllowedMentions.none(),
    )
    client.cfg = cfg
    client.db = db
    webhook_setup(client)

    # eagerly init the aiohttp session so py-cord's gateway code
    # finds it with the correct ws_response_class before connecting
    import aiohttp

    client.http._HTTPClient__session = aiohttp.ClientSession(
        connector=client.http.connector,
        ws_response_class=DiscordClientWebSocketResponse,
        trust_env=True,
    )

    for path in Path("commands").glob("*.py"):
        client.load_extension(f"commands.{path.stem}")
    client.load_extension("nuke")

    @client.event
    async def on_interaction(itx: Interaction):
        if itx.type == InteractionType.component:
            if itx.custom_id == "v4:ui:ok":
                with suppress(Exception):
                    await itx.response.edit_message(view=None)
                    await itx.delete_original_response()
                    return

        bl = getattr(client, "blacklist", None)
        if bl and itx.type != InteractionType.auto_complete:
            if itx.user and itx.user.id in bl.users:
                return await itx.error("SON YOU ARE BLACKLISTED")
            if itx.guild_id and itx.guild_id in bl.servers:
                return await itx.error("SON THIS SERVER IS BLACKLISTED")

        if itx.type == InteractionType.application_command:
            from utils.perms import _is_temp_blacklisted, deny

            remaining = await _is_temp_blacklisted(itx.user.id, itx.guild_id or 0)
            if remaining > 0:
                return await itx.error(
                    f"you are temp blacklisted from raid commands for {int(remaining)}s"
                )

            cog = getattr(itx.command, "cog", None)
            if cog and cog.__class__.__module__.startswith("commands."):
                if await deny(itx):
                    return

        await client.process_application_commands(itx)

    @client.event
    async def on_application_command(ctx: ApplicationContext):
        logging.info(f"{ctx.user} used /{ctx.command.name}")
        webhook_url = client.cfg.cmd_logs if client.cfg else ""
        if webhook_url:
            avatar = str(ctx.user.display_avatar.url) if ctx.user.display_avatar else ""
            channel = ctx.channel
            channel_name = channel.name if channel else "unknown"

            links = []
            if ctx.message:
                links = _link_re.findall(ctx.message.content or "")
            links_str = "\n".join(f"> {l}" for l in links) if links else "> none"

            container = Container(
                Section(
                    TextDisplay(content=f"Command used by {ctx.user.mention}\n"),
                    TextDisplay(
                        content=(
                            f"> Command: /{ctx.command.name}\n"
                            f"> Server: `{ctx.guild_id or 'dm'}`\n"
                            f"> Channel: <#{channel.id}> ({channel_name})\n"
                        )
                    ),
                    accessory=Thumbnail(url=avatar) if avatar else None,
                ),
                Separator(divider=True, spacing=SeparatorSpacingSize.small),
                TextDisplay(content=f"Links detected:\n{links_str}"),
            )

            payload = {
                "flags": 32768,
                "components": [container.to_component_dict()],
            }
            asyncio.create_task(log_send(webhook_url, payload))

    await client.start(cfg.token)


if __name__ == "__main__":
    try:
        import uvloop

        uvloop.run(main())
    except ImportError:
        asyncio.run(main())
