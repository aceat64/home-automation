import sys
import os
import logging
import argparse
import time
import json
import serial
import yaml
import jbd
import paho.mqtt.client as mqtt


def getInfo(port):
  try:
    bms = jbd.JBD(port, timeout=10)
    info = bms.readBasicInfo() | bms.readCellInfo()
    return info
  except:
    return False


def setup(client, config_file):
  logging.info(f"Loading pack config file: {config_file}")
  with open(config_file, "r", encoding="utf8") as yaml_file:
    config = yaml.safe_load(yaml_file)
  logging.info(f"Pack Name: {config['pack']['name']}")

  for sensor in config['sensor']:
    # make the sensor name safe for use in the mqtt path
    sensor_path_name = sensor['name'].replace(' ','_').lower()

    # add device so all sensors will be grouped together in hass
    sensor['device'] = {
      'name': config['pack']['name'],
      'identifiers': [config['pack']['name']],
      'model': "BMS",
      'manufacturer': "JBD"
    }
    sensor['state_topic'] = f"homeassistant/sensor/{config['pack']['name']}/state"
    sensor['unique_id'] = f"{config['pack']['name']}_{sensor_path_name}"

    if 'binary_sensor' in sensor and sensor['binary_sensor']:
      component = "binary_sensor"
    else:
      component = "sensor"

    client.publish(
      f"homeassistant/{component}/{config['pack']['name']}/{sensor_path_name}/config",
      json.dumps(sensor), 0, True)
    logging.debug(f"Topic: homeassistant/{component}/{config['pack']['name']}/{sensor_path_name}/config")
    logging.debug(f"Data: {json.dumps(sensor)}")
  return config


if __name__ == '__main__':
  parser = argparse.ArgumentParser(
    description="Reads from a JBD BMS and sends the data to Home Assistant.")
  parser.add_argument(
    '-p', '--port',
    default='/dev/ttyUSB1',
    help='Serial port to use')
  parser.add_argument(
    '-c', '--config',
    default=os.path.join(sys.path[0], 'config.yml'),
    help='Sensor configuration file')
  parser.add_argument(
    '-i', '--interval',
    default=10,
    help='Update interval')
  parser.add_argument(
    '-v', '--verbose',
    help='Verbose logging',
    action='store_true'
  )
  args = parser.parse_args()

  if args.verbose:
    loglevel = logging.DEBUG
  else:
    loglevel = logging.INFO

  logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)

  logging.info(f"Using port: {args.port}")
  port = serial.Serial(args.port)

  logging.info("Connecting to MQTT broker")
  client = mqtt.Client()
  client.username_pw_set(os.environ['MQTT_USER'], os.environ['MQTT_PASS'])
  client.connect(os.environ['MQTT_SERVER'], int(os.environ['MQTT_PORT']))

  config = setup(client, args.config)

  try:
    read_success = False
    while True:
      info = getInfo(port)
      if info:
        if not read_success:
          logging.info("Successful read from BMS")
          read_success = True
        logging.debug(f"Got info: {info}")
        client.publish(f"homeassistant/sensor/{config['pack']['name']}/state",
        json.dumps(info), 0, False)
      else:
        logging.warning('Failed to read from BMS')
        read_success = False
      logging.debug("Sleeping {args.interval}s")
      time.sleep(args.interval)
  except KeyboardInterrupt:
    sys.exit(0)
