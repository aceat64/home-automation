#!/usr/bin/python -u
import paho.mqtt.client as mqtt
import RPi.GPIO as gpio
import json, time, sys

# Uses the "physical pin" numbers, see https://pinout.xyz/
relayPin = 13

# Set to appropriate values for your MQTT server
client_user = 'someuser'
client_pass = 'somepass'
mqtt_server = '192.0.2.1'
mqtt_port = 1883

# Things you probably won't need to change
device_id = 'ont'
mqtt_keepalive = 60
mqtt_qos = 0
mqtt_retain = True

# Get things setup
gpio.setwarnings(False)
gpio.setmode(gpio.BOARD)
gpio.cleanup()
gpio.setup(relayPin, gpio.OUT)

# Make sure relay is off
gpio.output(relayPin, gpio.HIGH)

shutdown = 0

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe("home/" + device_id + "/set")

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    global last_command, command_cooldown, sensor, shutdown
    print("Command received: " + msg.payload)

    if msg.payload == "off":
        print("Turning off ONT")
        gpio.output(relayPin, gpio.LOW)
        client.publish("home/" + device_id, "off", mqtt_qos, mqtt_retain)
    elif msg.payload == "on":
        print("Turning on ONT")
        gpio.output(relayPin, gpio.HIGH)
        client.publish("home/" + device_id, "on", mqtt_qos, mqtt_retain)
    elif msg.payload == "shutdown":
        shutdown = 1
    else:
        print("Invalid command")

# Connect ot MQTT server and configure callbacks
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(client_user, client_pass)
client.connect(mqtt_server, mqtt_port, mqtt_keepalive)

# Start listening for messages
client.loop_start()

# Wait 1s while we connect
time.sleep(1)

client.publish("home/" + device_id, "on", mqtt_qos, mqtt_retain)

try:
    while shutdown == 0:
        time.sleep(1)
except KeyboardInterrupt:
    print "Shutdown requested"

client.loop_stop()
print("Good bye")
