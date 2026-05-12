import msgspec
import uvloop
import logging
import asyncio
from pathlib import Path
from discord import (
    Intents,
    MemberCacheFlags
)
from discord.ext.commands import Bot
from models.config import config
from utils import logger

class v4(Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        logging.info(f"logged in as {self.user}")

def main():
    uvloop.install()
    asyncio.set_event_loop(asyncio.new_event_loop())
    logger.setup()
    data = Path("config.json").read_bytes()
    cfg = msgspec.json.decode(data, type=config)
    intents = Intents.default()
    intents.members = True
    client = v4(
        command_prefix="!",
        intents=intents,
        member_cache_flags=MemberCacheFlags.none(),
        chunk_guilds_at_startup=False,
        max_messages=0,
        compress="zstd-stream"
    )
    client.load_extension("cogs.ping")
    client.run(cfg.token)

if __name__ == "__main__":
    main()
