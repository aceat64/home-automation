#!/usr/bin/python -u
import paho.mqtt.client as mqtt
import RPi.GPIO as gpio
import json, time, sys

# Uses the "physical pin" numbers, see https://pinout.xyz/
sensorPin = 15
relayPin = 11

# Set to appropriate values for your MQTT server
client_user = 'someuser'
client_pass = 'somepass'
mqtt_server = '192.0.2.1'
mqtt_port = 1883

# Things you probably won't need to change
device_id = 'garage_door'
mqtt_keepalive = 60
mqtt_qos = 0
mqtt_retain = True

# Seconds to wait before acting on subsequent commands
command_cooldown = 15

# Get things setup
gpio.setwarnings(False)
gpio.setmode(gpio.BOARD)
gpio.cleanup()
gpio.setup(relayPin, gpio.OUT)
gpio.setup(sensorPin, gpio.IN)

# Set pull-up resistor
gpio.setup(sensorPin, gpio.IN, gpio.PUD_UP)

# Make sure relay is off
gpio.output(relayPin, gpio.HIGH)

last_command = 0
shutdown = 0

def update_state(state):
    global qos, retain
    if state:
        print("State is: open")
        client.publish("home/" + device_id, "open", mqtt_qos, mqtt_retain)
    else:
        print("State is: closed")
        client.publish("home/" + device_id, "closed", mqtt_qos, mqtt_retain)

def press_button():
    gpio.output(relayPin, gpio.LOW)
    time.sleep(0.5)
    gpio.output(relayPin, gpio.HIGH)

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

    if time.time() - last_command > command_cooldown:
        if msg.payload == "open" and sensor == 0:
            last_command = time.time()
            print("Opening garage door!")
            press_button()
        elif msg.payload == "close" and sensor == 1:
            last_command = time.time()
            print("Closing garage door!")
            press_button()
        elif msg.payload == "open" or msg.payload == "close":
            print("Invalid door state for command, updating state")
            update_state(sensor)
        elif msg.payload == "shutdown":
            shutdown = 1
        else:
            print("Invalid command")
    else:
        print("Ignoring command, cooldown is still in effect")

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

# Initial update of state
last_state = gpio.input(sensorPin)
update_state(last_state)

try:
    while shutdown == 0:
        time.sleep(0.1)
        sensor = gpio.input(sensorPin)
        if sensor != last_state:
            last_state = sensor
            update_state(sensor)
except KeyboardInterrupt:
    print "Shutdown requested"

client.loop_stop()
print("Good bye")
