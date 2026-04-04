from machine import Pin, SPI
import st7789py as st7789
import vga2_8x16 as font
import network
import time

from config import WIFI_SSID, WIFI_PASSWORD, SERVER_URL

POLL_INTERVAL_S = 3600

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


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return True
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    for _ in range(30):
        if wlan.isconnected():
            return True
        time.sleep_ms(500)
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
    y, m, d = [int(x) for x in data["date"].split("-")]
    weekday = time.localtime(time.mktime((y, m, d, 0, 0, 0, 0, 0)))[6]
    regions.append(([DAYS[weekday], data["date"]], st7789.BLACK))
    n = len(regions)
    region_h = HEIGHT // n
    y = 0
    for i, (lines, color) in enumerate(regions):
        h = region_h if i < n - 1 else HEIGHT - y
        draw_region(display, y, h, color, lines)
        y += h


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
        display.fill(st7789.BLACK)
        display.text(font, "Connecting...", 4, 112, st7789.WHITE, st7789.BLACK)

        if not connect_wifi():
            show_error(display, "WiFi failed")
            time.sleep(30)
            continue

        try:
            data = fetch_data()
            render(display, data)
            time.sleep(POLL_INTERVAL_S)
        except Exception as e:
            show_error(display, str(e))
            time.sleep(60)


if __name__ == "__main__":
    main()
