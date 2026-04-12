# test_s3.py — Proof of concept: WiFi + E-Ink on Heltec Wireless Paper V1.2
# Connects to WiFi and displays the result on the E-Ink screen.

from machine import Pin, SPI
import network
import time
import config
from depg0213 import DEPG0213

print("=== Heltec Wireless Paper V1.2 Test ===")

# Init display (handles Vext power cycling internally)
print("Initialising display...")
spi = SPI(1, baudrate=6000000, polarity=0, phase=0,
          sck=Pin(3), mosi=Pin(2))
display = DEPG0213(spi, cs=4, dc=5, rst=6, busy=7, vext=45)

# Show connecting message
print("Showing 'Connecting...'")
display.fill(1)
display.text("Connecting...", 5, 5)
display.update()

# Connect to WiFi
print("Connecting to WiFi:", config.WIFI_SSID)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

for i in range(20):
    if wlan.isconnected():
        break
    time.sleep_ms(500)

# Draw final result
display.fill(1)

if wlan.isconnected():
    ip = wlan.ifconfig()[0]
    rssi = wlan.status('rssi')
    print("Connected! IP:", ip, "RSSI:", rssi)

    display.text("WiFi Connected!", 5, 10)
    display.hline(5, 22, 200, 0)
    display.text("SSID: " + config.WIFI_SSID, 5, 30)
    display.text("IP: " + ip, 5, 45)
    display.text("RSSI: " + str(rssi) + " dBm", 5, 60)
    display.hline(5, 74, 200, 0)
    display.text("Heltec WP V1.2", 5, 82)
    display.text("MicroPython 1.28", 5, 97)
else:
    print("WiFi failed")
    display.text("WiFi FAILED", 5, 10)
    display.text("SSID: " + config.WIFI_SSID, 5, 30)
    display.text("Check config.py", 5, 50)

print("Updating display...")
display.update()
print("Done!")
