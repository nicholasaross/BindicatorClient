"""Re-encode icons.txt back into the BIN_ICONS bytes format.

Reads icons.txt from the repo root and prints a Python literal ready to paste
into bindicator.py. Run from the repo root: py -3 tools/icons_from_text.py
"""
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
text = (repo / "icons.txt").read_text().splitlines()

icons = {}
name = None
grid = []
for line in text:
    s = line.strip()
    if s.startswith("==") and s.endswith("=="):
        if name is not None:
            icons[name] = grid
        name = s.strip("= ").strip()
        grid = []
    elif len(s) == 16 and set(s) <= {"#", "."}:
        grid.append(s)
if name is not None:
    icons[name] = grid

for key, rows in icons.items():
    if len(rows) != 16:
        raise SystemExit(f"{key!r}: expected 16 rows, got {len(rows)}")

def encode(rows):
    out = []
    for row in rows:
        bits = "".join("0" if c == "#" else "1" for c in row)
        out.append(int(bits[:8], 2))
        out.append(int(bits[8:], 2))
    return out

for name, rows in icons.items():
    bs = encode(rows)
    print(f'    "{name}": bytes([')
    for i in range(0, 32, 8):
        chunk = ", ".join(f"0x{b:02X}" for b in bs[i:i+8])
        print(f"        {chunk},")
    print("    ]),")
