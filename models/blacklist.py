from msgspec import Struct

class blacklistdata(Struct):
    users: list[int] = []
    servers: list[int] = []
