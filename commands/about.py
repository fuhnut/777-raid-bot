import time
import psutil
import discord
from discord.ext.commands import Cog
from discord.commands import (
    slash_command as command,
    ApplicationContext
)
from discord.ui import (
    DesignerView,
    TextDisplay,
    Container,
    ActionRow,
    Button
)
from discord import (
    ButtonStyle,
    InteractionContextType,
    IntegrationType
)

class about(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command(
        name="about",
        description="info about the bot.",
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
    async def about_cmd(self, ctx: ApplicationContext):
        p = psutil.Process()
        cpu = p.cpu_percent()
        ram = p.memory_info().rss / 1048576
        up = time.time() - p.create_time()
        
        h, r = divmod(up, 3600)
        m, s = divmod(r, 60)
        
        stats = (
            "about bot\n\n"
            f"**pycord ver** {discord.__version__}\n"
            f"**uptime:** {int(h)}h {int(m)}m {int(s)}s\n"
            f"**cpu:** {cpu}%\n"
            f"**ram:** {ram:.2f} mb"
        )
        
        components = [
            Container(
                TextDisplay(content=stats),
                ActionRow(
                    Button(
                        style=ButtonStyle.link,
                        label="github",
                        url="https://github.com/fuhnut/raid-bot-v4"
                    )
                )
            )
        ]
        await ctx.respond(
            view=DesignerView(
                *components,
                timeout=None
            ),
            ephemeral=True
        )

def setup(bot):
    bot.add_cog(about(bot))
