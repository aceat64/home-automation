#!/usr/bin/python3 -u
import paho.mqtt.client as mqtt
import json, time, sys, subprocess

# Set to appropriate values for your MQTT server
client_user = 'someuser'
client_pass = 'somepass'
mqtt_server = '192.0.2.1'
mqtt_port = 1883
ups_ip = '192.0.2.2'
device_id = 'fileserver'

# Things you probably won't need to change
mqtt_keepalive = 60
mqtt_qos = 0
mqtt_retain = True
interval = 30

def get_data():
    raw_output = str(subprocess.check_output(["apcaccess", "-h", ups_ip]), "utf-8")
    lines = raw_output.splitlines()
    data = {}
    for line in lines:
        line = line.split(':')
        key = line[0].strip()
        val = line[1].strip()
        #print(key + ": " + val)
        if key == 'STATUS':
            data['status'] = val
        if key == 'LINEV':
            data['linev'] = val.split(' ')[0]
        if key == 'LOADPCT':
            data['loadpct'] = val.split(' ')[0]
        if key == 'BCHARGE':
            data['bcharge'] = val.split(' ')[0]
        if key == 'TIMELEFT':
            data['timeleft'] = val.split(' ')[0]
        if key == 'NOMPOWER':
            data['nompower'] = val.split(' ')[0]
    return data

# Connect to MQTT server and configure callbacks
client = mqtt.Client()
client.username_pw_set(client_user, client_pass)
client.connect(mqtt_server, mqtt_port, mqtt_keepalive)

# Start things up
client.loop_start()

# Wait 1s while we connect
time.sleep(1)

try:
    while 1:
        data = get_data()
        client.publish("home/" + device_id + "/ups", json.dumps(data), mqtt_qos, mqtt_retain)
        time.sleep(interval)
except KeyboardInterrupt:
    print("\nShutdown requested")

client.loop_stop()
print("Good bye")

