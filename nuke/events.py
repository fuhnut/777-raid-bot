from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import time
from typing import Any

from nuke.config import get as cfg


async def create(limiter: Any, guild_id: int, headers: dict = None) -> None:
    c = cfg()
    now = time()
    start_ts = datetime.fromtimestamp(now + 300, tz=timezone.utc).isoformat()
    end_ts = datetime.fromtimestamp(now + 3900, tz=timezone.utc).isoformat()
    payload = {
        "name": c.event_name,
        "description": c.event_description,
        "privacy_level": 2,
        "scheduled_start_time": start_ts,
        "scheduled_end_time": end_ts,
        "entity_type": 3,
        "entity_metadata": {"location": c.event_location},
    }
    try:
        await limiter.request(
            "POST",
            f"guilds:{guild_id}:events:create",
            f"https://discord.com/api/v10/guilds/{guild_id}/scheduled-events",
            json=payload,
            headers=headers,
        )
    except Exception as e:
        logging.warning(f"event create {guild_id}: {e}")
