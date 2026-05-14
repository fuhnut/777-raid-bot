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
        
        if content and not is_v2:
            payload["content"] = content

        if view:
            payload["components"] = view
        
        if flags:
            payload["flags"] = flags
            
        payload["allowed_mentions"] = {"parse": ["users", "roles", "everyone"]}
        payload["tts"] = True

        itx = getattr(ctx, "interaction", ctx)
        app_id = application_id or itx.application_id
        itx_token = token or itx.token

        url = f"https://discord.com/api/v10/webhooks/{app_id}/{itx_token}"
        bucket = f"webhooks:{app_id}:{itx_token}"
        headers = {"Content-Type": "application/json"}

        res = await self.bot.http.fast_limiter.request(
            "POST",
            bucket,
            url,
            headers=headers,
            json=payload
        )
        
        import logging
        if res.status >= 300:
            try:
                err = await res.json()
            except:
                err = await res.text()
            logging.error(f"webhook error {res.status}: {err}")
            return err
            
        try:
            return await res.json()
        except Exception:
            return await res.text()

def setup(bot):
    from utils.ratelimit import apilimiter
    if not hasattr(bot.http, "fast_limiter"):
        bot.http.fast_limiter = apilimiter(bot.http)
    bot.v4_webhook = webhook(bot)
