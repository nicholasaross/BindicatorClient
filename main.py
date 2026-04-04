from machine import Pin, SPI
import st7789py as st7789
import vga2_8x16 as font
import time

# IdeaSpark ESP-WROOM-32 1.14" ST7789 135x240 TFT pinout
spi = SPI(2, baudrate=20000000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23))
display = st7789.ST7789(
    spi,
    135,
    240,
    reset=Pin(4, Pin.OUT),
    dc=Pin(2, Pin.OUT),
    cs=Pin(15, Pin.OUT),
    backlight=Pin(32, Pin.OUT),
)

# Clear screen to black
display.fill(st7789.BLACK)

# Draw colored bars
display.fill_rect(0, 0, 135, 40, st7789.RED)
display.fill_rect(0, 40, 135, 40, st7789.GREEN)
display.fill_rect(0, 80, 135, 40, st7789.BLUE)

# Display text
display.text(font, "Hello World!", 4, 140, st7789.WHITE, st7789.BLACK)
display.text(font, "ESP32 + ST7789", 4, 160, st7789.YELLOW, st7789.BLACK)
display.text(font, "135x240 TFT", 4, 180, st7789.CYAN, st7789.BLACK)

print("Display initialized OK")
