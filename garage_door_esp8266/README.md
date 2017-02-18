# MQTT Garage Door Contoller
Digistump Oak garage door controller using a magentic door sensor and SainSmart Relay Board.

## Requirements
* Digistump Oak (or ESP8266)
* Wifi network
* Door sensor (magnetic reed switch)
* SainSmart Relay Board (2-channel)

## Home-Assisstant Config
```
switch:
  - platform: mqtt
    name: "Garage Door"
    state_topic: "home/garage_door"
    command_topic: "home/garage_door/set"
    optimistic: false
    qos: 0
    retain: false
    payload_on: "open"
    payload_off: "closed"
```
