# Bindicator Client

A MicroPython application that fetches upcoming bin collection data from a Bindicator Server and displays it on an ESP32 with an attached screen. Supports three boards with two display types (colour TFT and monochrome e-ink).

## How it works

1. On boot, the ESP32 connects to WiFi (up to 5 attempts with progress display)
2. Makes an HTTP GET request to the Bindicator Server at `/next`
3. Receives a JSON response indicating the next collection date and which bin types are being collected
4. Displays a bar for each active bin type, plus a date and WiFi signal strength indicator
5. Refreshes the data every hour

### Example server response

```json
{"date": "2026-04-10", "bins": ["Food waste", "Garden waste", "Paper and cardboard"]}
```

### Display layout

#### TFT boards (IdeaSpark, Waveshare Geek)

The 135x240 pixel display is divided into equally-sized horizontal colour-coded regions. Only bin types present in the server response are shown, plus a status bar at the bottom.

| Bin type             | Background colour |
|----------------------|-------------------|
| Refuse               | Green             |
| Mixed recycling      | Dark gray         |
| Food waste           | Red               |
| Paper and cardboard  | Blue              |
| Garden waste         | Yellow            |
| Date + WiFi signal   | Black             |

The WiFi signal indicator updates every 60 seconds between data refreshes.

#### E-Ink board (Heltec Wireless Paper)

The 250x122 monochrome display shows a header with date and WiFi signal, then lists each active bin with a 16x16 pixel icon and name, separated by horizontal lines. Icons provide visual distinction without colour:

| Bin type             | Icon              |
|----------------------|-------------------|
| Refuse               | Wheelie bin       |
| Mixed recycling      | Bottle            |
| Food waste           | Apple             |
| Paper and cardboard  | Document          |
| Garden waste         | Leaf              |

The e-ink display refreshes only when data changes (no periodic RSSI updates, as each full refresh takes ~1.5 seconds).

## Supported Boards

| Board | Display | COM | BOARD= |
|-------|---------|-----|--------|
| IdeaSpark ESP-WROOM-32 | 1.14" ST7789 TFT 135x240 | COM3 | `"ideaspark"` |
| Waveshare ESP32-S3-GEEK | 1.14" ST7789 TFT 135x240 | COM6 | `"geek"` |
| Heltec Wireless Paper V1.2 | 2.13" SSD1682 E-Ink 250x122 | COM4 | `"heltec"` |

## Files

### On each ESP32

```
/bindicator.py        - Main application
/boards.py            - Board hardware definitions
/config.py            - WiFi credentials, server URL, board selection
/lib/                 - Display drivers (board-specific)
```

TFT boards need `/lib/st7789py.py` and `/lib/vga2_8x16.py`. The Heltec board needs `/lib/depg0213.py`.

### In the repository

| File               | Description                                      |
|--------------------|--------------------------------------------------|
| `bindicator.py`    | Main application script (multi-board)            |
| `boards.py`        | Board hardware definitions and display init      |
| `config.py`        | WiFi credentials, server URL, board (gitignored) |
| `st7789py.py`      | ST7789 TFT driver (deployed to `/lib/`)          |
| `vga2_8x16.py`     | 8x16 bitmap font for TFT (deployed to `/lib/`)   |
| `depg0213.py`      | SSD1682 E-Ink driver (deployed to `/lib/`)        |
| `setup_log.md`     | IdeaSpark setup log                              |
| `setup_log_s3.md`  | Heltec Wireless Paper setup log                  |
| `setup_log_geek.md`| Waveshare ESP32-S3-GEEK setup log                |

## Configuration

Create a `config.py` file (gitignored) with:

```python
BOARD = "ideaspark"  # or "geek" or "heltec"
WIFI_SSID = "your_ssid"
WIFI_PASSWORD = "your_password"
SERVER_URL = "http://192.168.1.10:8000/next"
```

Note: MicroPython cannot resolve local hostnames (e.g. `synology`), so the server URL must use an IP address.

## Deployment

Upload files to a board using `mpremote`:

```bash
# Example: deploy to Waveshare Geek (COM6)
py -3 -m mpremote connect COM6 cp config.py :config.py
py -3 -m mpremote connect COM6 cp bindicator.py :bindicator.py
py -3 -m mpremote connect COM6 cp boards.py :boards.py
py -3 -m mpremote connect COM6 mkdir :lib
py -3 -m mpremote connect COM6 cp st7789py.py :lib/st7789py.py
py -3 -m mpremote connect COM6 cp vga2_8x16.py :lib/vga2_8x16.py
```

To test:

```bash
py -3 -m mpremote connect COM6 exec "import bindicator; bindicator.main()"
```
