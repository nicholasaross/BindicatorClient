# boards.py — Hardware definitions for all supported ESP32 boards
# Each board entry holds SPI config, pin mapping, display dimensions,
# font metrics, and capability flags.

from machine import Pin, SPI, PWM


BOARDS = {
    "ideaspark": {
        "spi_id": 2, "baudrate": 20_000_000,
        "sck": 18, "mosi": 23, "cs": 15, "dc": 2, "rst": 4,
        "bl": 32, "bl_pwm": False,
        "driver": "st7789", "width": 135, "height": 240,
        "font_w": 8, "font_h": 16, "chars_per_line": 16,
        "color": True, "deferred": False,
    },
    "geek": {
        "spi_id": 1, "baudrate": 40_000_000,
        "sck": 12, "mosi": 11, "cs": 10, "dc": 8, "rst": 9,
        "bl": 7, "bl_pwm": True,
        "driver": "st7789", "width": 135, "height": 240,
        "font_w": 8, "font_h": 16, "chars_per_line": 16,
        "color": True, "deferred": False,
    },
    "heltec": {
        "spi_id": 1, "baudrate": 6_000_000,
        "sck": 3, "mosi": 2, "cs": 4, "dc": 5, "rst": 6,
        "busy": 7, "vext": 45,
        "driver": "depg0213", "width": 250, "height": 122,
        "font_w": 8, "font_h": 8, "chars_per_line": 31,
        "color": False, "deferred": True,
    },
}


def init_display(board_name):
    """Initialise display hardware for the named board.

    Returns (display_object, board_dict).
    """
    b = BOARDS[board_name]
    spi = SPI(b["spi_id"], baudrate=b["baudrate"], polarity=0, phase=0,
              sck=Pin(b["sck"]), mosi=Pin(b["mosi"]))

    if b["driver"] == "st7789":
        import st7789py as st7789

        if b["bl_pwm"]:
            pwm = PWM(Pin(b["bl"]))
            pwm.freq(1000)
            pwm.duty_u16(32768)
            bl_pin = None
        else:
            bl_pin = Pin(b["bl"], Pin.OUT)

        display = st7789.ST7789(
            spi, b["width"], b["height"],
            reset=Pin(b["rst"], Pin.OUT),
            dc=Pin(b["dc"], Pin.OUT),
            cs=Pin(b["cs"], Pin.OUT),
            backlight=bl_pin,
        )
    elif b["driver"] == "depg0213":
        from depg0213 import DEPG0213
        display = DEPG0213(spi, cs=b["cs"], dc=b["dc"], rst=b["rst"],
                           busy=b["busy"], vext=b.get("vext"))

    return display, b
