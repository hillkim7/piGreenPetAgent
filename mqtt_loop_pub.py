## publishing sensor data to MQTT broker

import os
import time
import sys
import sht1x_sensor
import paho.mqtt.client as mqtt
import json
import random

def generate_topic(service_code, product_sn):
    topic = 'petG1/' + service_code + '/' + product_sn + '/stat/_cur'
    return topic

def generate_client_id(client_prefix, product_sn):
    client_id = client_prefix + 'GPET' + product_sn + '_' + str(random.randint(100, 999))
    return client_id

# Data capture and upload interval in seconds.
INTERVAL=3

if len(sys.argv) < 3:
    print(sys.argv[0], "product_sn mqttConfig.json [interval]")
    sys.exit(0)

product_sn = sys.argv[1]
config_path = sys.argv[2]
if len(sys.argv) == 4:
    INTERVAL = int(sys.argv[3])

with open(config_path) as data_file:    
    mqtt_config = json.load(data_file)

topic = generate_topic(mqtt_config['serviceCode'], product_sn)
client_id = generate_client_id(mqtt_config['clientPrefix'], product_sn)

sht = sht1x_sensor.SHT1xSensor()

ACCESS_TOKEN = 'IOT_DEMO_TOKEN'

next_reading = time.time() 

print("MQTT client_id={} with interval={}".format(client_id, INTERVAL))
client = mqtt.Client(client_id)

# Set access token
client.username_pw_set(ACCESS_TOKEN)

# Connect to MQTT broker using mqttLocalHost and port and 60 seconds keepalive interval
client.connect(mqtt_config['mqttLocalHost'], mqtt_config['mqttLocalPort'], 60)

client.loop_start()

try:
    while True:
        temperature,humidity = sht.read_values()
        #print(u"Temperature: {:g}\u00b0C, Humidity: {:g}%".format(temperature, humidity))

        sensor_data = {
          "tm" : int(time.time()),
          "temp" : {"unit": "C", "val": temperature},
          "humi" : {"unit": "%", "val": humidity},
          "co2" : {"unit": "ppm", "val": random.randint(1000, 2000)}
        }

        data_in_json_format = json.dumps(sensor_data)
        print(u"publish: {:s}\u00b0C, Humidity: {:s}%".format(topic, data_in_json_format))
        client.publish(topic, data_in_json_format, 1)

        next_reading += INTERVAL
        sleep_time = next_reading-time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
except KeyboardInterrupt:
    pass

client.loop_stop()
client.disconnect()
