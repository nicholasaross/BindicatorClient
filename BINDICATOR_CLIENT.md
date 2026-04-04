# Bindicator Client

A MicroPython application for the IdeaSpark ESP-WROOM-32 with integrated ST7789 TFT display. It fetches upcoming bin collection data from a Bindicator Server and displays colour-coded bars for each collection type.

## How it works

1. On boot, the ESP32 connects to WiFi
2. Makes an HTTP GET request to the Bindicator Server at `/next`
3. Receives a JSON response indicating the next collection date and which bin types are being collected
4. Displays a colour-coded bar for each active bin type, plus a date bar at the bottom
5. Refreshes every hour

### Example server response

```json
{"date": "2026-04-10", "bins": ["Food waste", "Garden waste", "Paper and cardboard"]}
```

### Display layout

The 135x240 pixel display is divided into equally-sized horizontal regions. Only bin types present in the server response are shown, plus a date bar at the bottom. Text is centred both horizontally and vertically within each region.

| Bin type             | Background colour |
|----------------------|-------------------|
| Refuse               | Green             |
| Mixed recycling      | Dark gray         |
| Food waste           | Red               |
| Paper and cardboard  | Blue              |
| Garden waste         | Yellow            |
| Date + day of week   | Black             |

"Paper and cardboard" is split across two lines to fit the 16-character display width.

### Error handling

- WiFi connection failure: retries every 30 seconds
- Server unreachable or request error: displays error message, retries every 60 seconds
- Successful fetch: refreshes after 1 hour

## Files

### On the ESP32

```
/main.py              - Boot entry point (imports and runs bindicator)
/bindicator.py        - Bindicator Client application
/config.py            - WiFi credentials and server URL (not in git)
/lib/st7789py.py      - ST7789 display driver
/lib/vga2_8x16.py     - 8x16 VGA bitmap font
```

### In the repository

| File               | Description                                      |
|--------------------|--------------------------------------------------|
| `bindicator.py`    | Main application script                          |
| `config.py`        | WiFi credentials and server URL (gitignored)     |
| `main.py`          | Original demo script (not deployed)              |
| `st7789py.py`      | ST7789 display driver (deployed to `/lib/`)      |
| `vga2_8x16.py`     | Bitmap font (deployed to `/lib/`)                |
| `setup_log.md`     | Hardware setup and pin discovery log             |

## Configuration

Create a `config.py` file (gitignored) with:

```python
WIFI_SSID = "your_ssid"
WIFI_PASSWORD = "your_password"
SERVER_URL = "http://192.168.1.10:8000/next"
```

Note: MicroPython cannot resolve local hostnames (e.g. `synology`), so the server URL must use an IP address.

## Deployment

Upload files to the ESP32 using `mpremote`:

```bash
py -3 -m mpremote connect COM3 cp config.py :config.py
py -3 -m mpremote connect COM3 cp bindicator.py :bindicator.py
py -3 -m mpremote connect COM3 reset
```

## Hardware

- **Board:** IdeaSpark ESP-WROOM-32 (ESP32-D0WD, dual core 240MHz)
- **Display:** 1.14" ST7789 135x240 TFT LCD
- **Firmware:** MicroPython v1.27.0
- **USB-to-serial:** CH340 on COM3

### SPI pin mapping

| Signal    | GPIO |
|-----------|------|
| MOSI      | 23   |
| SCLK      | 18   |
| CS        | 15   |
| DC        | 2    |
| RST       | 4    |
| Backlight | 32   |
