# CLAUDE.md

Guidance for working in this repo. The README covers user-facing setup; this file captures things that aren't obvious from reading the code.

## Project

A **MicroPython** Bindicator client. On boot, an ESP32 connects to WiFi, fetches the next bin collection date from a server, and renders it on a small attached display. Polls hourly. See `README.md` for the user-facing overview and JSON contract.

## Runtime: MicroPython, not CPython

The `pyproject.toml` (`requires-python = ">=3.14"`) describes the host venv only — used for tooling (`mpremote`, `esptool`). All code in `bindicator.py`, `boards.py`, `st7789py.py`, `depg0213.py`, `vga2_8x16.py`, `main.py`, and `test_*.py` runs **on-device under MicroPython**. Implications:

- No `str.ljust()` / `str.center()` / `str.rjust()` — use manual padding (see `_pad`/`_center` in `bindicator.py`).
- Use `urequests` (with fallback to `requests`), not the host `requests` library.
- Use `time.sleep_ms()` and `time.localtime((y,m,d,h,mi,s,wd,yd))` — note the 8-tuple form.
- Use `framebuf.MONO_HLSB` for monochrome bitmaps; `framebuf.FrameBuffer.blit(fb, x, y, key)` with `key=1` makes white pixels transparent on e-ink.
- MicroPython **cannot resolve local hostnames** — `SERVER_URL` in `config.py` must be an IP address.
- Avoid CPython-only stdlib (`typing`, `dataclasses`, `pathlib`, `logging`, `argparse`, etc.).

## Architecture

Single shared application (`bindicator.py`) targets three boards via a board-config dict (`boards.py`). The `init_display(BOARD)` factory returns a `(display, board_dict)` tuple; the main loop branches on two capability flags:

- `board["color"]` — True → ST7789 TFT path (RGB565, immediate); False → e-ink path (1-bit, deferred).
- `board["deferred"]` — True → display requires explicit `update()` to flush (e-ink); skip in-loop RSSI refreshes.

Module-level shims (`_draw_text`, `_flush`, `_color565`, `FG`, `BG`) are bound once in `main()` based on display type so the rest of the rendering code is driver-agnostic.

### Supported boards (`boards.py`)

| Board       | MCU         | Display                | Driver     | COM   |
|-------------|-------------|------------------------|------------|-------|
| `ideaspark` | ESP32-WROOM | 1.14" ST7789 135×240   | `st7789py` | COM3  |
| `geek`      | ESP32-S3    | 1.14" ST7789 135×240   | `st7789py` | COM6  |
| `heltec`    | ESP32-S3    | 2.13" SSD1682 250×122  | `depg0213` | COM4  |

The board dict is the single source of truth for pin mapping, SPI config, font metrics, and capability flags. To add a new board, add an entry plus a branch in `init_display`.

### File layout on-device vs. in-repo

In the repo, drivers sit alongside the app for easy editing. On-device they live under `/lib/`:

```
/bindicator.py
/boards.py
/config.py        (per-device, gitignored in repo)
/lib/st7789py.py  (TFT boards)
/lib/vga2_8x16.py (TFT boards)
/lib/depg0213.py  (Heltec only)
```

`config.py` is **gitignored** — it carries WiFi credentials, the server URL, and `BOARD = "..."`. Never commit it.

## Working with the device

Deployment and REPL go through `mpremote` (run from the host venv):

```bash
py -3 -m mpremote connect COM6 cp bindicator.py :bindicator.py
py -3 -m mpremote connect COM6 cp boards.py    :boards.py
py -3 -m mpremote connect COM6 cp config.py    :config.py
py -3 -m mpremote connect COM6 mkdir :lib
py -3 -m mpremote connect COM6 cp st7789py.py  :lib/st7789py.py
py -3 -m mpremote connect COM6 cp vga2_8x16.py :lib/vga2_8x16.py
# Heltec only:
py -3 -m mpremote connect COM4 cp depg0213.py  :lib/depg0213.py

# Run from REPL without flashing as main:
py -3 -m mpremote connect COM6 exec "import bindicator; bindicator.main()"
```

`micropython.bin` (ESP32) and `micropython_s3.bin` (ESP32-S3) are checked in for reflashing via `esptool`.

`test_s3.py` and `test_geek.py` are bring-up smoke tests for the S3 boards — not a unit-test suite. There is no `pytest`-style test rig.

## Gotchas captured from prior bring-up (see `setup_log*.md`)

- ESP32 SPI baudrate ceiling is ~26.6 MHz. The IdeaSpark uses 20 MHz; pushing higher caused crash loops. The S3 boards tolerate 40 MHz.
- The `st7789py` driver expects a **row-major** font (one byte per row, MSB = leftmost pixel). Column-major fonts render garbled; mirrored output came from a custom 8×8 font — `vga2_8x16.py` is the known-good choice.
- The Heltec e-ink needs `vext` powered on before SPI talks to the panel; full refresh takes ~1.5 s, which is why the e-ink path skips per-minute RSSI updates.
- USB-C "charge-only" cables look identical to data cables but `esptool` will report "Found 0 serial ports". Try a different cable before debugging drivers.

## Conventions

- Keep `bindicator.py` driver-agnostic — branch on `board["color"]` / `board["deferred"]`, not on board name.
- New per-board hardware quirks belong in `boards.py` (as a flag or value) and in the `init_display` branch, not sprinkled through the app.
- Don't add CPython-only dependencies. If a helper is needed on-device, write it in MicroPython-compatible style.
