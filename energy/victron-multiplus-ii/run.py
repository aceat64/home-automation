import sys
import os
import logging
import argparse
import time
import json
import serial
import yaml
import ssl
import paho.mqtt.client as mqtt
from struct import *


def buildFrame(command, data=''):
  frame = [255]
  frame.extend(map(ord, command))
  frame.extend(map(ord, data))
  frame.insert(0, len(frame))
  return bytes(frame) + calcChecksum(frame)


def readFrame():
  length = port.read(1)
  frame = length + port.read(ord(length) + 1)
  payload = frame[0:-1]
  checksum = frame[-1:]
  if calcChecksum(payload) == checksum:
    return payload[1:]
  return False


def calcChecksum(data):
  return pack('B', 256 - sum(data) % 256)


def getRamVarInfo(id):
  port.write(buildFrame('W', f'\x36{id}\x00'))
  res = readFrame()
  if len(res) < 4:
    # This RamVar is not supported
    return False
  info = {}
  info['sc'], info['offset'] = unpack('<hh', res[3:7])
  if info['sc'] < 0:
    info['read_format'] = '<h'
  else:
    info['read_format'] = '<H'
  info['scale'] = abs(info['sc'])
  if info['scale'] >= 0x4000:
    info['scale'] = 1 / (0x8000 - info['scale'])
  return info

def getRamVar(id):
  info = getRamVarInfo(id)
  if not info:
    return False
  port.write(buildFrame('W', f'\x30{id}'))
  res = readFrame()
  raw_value = unpack(info['read_format'], res[3:5])[0]
  if abs(info['offset']) == 0x8000:
    # this is a single bit value
    if raw_value & (info['sc'] - 1):
      return True
    return False
  return info['scale'] * (raw_value + info['offset'])


def calcValue(id, value):
  info = getRamVarInfo(id)
  return info['scale'] * (value + info['offset'])


def getInfo(port):
  # Ask for version so the multiplus stops sending gratuitious version messages for a bit
  port.write(buildFrame('V')) # get version
  time.sleep(0.5)
  # toss the response(s), we don't care about them
  port.reset_input_buffer()

  info = {
    'led': {
      'on': [],
      'blink': []
    },
    'dc': {},
    'ac': {}
  }

  port.write(buildFrame('L')) # get LEDs
  led_frame = readFrame()
  if not led_frame:
    return False
  leds_on = ord(led_frame[2:3])
  leds_blink = ord(led_frame[3:4])

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
  dc_frame = readFrame()
  if not dc_frame:
    return False
  info['dc']['voltage'] = calcValue('\x04', unpack('<H', dc_frame[6:8])[0])
  info['dc']['current_used'] = round(calcValue('\x05', unpack('<I', dc_frame[8:11] + bytes([0x00]))[0]), 2)
  info['dc']['current_charge'] = round(calcValue('\x05', unpack('<I', dc_frame[11:14] + bytes([0x00]))[0]), 2)
  info['dc']['inverter_freq'] = round(10 / calcValue('\x07', unpack('<B', dc_frame[14:15])[0]), 2)

  port.write(buildFrame('F', '\x01')) # get AC info
  ac_frame = readFrame()
  if not ac_frame:
    return False
  ac_info = unpack('<BBxBxHHHHB', ac_frame[1:15])
  info['ac'] = {
    'mains_voltage': calcValue('\x00', ac_info[3]),
    'mains_current': round(calcValue('\x01', ac_info[4]) * ac_info[0], 2),
    'inverter_voltage': calcValue('\x02', ac_info[5]),
    'inverter_current': round(calcValue('\x03', ac_info[6]) * ac_info[1], 2),
    'mains_freq': round(10 / calcValue('\x08', ac_info[7]), 2)
  }
  state_defs = [
    "Down",
    "Startup",
    "Off",
    "Slave",
    "Inverting",
    "Inverter Half",
    "Inverting AES",
    "Power Assist",
    "Bypass",
    "Charge"
  ]
  sub_state_defs = [
    "Charge Init",
    "Charge Bulk",
    "Charge Absorption",
    "Charge Float",
    "Charge Storage",
    "Charge Repeated Absorption",
    "Charge Forced Absorption",
    "Charge Equalize",
    "Charge Bulk Stopped",
  ]
  port.write(buildFrame('W', f'\x0e\x00'))
  res = readFrame()
  state, sub_state = unpack('>BB', res[3:5])
  if state == 9:
    info['ac']['state'] = sub_state_defs[sub_state]
  else:
    info['ac']['state'] = state_defs[state]

  return info


