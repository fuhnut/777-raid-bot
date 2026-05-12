from msgspec import Struct

class config(Struct):
    token: str
    invite: str
