# MQTT Garage Door Contoller
Raspberry Pi garage door controller using a magentic door sensor and SainSmart Relay Board.

## Requirements
* Raspberry Pi (any version)
* Raspbian Jessie
* Wifi or wired network connection
* Door sensor (magnetic reed switch)
* SainSmart Relay Board (2-channel)

## Script Install

1. Edit `garage_door.py` with your MQTT info.
2. Copy `garage_door.py` to `/usr/local/sbin/garage_door.py`
3. Create `/lib/systemd/system/garage-door.service` with the following:
```
[Unit]
Description=Garage Door Controller
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/sbin/garage_door.py
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
```
4. `systemctl --system daemon-reload`
5. `systemctl enable garage-door.service`
6. `service garage-door start`

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
