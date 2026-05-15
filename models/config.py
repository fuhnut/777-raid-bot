from __future__ import annotations

from msgspec import Struct

class config(Struct):
    token: str
    invite: str
    database_key: str
    owners: list[int] = []
