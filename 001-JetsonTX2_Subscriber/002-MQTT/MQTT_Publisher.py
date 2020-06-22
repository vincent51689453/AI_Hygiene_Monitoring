#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import time
# This is the Publisher

client = mqtt.Client()
client.connect("localhost",1883)
while True:
    client.publish("topic/test", "Publisher")
    time.sleep(5)
    client.loop()

