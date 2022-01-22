import sys
import serial
from struct import *

port = serial.Serial('/dev/ttyUSB1', 2400)

def buildFrame(command, data=''):
  frame = [0xFF]
  frame.extend(map(ord, command))
  frame.extend(map(ord, data))
  frame.insert(0, len(frame))
  frame.append(256 - sum(frame) % 256)
  return bytes(frame)

# buildFrame('V')          # get version
# buildFrame('L')          # get LEDs
# buildFrame('F', '\x00')  # get DC info
# buildFrame('F', '\x01')  # get AC info
# print(buildFrame('V', '\x24\xdb\x11\x00\x00')) # example version response

def readFrame():
  length_byte = port.read(1)
  length = ord(length_byte)
  message = port.read(length + 1)
  frame = length_byte + message
  if sum([byte for byte in frame]) % 256 == 0:
    return(frame)
  return False

port.write(buildFrame('V')) # get version
port.reset_input_buffer()
if not readFrame():
  sys.exit(1)

info = {
  'led': {
    'on': [],
    'blink': []
  },
  'dc': {},
  'ac': {}
}

port.write(buildFrame('L')) # get LEDs
port.reset_input_buffer()
led_frame = readFrame()
if led_frame:
  leds_on = ord(led_frame[3:4])
  leds_blink = ord(led_frame[4:5])

  if leds_on & 1:
    info['led']['on'].append("Mains")
  if leds_on & 2:
    info['led']['on'].append("Absorption")
  if leds_on & 4:
    info['led']['on'].append("Bulk")
  if leds_on & 8:
    info['led']['on'].append("Float")
  if leds_on & 16:
    info['led']['on'].append("Inverter")
  if leds_on & 32:
    info['led']['on'].append("Overload")
  if leds_on & 64:
    info['led']['on'].append("Low Battery")
  if leds_on & 128:
    info['led']['on'].append("Temperature")

  if leds_blink & 1:
    info['led']['blink'].append("Mains")
  if leds_blink & 2:
    info['led']['blink'].append("Absorption")
  if leds_blink & 4:
    info['led']['blink'].append("Bulk")
  if leds_blink & 8:
    info['led']['blink'].append("Float")
  if leds_blink & 16:
    info['led']['blink'].append("Inverter")
  if leds_blink & 32:
    info['led']['blink'].append("Overload")
  if leds_blink & 64:
    info['led']['blink'].append("Low Battery")
  if leds_blink & 128:
    info['led']['blink'].append("Temperature")

port.write(buildFrame('F', '\x00')) # get DC info
port.reset_input_buffer()
dc_frame = readFrame()
if dc_frame:
  info['dc']['voltage'] = unpack('<h', dc_frame[7:9])[0] / 100
  info['dc']['current_used'] = unpack('<i', dc_frame[9:12] + bytes([0x00]))[0] / 100
  info['dc']['current_charge'] = unpack('<i', dc_frame[12:15] + bytes([0x00]))[0] / 100
  info['dc']['inverter_freq'] = round((10 / unpack('<B', dc_frame[15:16])[0]) * 1000, 2)

port.write(buildFrame('F', '\x01')) # get AC info
port.reset_input_buffer()
ac_frame = readFrame()
if ac_frame:
  state = [
    "Down",
    "Startup",
    "Off",
    "Slave",
    "Inverting",
    "Inverter Half",
    "Inverting AES",
    "Power Assist",
    "Bypass",
    "Charging"
  ]
  ac_info = unpack('<BBxBxHHHHB', ac_frame[2:16])
  info['ac'] = {
    'state': state[ac_info[2]],
    'mains_voltage': ac_info[3] / 100,
    'mains_current': (ac_info[4] * ac_info[0]) / 100,
    'inverter_voltage': ac_info[5] / 100,
    'inverter_current': (ac_info[6] * ac_info[1]) / 100,
    'mains_freq': round((10 / ac_info[7]) * 1000, 2)
  }

print(info)