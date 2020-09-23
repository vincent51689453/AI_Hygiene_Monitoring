import paho.mqtt.client as mqtt
from pynput import keyboard

def on_press (key):
    global client
    try:
        if(key.char=='q'):
            print("Handwash -> publish")
            client.reconnect()
            client.publish("MDSSCC/AIHH/SENSOR","WASHED")
        if(key.char=='e'):
            print("Handrub -> publish")
            client.reconnect()
            client.publish("MDSSCC/AIHH/SENSOR","PRESS")
        
    except AttributeError:
        print('special key {0} pressed'.format(key))

def on_release(key):
    #print('{0} released'.format(key))
    if key == keyboard.Key.esc:
        # Stop listener
        return False

client = mqtt.Client()
client.connect("158.132.152.125",1883)

listener = keyboard.Listener(on_press=on_press,on_release=on_release)
listener.start()

x = 0
while True:
    x+=1

