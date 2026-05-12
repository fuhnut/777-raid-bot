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
    for path in Path("cogs").glob("*.py"):
        client.load_extension(f"cogs.{path.stem}")
    client.run(cfg.token)

if __name__ == "__main__":
    main()
