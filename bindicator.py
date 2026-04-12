from machine import Pin, SPI
import st7789py as st7789
import vga2_8x16 as font
import network
import time

from config import WIFI_SSID, WIFI_PASSWORD, SERVER_URL

POLL_INTERVAL_S = 3600

# WiFi retry settings
WIFI_MAX_ATTEMPTS = 5
WIFI_POLL_INTERVAL_MS = 500
WIFI_POLL_COUNT = 20        # 20 x 500ms = 10s per attempt
WIFI_RETRY_DELAY_S = 5
WIFI_FAIL_SLEEP_S = 10
RSSI_UPDATE_S = 60

WIFI_STATUS_TEXT = {
    1000: "Idle",
    1001: "Connecting...",
    1010: "Got IP",
    201:  "No AP found",
    202:  "Wrong password",
    203:  "Connect fail",
    204:  "Beacon timeout",
    205:  "Assoc fail",
}

# Display constants
WIDTH = 135
HEIGHT = 240
FONT_W = 8
FONT_H = 16

# Colors
COLOR_GREEN = st7789.color565(0, 160, 0)
COLOR_DARK_GRAY = st7789.color565(80, 80, 80)
COLOR_BLUE = st7789.BLUE
COLOR_YELLOW = st7789.color565(200, 180, 0)
COLOR_RED = st7789.RED

# Bin types in display order: (json_name, bg_color, text_lines)
BIN_CONFIG = [
    ("Refuse",               COLOR_GREEN,     ["Refuse"]),
    ("Mixed recycling",      COLOR_DARK_GRAY, ["Mixed recycling"]),
    ("Food waste",           COLOR_RED,       ["Food waste"]),
    ("Paper and cardboard",  COLOR_BLUE,      ["Paper and", "cardboard"]),
    ("Garden waste",         COLOR_YELLOW,    ["Garden waste"]),
]


def init_display():
    spi = SPI(2, baudrate=20000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23))
    return st7789.ST7789(
        spi, 135, 240,
        reset=Pin(4, Pin.OUT),
        dc=Pin(2, Pin.OUT),
        cs=Pin(15, Pin.OUT),
        backlight=Pin(32, Pin.OUT),
    )


def _pad(s, w=16):
    s = s[:w]
    return s + " " * (w - len(s))


