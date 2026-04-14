"""Display and edit the icons in icons.txt with a grid overlay.

Click a cell to toggle it. Buttons (or shortcuts) to Save / Undo / Revert /
Refresh. Left/Right arrows or < / > buttons to switch icons. Run from the
repo root:
    py -3 tools/icons_view.py
"""
import tkinter as tk
from pathlib import Path

CELL = 36
PAD = 20
PREVIEW_CELL = 2
GRID_COLOR = "#bbbbbb"
MAJOR_COLOR = "#666666"
FILL = "#000000"
BG = "#ffffff"
UNDO_LIMIT = 200

ICONS_PATH = Path(__file__).resolve().parent.parent / "icons.txt"


def load_file():
    """Return (header_text, icons dict of name -> 16x16 list[list[str]])."""
    raw = ICONS_PATH.read_text().splitlines()
    header_lines = []
    for line in raw:
        s = line.strip()
        if s.startswith("==") and s.endswith("=="):
            break
        header_lines.append(line)
    while header_lines and header_lines[-1].strip() == "":
        header_lines.pop()
    header = "\n".join(header_lines)

    icons = {}
    name = None
    grid = []
    for line in raw:
        s = line.strip()
        if s.startswith("==") and s.endswith("=="):
            if name is not None and grid:
                icons[name] = grid
            name = s.strip("= ").strip()
            grid = []
        elif len(s) == 16 and set(s) <= {"#", "."}:
            grid.append([c for c in s])
    if name is not None and grid:
        icons[name] = grid
    return header, icons


def save_file(header, icons):
    parts = []
    if header:
        parts.append(header)
        parts.append("")
    for name, rows in icons.items():
        parts.append(f"== {name} ==")
        for row in rows:
            parts.append("".join(row))
        parts.append("")
    ICONS_PATH.write_text("\n".join(parts) + "\n")


header, icons = load_file()
names = list(icons.keys())
if not names:
    raise SystemExit("No icons found in icons.txt")

undo_stack = []
dirty = [False]
idx = [0]

root = tk.Tk()
root.title("icons.txt viewer")

size = CELL * 16 + PAD * 2
canvas = tk.Canvas(root, width=size, height=size, bg=BG, highlightthickness=0)
canvas.pack()

preview_size = PREVIEW_CELL * 16
preview = tk.Canvas(
    root, width=preview_size, height=preview_size, bg=BG, highlightthickness=1,
    highlightbackground=MAJOR_COLOR,
)
preview.pack(pady=(8, 0))

label = tk.Label(root, font=("Segoe UI", 14))
label.pack(pady=(4, 4))

nav = tk.Frame(root)
nav.pack(pady=(0, 4))
edit_bar = tk.Frame(root)
edit_bar.pack(pady=(0, 8))


def set_title():
    mark = " *" if dirty[0] else ""
    root.title(f"icons.txt viewer{mark}")


def draw():
    canvas.delete("all")
    preview.delete("all")
    rows = icons[names[idx[0]]]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                x0 = PAD + x * CELL
                y0 = PAD + y * CELL
                canvas.create_rectangle(
                    x0, y0, x0 + CELL, y0 + CELL,
                    fill=FILL, outline="",
                )
                px = x * PREVIEW_CELL
                py = y * PREVIEW_CELL
                preview.create_rectangle(
                    px, py, px + PREVIEW_CELL, py + PREVIEW_CELL,
                    fill=FILL, outline="",
                )
    for i in range(17):
        c = MAJOR_COLOR if i % 8 == 0 else GRID_COLOR
        w = 2 if i % 8 == 0 else 1
        x = PAD + i * CELL
        canvas.create_line(x, PAD, x, PAD + 16 * CELL, fill=c, width=w)
        y = PAD + i * CELL
        canvas.create_line(PAD, y, PAD + 16 * CELL, y, fill=c, width=w)
    label.config(text=f"{idx[0] + 1}/{len(names)}  -  {names[idx[0]]}")
    set_title()


def step(delta):
    idx[0] = (idx[0] + delta) % len(names)
    draw()


def cell_at(event):
    x = (event.x - PAD) // CELL
    y = (event.y - PAD) // CELL
    if 0 <= x < 16 and 0 <= y < 16:
        return int(x), int(y)
    return None


def push_undo(name, rows):
    undo_stack.append((name, [row[:] for row in rows]))
    if len(undo_stack) > UNDO_LIMIT:
        del undo_stack[: len(undo_stack) - UNDO_LIMIT]


def toggle(event):
    pos = cell_at(event)
    if pos is None:
        return
    x, y = pos
    name = names[idx[0]]
    rows = icons[name]
    push_undo(name, rows)
    rows[y][x] = "." if rows[y][x] == "#" else "#"
    dirty[0] = True
    draw()


def undo():
    if not undo_stack:
        return
    name, rows = undo_stack.pop()
    icons[name] = rows
    if name in names:
        idx[0] = names.index(name)
    dirty[0] = bool(undo_stack)
    draw()


def save():
    save_file(header, icons)
    undo_stack.clear()
    dirty[0] = False
    set_title()


def revert():
    global header, icons, names
    current = names[idx[0]] if names else None
    header, icons = load_file()
    names = list(icons.keys())
    undo_stack.clear()
    dirty[0] = False
    if not names:
        label.config(text="(no icons in icons.txt)")
        canvas.delete("all")
        preview.delete("all")
        set_title()
        return
    idx[0] = names.index(current) if current in names else 0
    draw()


# Refresh = same as revert (re-read disk); kept as alias for the F5 muscle memory.
refresh = revert


tk.Button(nav, text="<", width=3, command=lambda: step(-1)).pack(side="left", padx=4)
tk.Button(nav, text=">", width=3, command=lambda: step(1)).pack(side="left", padx=4)

tk.Button(edit_bar, text="Save", command=save).pack(side="left", padx=4)
tk.Button(edit_bar, text="Undo", command=undo).pack(side="left", padx=4)
tk.Button(edit_bar, text="Revert", command=revert).pack(side="left", padx=4)
tk.Button(edit_bar, text="Refresh", command=refresh).pack(side="left", padx=4)

root.bind("<Left>", lambda _e: step(-1))
root.bind("<Right>", lambda _e: step(1))
root.bind("<F5>", lambda _e: refresh())
root.bind("<Control-s>", lambda _e: save())
root.bind("<Control-z>", lambda _e: undo())
root.bind("<Escape>", lambda _e: root.destroy())
canvas.bind("<Button-1>", toggle)
canvas.bind("<B1-Motion>", toggle)

draw()
root.mainloop()
