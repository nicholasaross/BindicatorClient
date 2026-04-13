# ESP32-S3-GEEK Setup Log — 2026-04-13

## Objective
Install MicroPython on a Waveshare ESP32-S3-GEEK and get the integrated 1.14" ST7789 LCD and WiFi working.

## Hardware
- **Board:** Waveshare ESP32-S3-GEEK (USB-A dongle form factor)
- **Chip:** ESP32-S3R2 (QFN56, rev v0.2, dual core LX7 240MHz, 16MB flash, 2MB PSRAM)
- **Display:** 1.14" IPS LCD 135x240 pixels, 65K color, ST7789P3 controller
- **USB:** Native USB-Serial/JTAG (no external USB-to-serial chip)
- **MAC:** d0:cf:13:51:70:94

## Step 1: Connect to PC

Board plugged in via USB-A port. Windows detected `USB Serial Device (COM5)` with VID:PID `303A:1001` (Espressif native USB).

## Step 2: Flash MicroPython

Firmware: `ESP32_GENERIC_S3-20260406-v1.28.0.bin` (reused `micropython_s3.bin`).

**Important:** ESP32-S3 uses flash offset `0x0` (not `0x1000` like original ESP32).

```bash
esptool --port COM5 erase_flash                                           # 39.5 seconds
esptool --port COM5 --baud 460800 write_flash 0 micropython_s3.bin        # 15.5 seconds
```

**Note:** After flashing, the COM port changed from COM5 to COM6 (VID:PID changed from `303A:1001` to `303A:4001` — MicroPython's USB CDC).

REPL confirmed: MicroPython v1.28.0, ESP32_GENERIC_S3.

## Step 3: LCD Pin Mapping

Pin mapping sourced from Waveshare's official MicroPython example code (Kongduino/ESP32-S3-GEEK on GitHub):

| Signal    | GPIO |
|-----------|------|
| BL        | 7    |
| DC        | 8    |
| RST       | 9    |
| CS        | 10   |
| MOSI      | 11   |
| SCK       | 12   |

**SPI settings:** SPI(1), baudrate=40000000, polarity=0, phase=0
**Backlight:** PWM on GPIO 7, freq=1000, duty_u16=32768 (~50% brightness)

## Step 4: Display Driver

Reused the `st7789py` driver (russhughes/st7789py_mpy) from the IdeaSpark board — same ST7789 controller, just different pin mapping and SPI bus.

Display configured as 135x240 portrait (rotation=0). The `st7789py` driver handles this natively.

## Step 5: Demo Working

`test_geek.py` connects to WiFi and displays:
- Blue title bar with "WiFi Connected"
- SSID, IP address, RSSI in colour-coded text
- Signal strength bar chart
- Board name and MicroPython version in footer

WiFi connected on first attempt: IP 192.168.1.222, RSSI -66 dBm.

## Files on ESP32

```
/test_geek.py         — WiFi + display proof of concept
/config.py            — WiFi credentials and server URL
/lib/st7789py.py      — ST7789 display driver (russhughes)
/lib/vga2_8x16.py     — 8x16 VGA bitmap font
```

## Tools Used
- **esptool v5.2.0** — flashing firmware
- **mpremote v1.27.0** — file management and REPL
