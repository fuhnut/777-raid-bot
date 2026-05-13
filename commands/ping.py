from __future__ import annotations

from time import perf_counter
from discord.commands import (
    slash_command as v4,
    ApplicationContext
)
from discord.enums import (
    InteractionContextType,
    IntegrationType
)
from discord.ext.commands import Cog

class ping(Cog):
    def __init__(self, bot):
        self.bot = bot

    @v4(
        name="ping",
        description="check the bots latency",
        contexts={
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel
        },
        integration_types={
            IntegrationType.guild_install,
            IntegrationType.user_install
        }
    )
    async def ping(self, ctx: ApplicationContext):
        from contextlib import suppress
        from time import perf_counter
        start = perf_counter()
        with suppress(Exception):
            msg = await ctx.respond(
                f"ws: {round(self.bot.latency * 1000)}ms",
                ephemeral=True
            )
            rest = round((perf_counter() - start) * 1000)
            await msg.edit_original_response(
                content=f"ws: {round(self.bot.latency * 1000)}ms | rest: {rest}ms"
            )

def setup(bot):
    bot.add_cog(ping(bot))
