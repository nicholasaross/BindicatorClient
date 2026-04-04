# ESP32 Setup Log — 2026-04-03

## Objective
Install MicroPython on an IdeaSpark ESP-WROOM-32 and get the integrated ST7789 TFT LCD screen working.

## Hardware
- **Board:** IdeaSpark ESP-WROOM-32 (ESP32-D0WD rev v1.0, dual core 240MHz, Wi-Fi + BT)
- **Display:** 1.14" ST7789 135x240 TFT LCD, ribbon cable connected (sealed unit)
- **USB-to-serial:** CH340 on COM3
- **MAC:** 8c:aa:b5:a3:de:80

## Step 1: Connect to PC

**Problem:** `esptool` reported "Found 0 serial ports".

**Cause:** The USB-C cable was charge-only (no data lines).

**Fix:** Swapped to a data-capable USB-C cable. Board powered on (red + blue LEDs). Windows detected `USB-SERIAL CH340 (COM3)`.

## Step 2: Flash MicroPython

```bash
esptool --port COM3 chip_id            # Verify connection
esptool --port COM3 erase_flash        # Erase existing firmware
esptool --port COM3 --baud 460800 write_flash -z 0x1000 micropython.bin
```

Firmware: `ESP32_GENERIC-20251209-v1.27.0.bin` from micropython.org.
Flash completed in ~29 seconds. REPL confirmed working at 115200 baud.

## Step 3: Identify Display Pins

**Problem:** Board has an integrated ST7789 TFT connected via ribbon cable. Pin mapping is not the common TTGO T-Display layout.

**What didn't work:**
- I2C scan (this is an SPI display, not I2C/OLED)
- TTGO T-Display pinout: MOSI=19, DC=16, RST=23, BL=4 — backlight didn't respond
- Toggling every GPIO for backlight — none worked with wrong pinout
- SPI baudrate=40000000 — exceeded ESP32 limit of ~26.6MHz, caused crash loop

**Solution:** Found correct pinout from product manual:

| Signal    | GPIO |
|-----------|------|
| MOSI      | 23   |
| SCLK      | 18   |
| CS        | 15   |
| DC        | 2    |
| RST       | 4    |
| Backlight | 32   |

**SPI settings:** baudrate=20000000, polarity=0, phase=0

## Step 4: Install ST7789 Driver

The official MicroPython package index does not include an ST7789 driver. Used the pure-Python driver from `russhughes/st7789py_mpy`:

```bash
# Downloaded st7789py.py locally, then uploaded via mpremote
mpremote connect COM3 mkdir :lib
mpremote connect COM3 cp st7789py.py :lib/st7789py.py
```

## Step 5: Font

The st7789py driver's `text()` method requires an external bitmap font module with:
- `WIDTH`, `HEIGHT`, `FIRST`, `LAST` attributes
- `FONT` bytes array in **row-major** order (each byte = one row, MSB = leftmost pixel)

Using `vga2_8x16.py` from the russhughes/st7789py_mpy `romfonts/` directory. This is an 8x16 VGA BIOS font — the most readable bitmap font included with the driver for a 135px-wide display.

**Gotcha:** The common 5x7 font format uses column-major byte order, which produces garbled output with this driver. Must use row-major.

**Gotcha:** A custom 8x8 font (`font8x8.py`) was tried first but displayed characters mirrored. The upstream `vga2_8x16.py` font resolved this.

## Step 6: Hello World App

Final working `main.py`:

```python
from machine import Pin, SPI
import st7789py as st7789
import vga2_8x16 as font
import time

spi = SPI(2, baudrate=20000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23))
display = st7789.ST7789(
    spi, 135, 240,
    reset=Pin(4, Pin.OUT),
    dc=Pin(2, Pin.OUT),
    cs=Pin(15, Pin.OUT),
    backlight=Pin(32, Pin.OUT),
)

display.fill(st7789.BLACK)
display.fill_rect(0, 0, 135, 40, st7789.RED)
display.fill_rect(0, 40, 135, 40, st7789.GREEN)
display.fill_rect(0, 80, 135, 40, st7789.BLUE)
display.text(font, "Hello World!", 4, 140, st7789.WHITE, st7789.BLACK)
display.text(font, "ESP32 + ST7789", 4, 160, st7789.YELLOW, st7789.BLACK)
display.text(font, "135x240 TFT", 4, 180, st7789.CYAN, st7789.BLACK)
```

## Files on ESP32

```
/main.py            — Hello world app
/lib/st7789py.py    — ST7789 display driver
/lib/vga2_8x16.py   — 8x16 VGA bitmap font (from russhughes/st7789py_mpy)
```

## Tools Used
- **esptool v5.2.0** — flashing firmware
- **mpremote v1.27.0** — file management and reset
- **pyserial** — REPL interaction
