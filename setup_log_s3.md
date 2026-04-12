# ESP32-S3 Setup Log — 2026-04-12

## Objective
Install MicroPython on a Heltec Wireless Paper V1.2 (sold as Binghe YY1-0032) and get the integrated E-Ink display and WiFi working.

## Hardware
- **Board:** Heltec Wireless Paper V1.2 (labelled "Binghe YY1-0032")
- **Chip:** ESP32-S3FN8 (QFN56, rev v0.2, dual core LX7 240MHz, 8MB flash, no PSRAM)
- **LoRa:** Semtech SX1262 (not used)
- **Display:** 2.13" E-Ink 250x122 pixels (black/white), panel E0213A367
- **Display controller:** SSD1682 (Solomon Systech) — NOT UC8151D/JD79656 (those are V1.1)
- **USB-to-serial:** Silicon Labs CP210x on COM4
- **MAC:** ac:a7:04:06:e8:18

## Step 1: Connect to PC

Board connected via USB-C data cable. Windows detected `Silicon Labs CP210x USB to UART Bridge (COM4)`.

## Step 2: Flash MicroPython

Firmware: `ESP32_GENERIC_S3-20260406-v1.28.0.bin` from micropython.org (1.7MB).

**Important:** ESP32-S3 uses flash offset `0x0` (not `0x1000` like original ESP32).

```bash
esptool --port COM4 erase_flash                                           # 4.3 seconds
esptool --port COM4 --baud 460800 write_flash 0 micropython_s3.bin        # 27.1 seconds
```

REPL confirmed: MicroPython v1.28.0, ESP32_GENERIC_S3, 225KB free RAM.

## Step 3: Identify Display Controller

**Problem:** Board is sold as a generic "Binghe" ESP32-S3 LoRa board but is actually a Heltec Wireless Paper V1.2 (silkscreen label on PCB: "Heltec WirelessPaperV1.2").

**What didn't work:**
- SSD1680 commands with Heltec V1.0/V1.1 init sequence — display unresponsive
- UC8151D commands (JD79656) — wrong controller for V1.2
- LILYGO T3-S3 E-Paper pin mapping — wrong board entirely

**Key discovery:** Heltec Wireless Paper V1.2 uses a **different display panel** (E0213A367) with an **SSD1682** controller, not the JD79656/UC8151D of V1.1. Critical differences:
- BUSY pin: HIGH = busy (opposite of V1.1)
- Requires command `0x37` (waveform register) with specific data `[0x40, 0x80, 0x03, 0x0E]`
- Data entry mode `0x00` (X--, Y--), cursor at (14, 249)
- 2-bit source pixel offset (122 pixels mapped to positions 0..121 in 128-bit stream)

**Solution:** Wrote custom SSD1682 driver based on Heltec's official `HT_E0213A367.h` library.

## Step 4: E-Ink Display Working

Driver: `depg0213.py` (custom, SSD1682, landscape 250x122 framebuffer with rotation).

The display is physically landscape but the controller addresses it portrait. The driver:
1. Exposes a 250x122 landscape framebuffer via MicroPython's `framebuf`
2. Rotates/transposes the buffer when sending to the controller
3. Handles the SSD1682's 2-bit source pixel offset

## Pin Mapping (Heltec Wireless Paper, all versions)

### E-Ink Display (SPI)
| Signal | GPIO |
|--------|------|
| MOSI   | 2    |
| CLK    | 3    |
| CS     | 4    |
| DC     | 5    |
| RST    | 6    |
| BUSY   | 7    |
| Vext   | 45   |

**Vext (GPIO 45):** Must be driven LOW to power the display. Drive HIGH to power off. Power cycle (HIGH 2s, then LOW) required for clean controller reset.

**BUSY (GPIO 7):** HIGH = busy, LOW = ready (SSD1682 convention). Use INPUT_PULLUP.

### LoRa SX1262 (SPI)
| Signal | GPIO |
|--------|------|
| NSS    | 8    |
| SCK    | 9    |
| MOSI   | 10   |
| MISO   | 11   |
| RST    | 12   |
| BUSY   | 13   |
| DIO1   | 14   |

## Files on ESP32

```
/test_s3.py           — WiFi + display proof of concept
/config.py            — WiFi credentials and server URL
/lib/depg0213.py      — SSD1682 E-Ink display driver
```

## Tools Used
- **esptool v5.2.0** — flashing firmware
- **mpremote v1.27.0** — file management and REPL
