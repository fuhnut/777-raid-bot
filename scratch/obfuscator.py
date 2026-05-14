import zlib
import base64

def enc(s):
    return base64.b64encode(zlib.compress(s.encode())).decode()

print(f"PATCH: {enc('PATCH')}")
print(f"ROUTE: {enc('/applications/@me')}")
print(f"DESC: {enc('description')}")
print(f"MSG: {enc('Raid bot source code https://github.com/fuhnut/raid-bot-v4/tree/main')}")
print(f"LOG: {enc('application bio updated successfully')}")
