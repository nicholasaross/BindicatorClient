import network
import time
import framebuf

from config import WIFI_SSID, WIFI_PASSWORD, SERVER_URL, BOARD
from boards import init_display

# --- Timing constants ---
POLL_INTERVAL_S = 3600
WIFI_MAX_ATTEMPTS = 5
WIFI_POLL_INTERVAL_MS = 500
WIFI_POLL_COUNT = 20
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

# --- Bin configuration ---
# (server_name, rgb_tuple for TFT color)
BIN_CONFIG = [
    ("Refuse",              (0, 160, 0)),
    ("Mixed recycling",     (80, 80, 80)),
    ("Food waste",          (255, 0, 0)),
    ("Paper and cardboard", (0, 0, 255)),
    ("Garden waste",        (200, 180, 0)),
]

# --- 16x16 monochrome icons for e-ink (MONO_HLSB format, 32 bytes each) ---
# In MONO_HLSB: 0 = black (drawn), 1 = white (background).
# Blit with key=1 so white pixels are transparent.
BIN_ICONS = {
    # Wheelie bin: wide lid, body, two wheels
    "Refuse": bytes([
        0xFF, 0xFF, 0xC0, 0x03, 0xE0, 0x07, 0xF0, 0x0F,
        0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F,
        0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F,
        0xF0, 0x0F, 0xE0, 0x07, 0xFB, 0xDF, 0xFF, 0xFF,
    ]),
    # Bottle silhouette: narrow neck, wide body
    "Mixed recycling": bytes([
        0xFF, 0xFF, 0xFC, 0x3F, 0xFC, 0x3F, 0xFE, 0x7F,
        0xFE, 0x7F, 0xFC, 0x3F, 0xF8, 0x1F, 0xF0, 0x0F,
        0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F,
        0xF0, 0x0F, 0xF0, 0x0F, 0xF0, 0x0F, 0xFF, 0xFF,
    ]),
    # Apple with stem and leaf
    "Food waste": bytes([
        0xFF, 0xFF, 0xFE, 0xFF, 0xFC, 0xFF, 0xF2, 0x3F,
        0xE1, 0x0F, 0xE0, 0x07, 0xC0, 0x03, 0xC0, 0x03,
        0xC0, 0x03, 0xC0, 0x03, 0xC0, 0x03, 0xE0, 0x07,
        0xE0, 0x07, 0xF0, 0x0F, 0xFC, 0x3F, 0xFF, 0xFF,
    ]),
    # Document with folded corner and text lines
    "Paper and cardboard": bytes([
        0xFF, 0xFF, 0xE0, 0x1F, 0xE0, 0x1F, 0xE7, 0x8F,
        0xE7, 0xCF, 0xE7, 0xCF, 0xE4, 0x4F, 0xE7, 0xCF,
        0xE4, 0x4F, 0xE7, 0xCF, 0xE4, 0x4F, 0xE7, 0xCF,
        0xE4, 0x4F, 0xE0, 0x1F, 0xFF, 0xFF, 0xFF, 0xFF,
    ]),
    # Leaf with central vein
    "Garden waste": bytes([
        0xFF, 0xFF, 0xFF, 0xDF, 0xFF, 0x9F, 0xFF, 0x1F,
        0xFE, 0x1F, 0xFC, 0x9F, 0xF9, 0x9F, 0xF3, 0x9F,
        0xE7, 0xBF, 0xCF, 0x7F, 0xCE, 0xFF, 0xE5, 0xFF,
        0xF3, 0xFF, 0xFB, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,
    ]),
}

# --- Module-level state (set in main()) ---
_font = None          # font module, loaded only for TFT boards
_draw_text = None     # function(display, s, x, y, fg, bg)
_flush = None         # function(display) — no-op for TFT, update() for e-ink
_color565 = None      # function(r, g, b) — RGB565 converter or returns 0
FG = 0                # foreground color (white on TFT, black on e-ink)
BG = 0                # background color (black on TFT, white on e-ink)


