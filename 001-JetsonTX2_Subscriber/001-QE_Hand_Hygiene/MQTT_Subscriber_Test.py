#!/usr/bin/env python3

import paho.mqtt.client as mqtt

# This is the Subscriber
num_packet = 0

def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    client.subscribe("MDSSCC/AIHH/SENSOR")

def on_message(client, userdata, msg):
    global num_packet
    if (msg.payload.decode() == "WASHED"):
        print("Successful Message Counter=",num_packet)
        print("<<WASHED>> received")
        num_packet+=1
    if (msg.payload.decode() == "DIRTY"):
        print("Successful Message Counter=",num_packet)
        print("<<DIRTY>> received")
        num_packet+=1
        #client.disconnect()
    if (msg.payload.decode() == "PRESS"):
        print("Sensor is pressed")
    if (msg.payload.decode() == "RELEASE"):
        print("Sensor is released")
    
client = mqtt.Client()
#It should connect to MQTT server
#Jetson TX2(vincent) has been set as a MQTT server
#If publisher/subscriber on JetsonTX2(vincet) please connect to localhost
#Else please connect to  192.168.0.101 in the LAN
client.connect("localhost",1883,60)

client.on_connect = on_connect
client.on_message = on_message

client.loop_forever()
