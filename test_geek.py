# test_geek.py — Proof of concept: WiFi + LCD on Waveshare ESP32-S3-GEEK
# Connects to WiFi and displays the result on the 1.14" ST7789 LCD.

from machine import Pin, SPI, PWM
import network
import time
import st7789py as st7789
import vga2_8x16 as font
import config

# --- Pin definitions (Waveshare ESP32-S3-GEEK) ---
PIN_BL   = 7
PIN_DC   = 8
PIN_RST  = 9
PIN_CS   = 10
PIN_MOSI = 11
PIN_SCK  = 12

print("=== Waveshare ESP32-S3-GEEK Test ===")

# Enable backlight via PWM
bl_pwm = PWM(Pin(PIN_BL))
bl_pwm.freq(1000)
bl_pwm.duty_u16(32768)

# Init SPI and display (135x240, landscape via rotation=1 gives 240x135)
spi = SPI(1, baudrate=40_000_000, polarity=0, phase=0,
          sck=Pin(PIN_SCK), mosi=Pin(PIN_MOSI))
display = st7789.ST7789(
    spi, 135, 240,
    reset=Pin(PIN_RST, Pin.OUT),
    dc=Pin(PIN_DC, Pin.OUT),
    cs=Pin(PIN_CS, Pin.OUT),
    backlight=None,  # managed by PWM above
    rotation=0,
)

# Show connecting message
display.fill(st7789.BLACK)
display.text(font, "Connecting...", 4, 4, st7789.WHITE, st7789.BLACK)
display.text(font, config.WIFI_SSID, 4, 24, st7789.CYAN, st7789.BLACK)

# Connect to WiFi
print("Connecting to WiFi:", config.WIFI_SSID)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

for i in range(20):
    if wlan.isconnected():
        break
    # Animate dots
    display.text(font, "." * (i % 4 + 1) + "   ", 112, 4, st7789.YELLOW, st7789.BLACK)
    time.sleep_ms(500)

# Draw result
display.fill(st7789.BLACK)

if wlan.isconnected():
    ip = wlan.ifconfig()[0]
    rssi = wlan.status('rssi')
    print("Connected! IP:", ip, "RSSI:", rssi)

    # Title bar
    display.fill_rect(0, 0, 135, 20, st7789.BLUE)
    display.text(font, "WiFi Connected", 4, 2, st7789.WHITE, st7789.BLUE)

    # Info
    display.text(font, "SSID:", 4, 28, st7789.CYAN, st7789.BLACK)
    display.text(font, config.WIFI_SSID, 4, 46, st7789.WHITE, st7789.BLACK)
    display.text(font, "IP:", 4, 70, st7789.CYAN, st7789.BLACK)
    display.text(font, ip, 4, 88, st7789.GREEN, st7789.BLACK)
    display.text(font, "RSSI:", 4, 112, st7789.CYAN, st7789.BLACK)
    display.text(font, str(rssi) + " dBm", 4, 130, st7789.GREEN, st7789.BLACK)

    # Divider
    display.hline(4, 152, 127, st7789.color565(80, 80, 80))

    # Footer
    display.text(font, "ESP32-S3-GEEK", 4, 160, st7789.YELLOW, st7789.BLACK)
    display.text(font, "MicroPython", 4, 178, st7789.MAGENTA, st7789.BLACK)

    # Signal strength bar
    bars = min(5, max(0, (rssi + 90) // 10))
    for b in range(5):
        color = st7789.GREEN if b < bars else st7789.color565(40, 40, 40)
        h = 6 + b * 4
        display.fill_rect(4 + b * 14, 210 - h, 10, h, color)
else:
    print("WiFi failed")
    display.fill_rect(0, 0, 135, 20, st7789.RED)
    display.text(font, "WiFi FAILED", 4, 2, st7789.WHITE, st7789.RED)
    display.text(font, "SSID:", 4, 40, st7789.CYAN, st7789.BLACK)
    display.text(font, config.WIFI_SSID, 4, 58, st7789.WHITE, st7789.BLACK)
    display.text(font, "Check", 4, 100, st7789.YELLOW, st7789.BLACK)
    display.text(font, "config.py", 4, 118, st7789.YELLOW, st7789.BLACK)

print("Done!")