# --- Text helpers ---

def _pad(s, w):
    s = s[:w]
    return s + " " * (w - len(s))


def _center(s, w):
    s = s[:w]
    p = w - len(s)
    return " " * (p // 2) + s + " " * (p - p // 2)


def _wrap(name, max_w):
    """Word-wrap a string to fit max_w characters. Returns list of lines."""
    if len(name) <= max_w:
        return [name]
    brk = name.rfind(" ", 0, max_w)
    if brk <= 0:
        brk = max_w
    return [name[:brk], name[brk:].lstrip()]


def _parse_date(date_str):
    """Parse 'YYYY-MM-DD' and return (day_abbr, formatted_date)."""
    DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
    MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    yr, mo, dy = [int(x) for x in date_str.split("-")]
    weekday = time.localtime(time.mktime((yr, mo, dy, 0, 0, 0, 0, 0)))[6]
    day_name = DAYS[weekday]
    date_fmt = "{} {}".format(dy, MONTHS[mo - 1])
    return day_name, date_fmt


# --- WiFi helpers ---

def get_rssi():
    wlan = network.WLAN(network.STA_IF)
    try:
        if wlan.isconnected():
            return wlan.status('rssi')
    except:
        pass
    return 0


def rssi_text(rssi):
    """Return (label, color) for RSSI value. Color is RGB tuple or None."""
    if rssi == 0:
        return "WiFi: --", (80, 80, 80)
    if rssi >= -50:
        return "WiFi: Strong", (0, 160, 0)
    if rssi >= -60:
        return "WiFi: Good", (0, 160, 0)
    if rssi >= -70:
        return "WiFi: Fair", (200, 180, 0)
    if rssi >= -80:
        return "WiFi: Weak", (255, 0, 0)
    return "WiFi: Poor", (255, 0, 0)


# --- WiFi connection ---

def show_wifi_status(display, board, attempt, max_attempts, status_text,
                     dots=0, full_redraw=True):
    cpl = board["chars_per_line"]
    fw = board["font_w"]
    fh = board["font_h"]
    w = board["width"]

    if full_redraw:
        display.fill(BG)
        title = "WiFi"
        x = (w - len(title) * fw) // 2
        _draw_text(display, title, x, fh * 2, FG, BG)
        att = "Attempt {} of {}".format(attempt, max_attempts)
        x = (w - len(att) * fw) // 2
        _draw_text(display, att, x, fh * 4, FG, BG)

    _draw_text(display, _center(status_text, cpl), 0, fh * 6, _color565(200, 180, 0), BG)
    if not board["deferred"]:
        _draw_text(display, _pad("." * dots, cpl), 0, fh * 8, _color565(80, 80, 80), BG)


def connect_wifi(display, board):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    for attempt in range(1, WIFI_MAX_ATTEMPTS + 1):
        if wlan.isconnected():
            return True

        show_wifi_status(display, board, attempt, WIFI_MAX_ATTEMPTS,
                         "Connecting...", dots=0, full_redraw=True)
        _flush(display)

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

            if not board["deferred"]:
                show_wifi_status(display, board, attempt, WIFI_MAX_ATTEMPTS,
                                 status_text,
                                 dots=(poll % board["chars_per_line"]) + 1,
                                 full_redraw=False)
            time.sleep_ms(WIFI_POLL_INTERVAL_MS)

        show_wifi_status(display, board, attempt, WIFI_MAX_ATTEMPTS,
                         "Failed", dots=0, full_redraw=False)
        _flush(display)

        try:
            wlan.disconnect()
        except:
            pass
        time.sleep_ms(500)
        if attempt < WIFI_MAX_ATTEMPTS:
            time.sleep(WIFI_RETRY_DELAY_S)

    return False


# --- Data fetching ---

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


# --- TFT rendering (135x240, color) ---

def draw_region(display, board, y, height, bg_color, lines, fg_color):
    w = board["width"]
    fw = board["font_w"]
    fh = board["font_h"]
    display.fill_rect(0, y, w, height, bg_color)
    block_h = len(lines) * fh
    text_y = y + (height - block_h) // 2
    for line in lines:
        text_x = (w - len(line) * fw) // 2
        _draw_text(display, line, text_x, text_y, fg_color, bg_color)
        text_y += fh


def draw_date_region(display, board, y, h, day_name, date_str, rssi):
    w = board["width"]
    fw = board["font_w"]
    fh = board["font_h"]
    display.fill_rect(0, y, w, h, BG)
    label, rgb = rssi_text(rssi)
    rssi_color = _color565(*rgb)
    lines_h = 3 * fh
    text_y = y + (h - lines_h) // 2
    x = (w - len(day_name) * fw) // 2
    _draw_text(display, day_name, x, text_y, FG, BG)
    text_y += fh
    x = (w - len(date_str) * fw) // 2
    _draw_text(display, date_str, x, text_y, FG, BG)
    text_y += fh
    x = (w - len(label) * fw) // 2
    _draw_text(display, label, x, text_y, rssi_color, BG)


def draw_date_region_compact(display, board, y, h, date_line, rssi):
    """2-line date region for when vertical space is tight."""
    w = board["width"]
    fw = board["font_w"]
    fh = board["font_h"]
    display.fill_rect(0, y, w, h, BG)
    label, rgb = rssi_text(rssi)
    rssi_color = _color565(*rgb)
    lines_h = 2 * fh
    text_y = y + (h - lines_h) // 2
    x = (w - len(date_line) * fw) // 2
    _draw_text(display, date_line, x, text_y, FG, BG)
    text_y += fh
    x = (w - len(label) * fw) // 2
    _draw_text(display, label, x, text_y, rssi_color, BG)


def render_tft(display, board, data):
    """Render bin data on TFT display. Returns (date_y, date_h, day_name, date_str)."""
    w = board["width"]
    h = board["height"]
    cpl = board["chars_per_line"]
    fh = board["font_h"]

    display.fill(BG)
    bins = data["bins"]
    regions = []
    for name, rgb in BIN_CONFIG:
        if name in bins:
            lines = _wrap(name, cpl)
            color = _color565(*rgb)
            regions.append((lines, color))

    day_name, date_fmt = _parse_date(data["date"])

    n = len(regions) + 1
    region_h = h // n
    y = 0
    for i, (lines, color) in enumerate(regions):
        rh = region_h if i < n - 1 else h - y
        draw_region(display, board, y, rh, color, lines, FG)
        y += rh

    date_h = h - y
    # Use 2-line layout (day+date combined, wifi) if region is tight
    if date_h < 3 * fh:
        combined = "{} {}".format(day_name, date_fmt)
        draw_date_region_compact(display, board, y, date_h, combined, get_rssi())
    else:
        draw_date_region(display, board, y, date_h, day_name, date_fmt, get_rssi())
    return y, date_h, day_name, date_fmt


# --- E-Ink rendering (250x122, monochrome with icons) ---

def _draw_icon(display, icon_bytes, x, y):
    """Blit a 16x16 monochrome icon onto the e-ink framebuffer."""
    icon_fb = framebuf.FrameBuffer(bytearray(icon_bytes), 16, 16, framebuf.MONO_HLSB)
    display.fb.blit(icon_fb, x, y, 1)  # key=1: white is transparent


def render_eink(display, board, data):
    """Render bin data on e-ink display with icons. Returns None (no RSSI updates)."""
    W = board["width"]
    H = board["height"]
    fw = board["font_w"]
    fh = board["font_h"]

    display.fill(1)  # white background

    # Parse date
    bins = data["bins"]
    day_name, date_fmt = _parse_date(data["date"])
    day_str = "{} {}".format(day_name, date_fmt)

    # WiFi (shown once)
    rssi = get_rssi()
    wifi_label, _ = rssi_text(rssi)

    # Header: date left, WiFi right
    display.text(day_str, 4, 4, 0)
    rx = W - len(wifi_label) * fw - 4
    display.text(wifi_label, rx, 4, 0)
    display.hline(0, 14, W, 0)

    # Active bins in config order
    active = [name for name, _ in BIN_CONFIG if name in bins]

    if not active:
        msg = "No collections"
        mx = (W - len(msg) * fw) // 2
        display.text(msg, mx, (H - fh) // 2, 0)
    else:
        top_y = 18
        bot_y = H - 4
        avail = bot_y - top_y
        region_h = avail // len(active)

        for i, name in enumerate(active):
            ry = top_y + i * region_h

            # Icon (16x16) centered vertically in region
            icon_data = BIN_ICONS.get(name)
            icon_y = ry + (region_h - 16) // 2
            text_y = ry + (region_h - fh) // 2

            if icon_data:
                _draw_icon(display, icon_data, 20, icon_y)
                tx = 42  # after icon with gap
            else:
                tx = 20

            display.text(name, tx, text_y, 0)

            # Separator between bins
            if i < len(active) - 1:
                sep_y = ry + region_h
                display.hline(4, sep_y, W - 8, 0)

    # Bottom border
    display.hline(0, H - 3, W, 0)

    display.update()
    return None


# --- Shared rendering ---

def render(display, board, data):
    if board["color"]:
        return render_tft(display, board, data)
    else:
        return render_eink(display, board, data)


# --- Error display ---

def show_error(display, board, msg):
    fw = board["font_w"]
    fh = board["font_h"]
    cpl = board["chars_per_line"]
    h = board["height"]
    err_color = _color565(255, 0, 0)

    display.fill(BG)
    y = 4
    while msg and y + fh <= h:
        if len(msg) <= cpl:
            line, msg = msg, ""
        else:
            brk = msg.rfind(" ", 0, cpl)
            if brk <= 0:
                brk = cpl
            line, msg = msg[:brk], msg[brk:].lstrip()
        _draw_text(display, line, 4, y, err_color, BG)
        y += fh
    _flush(display)


# --- Main loop ---

def main():
    global _font, _draw_text, _flush, _color565, FG, BG

    display, board = init_display(BOARD)

    if board["color"]:
        import st7789py as st7789
        import vga2_8x16 as font_mod
        _font = font_mod
        _draw_text = lambda d, s, x, y, fg, bg: d.text(_font, s, x, y, fg, bg)
        _flush = lambda d: None
        _color565 = st7789.color565
        FG = st7789.WHITE
        BG = st7789.BLACK
    else:
        _draw_text = lambda d, s, x, y, fg, bg: d.text(s, x, y, fg)
        _flush = lambda d: d.update()
        _color565 = lambda r, g, b: 0  # all colors map to black
        FG = 0   # black text
        BG = 1   # white background

    while True:
        if not connect_wifi(display, board):
            show_error(display, board,
                       "WiFi failed after {} attempts".format(WIFI_MAX_ATTEMPTS))
            time.sleep(WIFI_FAIL_SLEEP_S)
            continue

        time.sleep(2)

        try:
            data = fetch_data()
            result = render(display, board, data)

            if board["deferred"]:
                # E-ink: sleep without screen updates
                time.sleep(POLL_INTERVAL_S)
            else:
                # TFT: periodic RSSI refresh
                date_y, date_h, day_name, date_str = result
                fh = board["font_h"]
                compact = date_h < 3 * fh
                if compact:
                    combined = "{} {}".format(day_name, date_str)
                for _ in range(POLL_INTERVAL_S // RSSI_UPDATE_S):
                    time.sleep(RSSI_UPDATE_S)
                    if compact:
                        draw_date_region_compact(display, board, date_y,
                                                 date_h, combined, get_rssi())
                    else:
                        draw_date_region(display, board, date_y, date_h,
                                         day_name, date_str, get_rssi())
        except Exception as e:
            show_error(display, board, str(e))
            time.sleep(60)


if __name__ == "__main__":
    main()
