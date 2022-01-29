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


def buildFrame(address, data = []):
  payload = [ord(address), len(data)] + data
  checksum = calcChecksum(payload)
  return bytes(b'\xdd\xa5' + bytes(payload) + checksum + b'\x77')


def readFrame():
  frame = port.read_until('\x77')
  if not frame:
    return False
  if frame[0] != ord(b'\xdd'):
    logging.debug("Not the start of a frame")
    return False
  payload = frame[2:-3]
  checksum = frame[-3:-1]
  if calcChecksum(payload) != checksum:
    logging.debug("Invalid checksum")
    return False
  return payload


def calcChecksum(data):
  return pack('>H', 65536 - sum(data))


def getInfo(port):
  port.write(buildFrame(b'\x03'))
  frame = readFrame()
  if not frame:
    logging.debug("Not a valid frame")
    return False

  values = unpack('>BxHhHHHxxHxxHxBBBB', frame[0:25])
  if values[0] != 0:
    # status is not ok!
    logging.debug("Frame status not ok")
    return False

  info = {
    'pack_mv': values[1],
    'pack_ma': values[2],
    'cur_cap': values[3],
    'full_cap': values[4],
    'cycle_cnt': values[5],
    'cap_pct': values[8],
    'cell_cnt': values[10]
  }

  ntc_cnt = values[11]
  ntc_values = unpack(f'>{ntc_cnt}h', frame[25:25 + (ntc_cnt * 2)])
  for i in range(ntc_cnt):
    info[f'ntc{i}'] = (ntc_values[i] - 2731.5) / 10 # convert from K to C

  if values[9] & 1:
    info['chg_fet_en'] = True
  else:
    info['chg_fet_en'] = False
  if values[9] & 2:
    info['dsg_fet_en'] = True
  else:
    info['dsg_fet_en'] = False

  balance = values[6]

  for i in range(16):
    if balance & 1:
      info[f'bal{i}'] = True
    else:
      info[f'bal{i}'] = False
    balance >>= 1

  errors = values[7]
  error_names = [
    'covp_err',
    'cuvp_err',
    'povp_err',
    'puvp_err',
    'chgot_err',
    'chgut_err',
    'dsgot_err',
    'dsgut_err',
    'chgoc_err',
    'dsgoc_err',
    'sc_err',
    'afe_err'
  ]

  for error_name in error_names:
    if errors & 1:
      info[error_name] = True
    else:
      info[error_name] = False
    errors >>= 1

  port.write(buildFrame(b'\x04'))
  frame = readFrame()
  if not frame:
    logging.debug("Not a valid frame")
    return False
  cell_values = unpack(f">Bx{info['cell_cnt']}H", frame)
  if cell_values[0] != 0:
    logging.debug("Frame status not ok")
    return False
  for i in range(16):
    info[f"cell{i}_mv"] = cell_values[i + 1]  # Up by 1 because the first entry is the status byte

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
      'name': config['pack']['name'],
      'identifiers': [config['pack']['name']],
      'model': "BMS",
      'manufacturer': "JBD"
    }
    sensor['state_topic'] = f"homeassistant/sensor/{config['pack']['name']}/state"
    sensor['availability_topic'] = f"homeassistant/sensor/{config['pack']['name']}/status"
    sensor['unique_id'] = f"{config['pack']['name']}_{sensor_path_name}"

    client.publish(
      f"homeassistant/{component}/{config['pack']['name']}/{sensor_path_name}/config",
      json.dumps(sensor), 0, True)
    logging.debug(f"Topic: homeassistant/{component}/{config['pack']['name']}/{sensor_path_name}/config")
    logging.debug(f"Data: {json.dumps(sensor)}")
  return True


def on_connect(client, userdata, flags, rc):
  logging.info(f"Connected to MQTT broker, rc: {rc}")


def on_disconnect(client, userdata, rc):
  logging.warning(f"Disconnected from MQTT broker, rc: {rc}")


if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description="Reads from a JBD BMS and sends the data to Home Assistant.")
  parser.add_argument(
    '-p', '--port',
    default=os.getenv('PORT', '/dev/ttyUSB0'),
    help="Serial port to use")
  parser.add_argument(
    '-c', '--config',
    default=os.getenv('CONFIG', os.path.join(sys.path[0], 'config.yml')),
    help="Sensor configuration file")
  parser.add_argument(
    '-i', '--interval',
    default=int(os.getenv('INTERVAL', 10)),
    help="Update interval")
  parser.add_argument(
    '-t', '--timeout',
    default=int(os.getenv('TIMEOUT', 2)),
    help="Serial read timeout")
  parser.add_argument(
    '-v', '--verbose',
    help="Verbose logging",
    action='store_true'
  )
  args = parser.parse_args()

  if args.verbose or os.getenv('VERBOSE'):
    loglevel = logging.DEBUG
  else:
    loglevel = logging.INFO

  logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)

  logging.info(f"Loading pack config file: {args.config}")
  with open(args.config, "r", encoding="utf8") as yaml_file:
    config = yaml.safe_load(yaml_file)
  logging.info(f"Pack Name: {config['pack']['name']}")

  logging.info(f"Using port: {args.port}")
  port = serial.Serial(args.port, timeout = args.timeout)

  client = mqtt.Client()
  # Use TLS, but wrong
  client.tls_set(cert_reqs=ssl.CERT_NONE)
  client.tls_insecure_set(True)
  client.will_set(f"homeassistant/sensor/{config['pack']['name']}/status", 'offline', 0, True)
  client.username_pw_set(os.getenv('MQTT_USER'), os.getenv('MQTT_PASS'))
  client.connect(os.getenv('MQTT_SERVER'), int(os.getenv('MQTT_PORT', 8883)))
  client.on_connect = on_connect
  client.on_disconnect = on_disconnect
  client.loop_start()

  setup(client, config)

  try:
    read_success = False
    count = 0
    while True:
      info = getInfo(port)
      if info:
        logging.debug(f"Got info: {info}")
        if not read_success:
          logging.info("Successful read from BMS")
          read_success = True

        client.publish(f"homeassistant/sensor/{config['pack']['name']}/status", 'online', 0, False)
        client.publish(f"homeassistant/sensor/{config['pack']['name']}/state", json.dumps(info), 0, False)
        
        count += 1
        if (count % 10 == 0):
          logging.info(f"Sent {count} updates")
      else:
        logging.warning("Failed to read from BMS")
        read_success = False

      logging.debug(f"Sleeping {args.interval}s")
      time.sleep(args.interval)
  except KeyboardInterrupt:
    sys.exit(0)
