#!/usr/bin/env python3
## mqtt chat client example

import time
import sys
import paho.mqtt.client as mqtt
import json
import random

def on_connect(mqttc, obj, flags, rc):
    print("Connected to %s:%s" % (mqttc._host, mqttc._port))

def on_message(mqttc, obj, msg):
    print("on message: " + msg.topic+" "+str(msg.qos)+" payload: "+str(msg.payload))
    print("msg.payload --> type:{} text: {} len: {}".format(type(msg.payload), msg.payload, len(msg.payload)))
    payload = msg.payload.decode('utf-8')
    print("msg.payloaddecode('utf-8') --> type:{} text: {} len: {}".format(type(payload), payload, len(payload)))
    try:
        data = json.loads(payload)
        print("text: " + data['text'])
    except ValueError:
        print("no json text: " + payload)

def on_publish(mqttc, obj, mid):
    print("mid: "+str(mid))

def on_subscribe(mqttc, obj, mid, granted_qos):
    print("Subscribed: "+str(mid)+" "+str(granted_qos))

def on_log(mqttc, obj, level, string):
    print('Log: {}'.formt(string))

if len(sys.argv) < 4:
    print(sys.argv[0], "mqtt_addr port topic")
    sys.exit(0)

mqtt_addr = sys.argv[1]
mqtt_port = int(sys.argv[2])
if mqtt_port == 0:
    mqtt_port = 1883
topic = sys.argv[3]


ACCESS_TOKEN = 'IOT_DEMO_TOKEN'

next_reading = time.time() 

print("MQTT server={} {} topic={}".format(mqtt_addr, mqtt_port, topic))
client = mqtt.Client()

client.on_message = on_message
client.on_connect = on_connect
client.on_publish = on_publish
client.on_subscribe = on_subscribe

# Set access token
#client.username_pw_set(ACCESS_TOKEN)

# Connect to MQTT broker using mqttLocalHost and port and 60 seconds keepalive interval
client.connect(mqtt_addr, mqtt_port, 60)

client.loop_start()

client.subscribe(topic, 0)

try:
    while True:
        print('>>', end='')
        text = sys.stdin.readline().strip()
        msg = {}
        msg['tm'] = int(time.time())
        msg['text'] = text
        json_msg = json.dumps(msg)
        print("publish: {:s} {:s}".format(topic, json_msg))
        client.publish(topic, json_msg, 1)
except KeyboardInterrupt:
    pass

client.loop_stop()
client.disconnect()
