import re
import random
import discord
from pathlib import Path
from discord.ext.commands import Cog
from discord import (
    ButtonStyle,
    SeparatorSpacingSize,
    InteractionType
)
from discord.enums import (
    InteractionContextType,
    IntegrationType
)
from discord.commands import (
    slash_command as command,
    Option,
    ApplicationContext
)
from discord.ui import (
    DesignerView,
    TextDisplay,
    Container,
    Separator,
    ActionRow,
    Button
)
from utils.cache import diskstore
from models.raid import raidstate
from msgspec.json import decode

class floodview(DesignerView):
    def __init__(
        self,
        bot
    ):
        super().__init__(timeout=None)
        self.bot = bot
        self.btn5 = "v4:floodcmd:5x"
        self.btn6 = "v4:floodcmd:6x"

    def _get_payload(
        self,
        state: raidstate
    ):
        msg = state.message
        if not state.bypass:
            return {
                "content": msg,
                "is_v2": False
            }
        return {
            "view": [
                TextDisplay(content=msg).to_component_dict()
            ],
            "is_v2": True
        }

    async def dispatch(
        self,
        itx: discord.Interaction,
        count: int,
        respond: bool,
        state: raidstate
    ):
        if respond:
            if state.bypass:
                await itx.response.defer(ephemeral=True)
            else:
                p = self._get_payload(state)
                await itx.response.send_message(content=p["content"])
                count -= 1
        else:
            await itx.response.defer(ephemeral=True)
        import asyncio
        tasks = []
        for _ in range(count):
            p = self._get_payload(state)
            tasks.append(
                self.bot.v4_webhook.send(
                    ctx=itx,
                    silent=state.silent,
                    **p
                )
            )
        await asyncio.gather(*tasks)

class flood(Cog):
    def __init__(
        self,
        bot
    ):
        self.bot = bot
        self.states = diskstore(
            filepath="flood_cmd_states.bin",
            limit=1000,
            mode="lru"
        )

    @Cog.listener()
    async def on_ready(self):
        self.bot.add_view(floodview(self.bot))

    @command(
        name="flood",
        description="spam a custom message",
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
    async def flood_cmd(
        self,
        ctx: ApplicationContext,
        message: Option(
            str,
            name="message",
            description="the message to spam",
            required=True
        ),
        silent: Option(
            bool,
            name="silent",
            description="send as silent msg?",
            default=False
        ),
        bypass_automod: Option(
            bool,
            name="bypass_automod",
            description="bypass automod?",
            default=False
        )
    ):
        state = raidstate(
            silent=silent,
            bypass=bypass_automod,
            message=message
        )
        await self.states.set(
            f"{ctx.channel_id}:{ctx.user.id}",
            state,
            3600.0
        )
        components = [
            Container(
                TextDisplay(content=f"spamming: {message[:50]}..."),
                Separator(
                    divider=True,
                    spacing=SeparatorSpacingSize.small,
                ),
                ActionRow(
                    Button(
                        style=ButtonStyle.primary,
                        label="flood 5x",
                        custom_id="v4:floodcmd:5x",
                    ),
                    Button(
                        style=ButtonStyle.danger,
                        label="flood 6x",
                        custom_id="v4:floodcmd:6x",
                    ),
                ),
            ),
        ]
        await ctx.respond(
            view=DesignerView(
                *components,
                timeout=None
            ),
            ephemeral=True
        )

    @Cog.listener()
    async def on_interaction(
        self,
        itx: discord.Interaction
    ):
        if itx.type != InteractionType.component:
            return
        cid = itx.custom_id
        view = floodview(self.bot)
        if cid not in (
            view.btn5,
            view.btn6
        ):
            return
        key = f"{itx.channel_id}:{itx.user.id}"
        state = await self.states.get(
            key,
            raidstate
        )
        if not state or not state.message:
            return
        if cid == view.btn5:
            await view.dispatch(
                itx,
                5,
                False,
                state
            )
        elif cid == view.btn6:
            await view.dispatch(
                itx,
                6,
                True,
                state
            )

def setup(bot):
    bot.add_cog(flood(bot))
