from __future__ import annotations

from msgspec import Struct as struct


class cachedmember(struct, kw_only=True):
    user_id: int
    role_ids: list[int]
