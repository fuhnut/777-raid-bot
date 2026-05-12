from discord.http import Route

class webhook:
    __slots__ = ("bot",)

    def __init__(self, bot):
        self.bot = bot

    async def send(
        self,
        ctx,
        content: str | None = None,
        view: list | None = None,
        is_v2: bool = False,
        silent: bool = False
    ):
        payload = {}
        flags = 0
        if silent:
            flags |= 4096
        if is_v2:
            flags |= 32768
        else:
            if content:
                payload["content"] = content

        if view:
            payload["components"] = view
        
        if flags:
            payload["flags"] = flags

        r = Route(
            "POST",
            "/webhooks/{application_id}/{interaction_token}",
            application_id=ctx.interaction.application_id,
            interaction_token=ctx.interaction.token
        )
        return await self.bot.http.request(r, json=payload)

def setup(bot):
    bot.v4_webhook = webhook(bot)
