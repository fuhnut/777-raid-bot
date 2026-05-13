from __future__ import annotations

class webhook:
    __slots__ = ("bot",)

    def __init__(self, bot):
        self.bot = bot

    async def send(
        self,
        ctx=None,
        content: str | None = None,
        view: list | None = None,
        is_v2: bool = False,
        silent: bool = False,
        application_id: str | None = None,
        token: str | None = None
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
            
        payload["allowed_mentions"] = {"parse": ["users", "roles", "everyone"]}

        app_id = application_id or ctx.interaction.application_id
        itx_token = token or ctx.interaction.token

        if not hasattr(self.bot.http, "fast_limiter"):
            from utils.ratelimit import apilimiter
            session = getattr(self.bot.http, "_HTTPClient__session", getattr(self.bot.http, "_session", None))
            self.bot.http.fast_limiter = apilimiter(session)

        url = f"https://discord.com/api/v10/webhooks/{app_id}/{itx_token}"
        bucket = f"webhooks:{app_id}"
        headers = {"Content-Type": "application/json"}

        res = await self.bot.http.fast_limiter.request(
            "POST",
            bucket,
            url,
            headers=headers,
            json=payload
        )
        
        if res.status in (204, 304):
            return None
        try:
            return await res.json()
        except Exception:
            return await res.text()

def setup(bot):
    bot.v4_webhook = webhook(bot)
