from discord.ext.commands import Cog
from discord.ext.commands import check
from discord.commands import SlashCommandGroup
from discord.commands import Option
from discord.commands import AutocompleteContext
from discord.commands import ApplicationContext
from discord import InteractionContextType
from discord import IntegrationType
from utils.db import db
from models.blacklist import blacklistdata

_BL_KEY = 0

async def _load() -> blacklistdata:
    return await db.get(_BL_KEY, blacklistdata)

async def _save(data: blacklistdata) -> None:
    await db.set(_BL_KEY, data)

def _owner_check(ctx: ApplicationContext) -> bool:
    return ctx.user.id in ctx.bot.cfg.owners

def owner_only():
    return check(_owner_check)

async def _remove_autocomplete(ctx: AutocompleteContext):
    bl = getattr(ctx.interaction.client, "blacklist", None)
    if not bl:
        return []
    val = ctx.value.lower()
    kind = ctx.options.get("type", "user")
    if kind == "server":
        return [str(i) for i in bl.servers if val in str(i)][:25]
    return [str(i) for i in bl.users if val in str(i)][:25]

class blacklist(Cog):
    def __init__(self, bot):
        self.bot = bot

    x = SlashCommandGroup(
        name="x",
        description="manage the bot blacklist",
        contexts={
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel
        },
        integration_types={
            IntegrationType.guild_install,
            IntegrationType.user_install
        },
        checks=[_owner_check]
    )

    @x.command(
        name="add",
        description="blacklist a user or server"
    )
    async def x_add(
        self,
        ctx: ApplicationContext,
        type: Option(
            str,
            name="type",
            description="user or server",
            choices=["user", "server"],
            required=True
        ),
        id: Option(
            str,
            name="id",
            description="the user or server id to blacklist",
            required=True
        )
    ):
        try:
            target_id = int(id)
        except ValueError:
            return await ctx.error("invalid id.")

        bl = await _load()

        if type == "user":
            if target_id in bl.users:
                return await ctx.warn(f"`{target_id}` is already blacklisted.")
            bl.users.append(target_id)
            await _save(bl)
            ctx.bot.blacklist = bl
            return await ctx.success(f"blacklisted user `{target_id}`.")

        if target_id in bl.servers:
            return await ctx.warn(f"`{target_id}` is already blacklisted.")
        bl.servers.append(target_id)
        await _save(bl)
        ctx.bot.blacklist = bl
        return await ctx.success(f"blacklisted server `{target_id}`.")

    @x.command(
        name="remove",
        description="remove a user or server from the blacklist"
    )
    async def x_remove(
        self,
        ctx: ApplicationContext,
        type: Option(
            str,
            name="type",
            description="user or server",
            choices=["user", "server"],
            required=True
        ),
        id: Option(
            str,
            name="id",
            description="the id to remove",
            autocomplete=_remove_autocomplete,
            required=True
        )
    ):
        try:
            target_id = int(id)
        except ValueError:
            return await ctx.error("invalid id.")

        bl = await _load()

        if type == "user":
            if target_id not in bl.users:
                return await ctx.warn(f"`{target_id}` is not blacklisted.")
            bl.users.remove(target_id)
            await _save(bl)
            ctx.bot.blacklist = bl
            return await ctx.success(f"removed user `{target_id}` from blacklist.")

        if target_id not in bl.servers:
            return await ctx.warn(f"`{target_id}` is not blacklisted.")
        bl.servers.remove(target_id)
        await _save(bl)
        ctx.bot.blacklist = bl
        return await ctx.success(f"removed server `{target_id}` from blacklist.")

    @x.command(
        name="list",
        description="list all blacklisted users or servers"
    )
    async def x_list(
        self,
        ctx: ApplicationContext,
        type: Option(
            str,
            name="type",
            description="user or server",
            choices=["user", "server"],
            required=True
        )
    ):
        bl = await _load()

        if type == "user":
            if not bl.users:
                return await ctx.warn("no blacklisted users.")
            ids = "\n".join(f"`{i}`" for i in bl.users)
            return await ctx.success(f"**blacklisted users:**\n{ids}")

        if not bl.servers:
            return await ctx.warn("no blacklisted servers.")
        ids = "\n".join(f"`{i}`" for i in bl.servers)
        return await ctx.success(f"**blacklisted servers:**\n{ids}")

def setup(bot):
    bot.add_cog(blacklist(bot))