def _center(s, w=16):
    s = s[:w]
    p = w - len(s)
    return " " * (p // 2) + s + " " * (p - p // 2)


def show_wifi_status(display, attempt, max_attempts, status_text, dots=0, full_redraw=True):
    if full_redraw:
        display.fill(st7789.BLACK)
        title = "WiFi"
        x = (WIDTH - len(title) * FONT_W) // 2
        display.text(font, title, x, 32, st7789.WHITE, st7789.BLACK)
        att = "Attempt {} of {}".format(attempt, max_attempts)
        x = (WIDTH - len(att) * FONT_W) // 2
        display.text(font, att, x, 64, st7789.WHITE, st7789.BLACK)
    # Pad to 16 chars so background overwrites old text (no fill_rect flicker)
    display.text(font, _center(status_text), 0, 96, COLOR_YELLOW, st7789.BLACK)
    display.text(font, _pad("." * dots), 0, 128, COLOR_DARK_GRAY, st7789.BLACK)


def get_rssi():
    wlan = network.WLAN(network.STA_IF)
    try:
        if wlan.isconnected():
            return wlan.status('rssi')
    except:
        pass
    return 0


def rssi_text(rssi):
    if rssi == 0:
        return "WiFi: --", COLOR_DARK_GRAY
    if rssi >= -50:
        return "WiFi: Strong", COLOR_GREEN
    if rssi >= -60:
        return "WiFi: Good", COLOR_GREEN
    if rssi >= -70:
        return "WiFi: Fair", COLOR_YELLOW
    if rssi >= -80:
        return "WiFi: Weak", COLOR_RED
    return "WiFi: Poor", COLOR_RED


def draw_date_region(display, y, h, day_name, date_str, rssi):
    display.fill_rect(0, y, WIDTH, h, st7789.BLACK)
    label, rssi_color = rssi_text(rssi)
    lines_h = 3 * FONT_H
    text_y = y + (h - lines_h) // 2
    x = (WIDTH - len(day_name) * FONT_W) // 2
    display.text(font, day_name, x, text_y, st7789.WHITE, st7789.BLACK)
    text_y += FONT_H
    x = (WIDTH - len(date_str) * FONT_W) // 2
    display.text(font, date_str, x, text_y, st7789.WHITE, st7789.BLACK)
    text_y += FONT_H
    x = (WIDTH - len(label) * FONT_W) // 2
    display.text(font, label, x, text_y, rssi_color, st7789.BLACK)


def connect_wifi(display):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    for attempt in range(1, WIFI_MAX_ATTEMPTS + 1):
        if wlan.isconnected():
            return True
        show_wifi_status(display, attempt, WIFI_MAX_ATTEMPTS, "Connecting...", dots=0, full_redraw=True)
        if attempt > 1:
            try:
                wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            except:
                pass
        for poll in range(WIFI_POLL_COUNT):
            if wlan.isconnected():
                return True
            status = wlan.status()
            status_text = WIFI_STATUS_TEXT.get(status, "Status: {}".format(status))
            show_wifi_status(display, attempt, WIFI_MAX_ATTEMPTS, status_text, dots=(poll % 16) + 1, full_redraw=False)
            time.sleep_ms(WIFI_POLL_INTERVAL_MS)

        show_wifi_status(display, attempt, WIFI_MAX_ATTEMPTS, "Failed", dots=0, full_redraw=False)
        try:
            wlan.disconnect()
        except:
            pass
        time.sleep_ms(500)
        if attempt < WIFI_MAX_ATTEMPTS:
            time.sleep(WIFI_RETRY_DELAY_S)
    return False


def fetch_data():
    try:
        import urequests as requests
    except ImportError:
        import requests
    response = requests.get(SERVER_URL)
    try:
        data = response.json()
    finally:
        response.close()
    return data


def draw_region(display, y, height, bg_color, lines, fg_color=st7789.WHITE):
    display.fill_rect(0, y, WIDTH, height, bg_color)
    num_lines = len(lines)
    block_h = num_lines * FONT_H
    text_y = y + (height - block_h) // 2
    for line in lines:
        text_x = (WIDTH - len(line) * FONT_W) // 2
        display.text(font, line, text_x, text_y, fg_color, bg_color)
        text_y += FONT_H


def render(display, data):
    display.fill(st7789.BLACK)
    bins = data["bins"]
    regions = [(lines, color) for name, color, lines in BIN_CONFIG if name in bins]
    DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
    yr, mo, dy = [int(x) for x in data["date"].split("-")]
    weekday = time.localtime(time.mktime((yr, mo, dy, 0, 0, 0, 0, 0)))[6]
    day_name = DAYS[weekday]
    date_str = data["date"]
    n = len(regions) + 1
    region_h = HEIGHT // n
    y = 0
    for i, (lines, color) in enumerate(regions):
        h = region_h if i < n - 1 else HEIGHT - y
        draw_region(display, y, h, color, lines)
        y += h
    date_h = HEIGHT - y
    draw_date_region(display, y, date_h, day_name, date_str, get_rssi())
    return y, date_h, day_name, date_str


def show_error(display, msg):
    display.fill(st7789.BLACK)
    # Simple word wrap at 16 chars
    y = 4
    while msg and y + FONT_H <= HEIGHT:
        if len(msg) <= 16:
            line, msg = msg, ""
        else:
            brk = msg.rfind(" ", 0, 16)
            if brk <= 0:
                brk = 16
            line, msg = msg[:brk], msg[brk:].lstrip()
        display.text(font, line, 4, y, st7789.RED, st7789.BLACK)
        y += FONT_H


def main():
    display = init_display()

    while True:
        if not connect_wifi(display):
            show_error(display, "WiFi failed after {} attempts".format(WIFI_MAX_ATTEMPTS))
            time.sleep(WIFI_FAIL_SLEEP_S)
            continue

        time.sleep(2)  # let network stack settle after WiFi connect

        try:
            data = fetch_data()
            date_y, date_h, day_name, date_str = render(display, data)
            for _ in range(POLL_INTERVAL_S // RSSI_UPDATE_S):
                time.sleep(RSSI_UPDATE_S)
                draw_date_region(display, date_y, date_h, day_name, date_str, get_rssi())
        except Exception as e:
            show_error(display, str(e))
            time.sleep(60)


if __name__ == "__main__":
    main()
