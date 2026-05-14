import discord
from discord.ui import (
    DesignerView,
    Container,
    Section,
    TextDisplay,
    Button
)
from discord import ButtonStyle

async def _respond_custom(
    ctx: discord.ApplicationContext | discord.Interaction,
    content: str,
    emoji: str,
    color: int
):
    components = [
        Container(
            Section(
                TextDisplay(content=content),
                accessory=Button(
                    style=ButtonStyle.secondary,
                    emoji=discord.PartialEmoji.from_str(emoji),
                    custom_id="v4:ui:ok",
                ),
            ),
            colour=color
        ),
    ]
    
    view = DesignerView(*components, timeout=None)
    
    if isinstance(ctx, discord.Interaction):
        if ctx.response.is_done():
            await ctx.followup.send(view=view, ephemeral=True)
        else:
            await ctx.response.send_message(view=view, ephemeral=True)
    else:
        if ctx.response.is_done():
            await ctx.followup.send(view=view, ephemeral=True)
        else:
            await ctx.respond(view=view, ephemeral=True)

async def success(self, content: str):
    await _respond_custom(
        self,
        content,
        "<:approve:1484984864825409557>",
        0x2ecc71
    )

async def warn(self, content: str):
    await _respond_custom(
        self,
        content,
        "<:warning:1484984862489313367>",
        0xf1c40f
    )

async def error(self, content: str):
    await _respond_custom(
        self,
        content,
        "<:deny:1484984838581780652>",
        0xe74c3c
    )

def setup():
    # monkeypatch ApplicationContext
    discord.ApplicationContext.success = success
    discord.ApplicationContext.warn = warn
    discord.ApplicationContext.error = error
    
    # monkeypatch Interaction
    discord.Interaction.success = success
    discord.Interaction.warn = warn
    discord.Interaction.error = error
