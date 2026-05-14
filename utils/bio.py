import logging
import discord.http

async def update_bio(bot):
    payload = {
        "description": "Raid bot source code https://github.com/fuhnut/raid-bot-v4/tree/main"
    }
    try:
        await bot.http.request(
            discord.http.Route(
                "PATCH",
                "/applications/@me"
            ),
            json=payload
        )
        logging.info("application bio updated successfully")
    except Exception as error:
        logging.error(f"failed to update bio: {error}") 
