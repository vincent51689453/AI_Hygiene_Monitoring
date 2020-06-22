#!/usr/bin/env python3

import paho.mqtt.client as mqtt
import time
# This is the Publisher

client = mqtt.Client()
client.connect("localhost",1883)

mqtt_message =' { "total_count" :' + str(7)+ \
    ', "valid_patient_counter" :'+ str(1)+ \
    ', "invalid_patient_counter" :'+str(3)+\
    ', "valid_exit_counter":'+str(1)+\
    ', "invalid_exit_counter":'+str(2) +\
    ', "success_rate":'+str(29) +\
    ', "total_sucess":'+str(2) +\
    ', "total_fail":'+str(5) + '}'
print("[INFO] MQTT Message:",mqtt_message)
client.publish("MDSSCC/AIHH/gui_dashboard", mqtt_message)
client.loop_stop()
client.disconnect()