def setup(client, config):
  for sensor in config['sensor']:
    # make the sensor name safe for use in the mqtt path
    sensor_path_name = sensor['name'].replace(' ','_').lower()

    if 'binary_sensor' in sensor and sensor['binary_sensor']:
      component = "binary_sensor"
    else:
      component = "sensor"

    # add device so all sensors will be grouped together in hass
    sensor['device'] = {
      'name': config['inverter']['name'],
      'identifiers': [config['inverter']['name']],
      'model': "MultiPlus-II",
      'manufacturer': "Victron Energy"
    }
    sensor['state_topic'] = f"homeassistant/sensor/{config['inverter']['name']}/state"
    sensor['availability_topic'] = f"homeassistant/sensor/{config['inverter']['name']}/status"
    sensor['unique_id'] = f"{config['inverter']['name']}_{sensor_path_name}"

    client.publish(
      f"homeassistant/{component}/{config['inverter']['name']}/{sensor_path_name}/config",
      json.dumps(sensor), 0, True)
    logging.debug(f"Topic: homeassistant/{component}/{config['inverter']['name']}/{sensor_path_name}/config")
    logging.debug(f"Data: {json.dumps(sensor)}")
  return True


def on_connect(client, userdata, flags, rc):
  logging.info("Connected to MQTT broker")

if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description="Reads from a Victron MultiPlus-II and sends the data to Home Assistant.")
  parser.add_argument(
    '-p', '--port',
    default=os.getenv('PORT', '/dev/ttyUSB0'),
    help='Serial port to use')
  parser.add_argument(
    '-c', '--config',
    default=os.getenv('CONFIG', os.path.join(sys.path[0], 'config.yml')),
    help='Sensor configuration file')
  parser.add_argument(
    '-i', '--interval',
    default=int(os.getenv('INTERVAL', 10)),
    help='Update interval')
  parser.add_argument(
    '-v', '--verbose',
    help='Verbose logging',
    action='store_true'
  )
  args = parser.parse_args()

  if args.verbose or os.getenv('VERBOSE'):
    loglevel = logging.DEBUG
  else:
    loglevel = logging.INFO

  logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)

  logging.info(f"Loading inverter config file: {args.config}")
  with open(args.config, "r", encoding="utf8") as yaml_file:
    config = yaml.safe_load(yaml_file)
  logging.info(f"Inverter Name: {config['inverter']['name']}")

  logging.info(f"Using port: {args.port}")
  port = serial.Serial(args.port, 2400)

  logging.info("Connecting to MQTT broker")
  client = mqtt.Client(transport="websockets")
  client.on_connect = on_connect
  # Use TLS, but wrong
  client.tls_set(cert_reqs=ssl.CERT_NONE)
  client.tls_insecure_set(True)
  client.will_set(f"homeassistant/sensor/{config['inverter']['name']}/status", 'offline', 0, True)
  client.username_pw_set(os.getenv('MQTT_USER'), os.getenv('MQTT_PASS'))
  client.connect(os.getenv('MQTT_SERVER'), int(os.getenv('MQTT_PORT', 8884)))

  setup(client, config)

  try:
    read_success = False
    while True:
      info = getInfo(port)
      if info:
        if not read_success:
          logging.info("Successful read from inverter")
          read_success = True
          client.publish(f"homeassistant/sensor/{config['inverter']['name']}/status", 'online', 0, False)
        logging.debug(f"Got info: {info}")
        client.publish(f"homeassistant/sensor/{config['inverter']['name']}/state",
        json.dumps(info), 0, False)
      else:
        logging.warning("Unable to read data from inverter")
        read_success = False
      logging.debug(f"Sleeping {args.interval}s")
      time.sleep(args.interval)
  except KeyboardInterrupt:
    sys.exit(0)
