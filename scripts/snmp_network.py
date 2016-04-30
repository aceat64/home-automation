#!/usr/bin/python3 -u
import paho.mqtt.client as mqtt
from easysnmp import Session
import json, time, sys

# Set to appropriate values for your MQTT server
client_user = 'someuser'
client_pass = 'somepass'
mqtt_server = '192.0.2.1'
mqtt_port = 1883

# Set for your router and interface
router_ip = '192.0.2.1'
snmp_community = 'public'
interface_name = 'eth0'
interface_index = 2

# Things you probably won't need to change
device_id = 'router'
mqtt_keepalive = 60
mqtt_qos = 0
mqtt_retain = False
interval = 3

def get_octets():
    global interface_index
    octets = {}
    octets['in'] = session.get(('IF-MIB::ifInOctets', interface_index))
    octets['out'] = session.get(('IF-MIB::ifOutOctets', interface_index))
    return {'in': int(octets['in'].value), 'out': int(octets['out'].value)}

def calc_bps(old_octets, new_octets):
    global interval

    # If counter has reset
    if old_octets > new_octets:
        # If it's a 32-bit counter
        if old_octets < 2 ** 32:
            octets = 2 ** 32 - old_octets + new_octets
        # If it's a 64-bit counter
        elif old_octets < 2 ** 64:
            octets = 2 ** 32 - old_octets + new_octets
        else:
            # Well this is awkward, say something to console, maybe it won't happen again
            print("Invalid value for old_octets: %s" % old_octets)
            # Screw up the graphs just for fun
            octets = 9999999999999
    else:
        # easy mode
        octets = new_octets - old_octets
    return int((octets * 8) / interval)

# Connect ot MQTT server and configure callbacks
client = mqtt.Client()
client.username_pw_set(client_user, client_pass)
client.connect(mqtt_server, mqtt_port, mqtt_keepalive)

# Start things up
client.loop_start()

# Wait 1s while we connect
time.sleep(1)

# Create an SNMP session to be used for all our requests
session = Session(hostname=router_ip, community=snmp_community, version=2)

old_octets = get_octets()

try:
    while 1:
        time.sleep(interval)

        new_octets = get_octets()

        bps = {}
        bps['in'] = calc_bps(old_octets['in'], new_octets['in'])
        bps['out'] = calc_bps(old_octets['out'], new_octets['out'])

        payload = {'in': bps['in'], 'out': bps['out']}

        client.publish("home/" + device_id + "/" + interface_name, json.dumps(payload), mqtt_qos, mqtt_retain)

        old_octets = new_octets
except KeyboardInterrupt:
    print("\nShutdown requested")

client.loop_stop()
print("Good bye")
