import sys
import os
import logging
import argparse
import time
import json
import serial
import yaml
import paho.mqtt.client as mqtt
from struct import *


def buildFrame(command, data=''):
  frame = [0xFF]
  frame.extend(map(ord, command))
  frame.extend(map(ord, data))
  frame.insert(0, len(frame))
  frame.append(256 - sum(frame) % 256)
  return bytes(frame)


def readFrame():
  length_byte = port.read(1)
  length = ord(length_byte)
  message = port.read(length + 1)
  frame = length_byte + message
  if sum([byte for byte in frame]) % 256 == 0:
    return(frame)
  return False


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
  dc_frame = readFrame()
  if not dc_frame:
    return False
  info['dc']['voltage'] = unpack('<H', dc_frame[7:9])[0] / 100
  info['dc']['current_used'] = unpack('<I', dc_frame[9:12] + bytes([0x00]))[0] / 100
  info['dc']['current_charge'] = unpack('<I', dc_frame[12:15] + bytes([0x00]))[0] / 100
  info['dc']['inverter_freq'] = round((10 / unpack('<B', dc_frame[15:16])[0]) * 1000, 2)

  port.write(buildFrame('F', '\x01')) # get AC info
  ac_frame = readFrame()
  if not ac_frame:
    return False
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

  return info


def setup(client, config_file):
  logging.info(f"Loading inverter config file: {config_file}")
  with open(config_file, "r", encoding="utf8") as yaml_file:
    config = yaml.safe_load(yaml_file)
  logging.info(f"Inverter Name: {config['inverter']['name']}")

  for sensor in config['sensor']:
    # make the sensor name safe for use in the mqtt path
    sensor_path_name = sensor['name'].replace(' ','_').lower()

    # add device so all sensors will be grouped together in hass
    sensor['device'] = {
      'name': config['inverter']['name'],
      'identifiers': [config['inverter']['name']],
      'model': "MultiPlus-II",
      'manufacturer': "Victron Energy"
    }
    sensor['state_topic'] = f"homeassistant/sensor/{config['inverter']['name']}/state"
    sensor['unique_id'] = f"{config['inverter']['name']}_{sensor_path_name}"

    if 'binary_sensor' in sensor and sensor['binary_sensor']:
      component = "binary_sensor"
    else:
      component = "sensor"

    client.publish(
      f"homeassistant/{component}/{config['inverter']['name']}/{sensor_path_name}/config",
      json.dumps(sensor), 0, True)
    logging.debug(f"Topic: homeassistant/{component}/{config['inverter']['name']}/{sensor_path_name}/config")
    logging.debug(f"Data: {json.dumps(sensor)}")
  return config


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

  logging.info(f"Using port: {args.port}")
  port = serial.Serial(args.port, 2400)

  logging.info("Connecting to MQTT broker")
  client = mqtt.Client()
  client.username_pw_set(os.getenv('MQTT_USER'), os.getenv('MQTT_PASS'))
  client.connect(os.getenv('MQTT_SERVER'), int(os.getenv('MQTT_PORT', 1883)))

  config = setup(client, args.config)

  try:
    read_success = False
    while True:
      info = getInfo(port)
      if info:
        if not read_success:
          logging.info("Successful read from inverter")
          read_success = True
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
