from __future__ import annotations

import logging

from discord import Interaction, Member

from models.config import config as cfg_type
from utils.member_cache import cachedmember, membercache
from utils.member_cache import get as get_member_cache


async def check(itx: Interaction, cache: membercache) -> bool:
    c = cfg_type()
    server_id = getattr(c, "required_server_id", 0)
    role_id = getattr(c, "required_role_id", 0)
    if server_id == 0 or role_id == 0:
        return True
    if not itx.guild or itx.guild.id != server_id:
        return False

    member = cache.get(itx.user.id)
    if member is None:
        try:
            fetched: Member = await itx.guild.fetch_member(itx.user.id)
            m = cachedmember(user_id=fetched.id, role_ids=[r.id for r in fetched.roles])
            cache.add(m)
            await cache.save(m)
            member = m
        except Exception:
            return False

    return role_id in member.role_ids
