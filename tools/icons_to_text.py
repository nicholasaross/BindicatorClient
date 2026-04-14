"""Dump the BIN_ICONS dict from bindicator.py as editable ASCII art.

Each icon is rendered as a 16x16 grid using '#' (black/drawn) and '.' (white).
Run from the repo root: py -3 tools/icons_to_text.py > icons.txt
"""
import importlib.util
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bindicator", repo / "bindicator.py")
# We only need the BIN_ICONS dict; stub the MicroPython-only imports.
sys.modules.setdefault("network", type(sys)("network"))
sys.modules.setdefault("framebuf", type(sys)("framebuf"))
fake_config = type(sys)("config")
fake_config.WIFI_SSID = fake_config.WIFI_PASSWORD = fake_config.SERVER_URL = ""
fake_config.BOARD = "ideaspark"
sys.modules.setdefault("config", fake_config)
fake_boards = type(sys)("boards")
fake_boards.init_display = lambda *_a, **_k: (None, {})
sys.modules.setdefault("boards", fake_boards)

mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

BLACK, WHITE = "#", "."

def decode(icon_bytes):
    rows = []
    for r in range(16):
        b1, b2 = icon_bytes[r * 2], icon_bytes[r * 2 + 1]
        bits = f"{b1:08b}{b2:08b}"
        rows.append("".join(BLACK if b == "0" else WHITE for b in bits))
    return rows


ORDER = ["Refuse", "Mixed recycling", "Food waste", "Paper and cardboard", "Garden waste"]

print("# 16x16 MONO_HLSB icons for the e-ink display")
print("# '#' = black (drawn), '.' = white (background, transparent with key=1)")
print("# Edit the grids below, then run tools/icons_from_text.py to re-encode.")
print()
for name in ORDER:
    print(f"== {name} ==")
    for row in decode(mod.BIN_ICONS[name]):
        print(row)
    print()
