import random

def gen_glitch(length=1800):
    ranges = [
        (0x0021, 0x007E), # ASCII
        (0x0400, 0x04FF), # Cyrillic
        (0x0530, 0x058F), # Armenian
        (0x0600, 0x06FF), # Arabic
        (0x2C00, 0x2C5F), # Glagolitic
        (0x3040, 0x309F), # Hiragana
        (0x30A0, 0x30FF), # Katakana
        (0x4E00, 0x9FFF), # CJK Unified Ideographs
        (0xAC00, 0xD7AF), # Hangul
        (0x0300, 0x036F), # Combining Diacritical Marks (Zalgo)
    ]
    chars = []
    for _ in range(length):
        r = random.choice(ranges)
        chars.append(chr(random.randint(r[0], r[1])))
    return "".join(chars)

prefixes = ["@everyone @here discordapp.com/invite/xAeKGTD8Et"]
suffixes = ["# SPAMMED BY 767", "# 767 OWNS YOU", "# BOT FREE TO USE", "# JOIN 767 NOW", "# FREE OPEN SOURCE"]  

messages = []
for i in range(10):
    msg = f"{prefixes[0]} {gen_glitch()}\n\n{random.choice(suffixes)}"
    messages.append(msg)

import json
content = json.dumps(messages, indent=4, ensure_ascii=False)
with open("messages.jsonc", "w", encoding="utf-8") as f:
    f.write("// Please have an actual understanding of json before modifying this\n")
    f.write(content)
