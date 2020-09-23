#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import time
import argparse

parser = argparse.ArgumentParser()

#Incompliance patient
parser.add_argument('-a')

#Compliance patient
parser.add_argument('-b')

#Incompliance surrondings
parser.add_argument('-c')

#Compliance surrondings
parser.add_argument('-d')
parameters = parser.parse_args()

w = int(parameters.a)
x = int(parameters.b)
y = int(parameters.c)
z = int(parameters.d)

total_count = w + x + y + z
if(total_count>0):
    sucess_rate = (x + z)/total_count
else:
    sucess_rate = 0
total_success = x + z
total_fail = w + y

print("a:{} b:{} c:{} d:{}".format(w,x,y,z))
# This is the Publisher

client = mqtt.Client()
client.connect("localhost",1883)

mqtt_message =' { "total_count" :' + str(total_count)+ \
    ', "valid_patient_counter" :'+ str(x)+ \
    ', "invalid_patient_counter" :'+str(w)+\
    ', "valid_exit_counter":'+str(z)+\
    ', "invalid_exit_counter":'+str(y) +\
    ', "success_rate":'+str(sucess_rate) +\
    ', "total_sucess":'+str(total_success) +\
    ', "total_fail":'+str(total_fail) + '}'
print("[INFO] MQTT Message:",mqtt_message)
client.publish("MDSSCC/AIHH/gui_dashboard", mqtt_message)
client.loop_stop()
client.disconnect()


