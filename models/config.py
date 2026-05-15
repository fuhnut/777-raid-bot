from __future__ import annotations

from msgspec import Struct

class config(Struct):
    token: str
    invite: str
    owners: list[int] = []
