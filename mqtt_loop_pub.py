#!/usr/bin/env python3
## publishing sensor data to MQTT broker

import os
import time
import sys
import sht1x_sensor
import paho.mqtt.client as mqtt
import json
import random
import spidev

def generate_topic(service_code, product_sn):
    topic = 'petG1/' + service_code + '/' + product_sn + '/stat/_cur'
    return topic

def generate_client_id(client_prefix, product_sn):
    client_id = client_prefix + 'GPET' + product_sn + '_' + str(random.randint(100, 999))
    return client_id

CO2_CHANNEL=0
WATER_LEVEL_CHANNEL=1
SOIL_HUMIDIFY_CHANNEL=2
LIGHT_CHANNEL=3

spi = spidev.SpiDev()
spi.open(0, 0)
# It must set the speed as 1 M to talk with MCP3008.
spi.max_speed_hz = 1000000

def read_channel(channel):
    cmd = 0b11 << 6  # Start bit, single channel read
    cmd |= (channel & 0x07) << 3  # channel number (in 3 bits)
    resp = spi.xfer2([cmd, 0x0, 0x0])
    result = (resp[0] & 0x01) << 9
    result |= (resp[1] & 0xFF) << 1
    result |= (resp[2] & 0x80) >> 7
    return result & 0x3FF

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
        temp,humi = sht.read_values()
        co2 = read_channel(CO2_CHANNEL)
        wLev = read_channel(WATER_LEVEL_CHANNEL)
        sHumi = read_channel(SOIL_HUMIDIFY_CHANNEL)
        light = read_channel(LIGHT_CHANNEL)
        #print(u"Temperature: {:g}\u00b0C, Humidity: {:g}%".format(temp, humi))

        sensor_data = {
          "tm" : int(time.time()),
          "temp" : {"unit": "C", "val": temp},
          "humi" : {"unit": "%", "val": humi},
          "co2" : {"unit": "u10", "val": co2},
          "wLev" : {"unit": "u10", "val": wLev},
          "sHumi" : {"unit": "u10", "val": sHumi},
          "light" : {"unit": "u10", "val": light},
        }

        data_in_json_format = json.dumps(sensor_data)
        print("publish: {:s} {:s}%".format(topic, data_in_json_format))
        client.publish(topic, data_in_json_format, 1)

        next_reading += INTERVAL
        sleep_time = next_reading-time.time()
        if sleep_time > 0:
            time.sleep(sleep_time)
except KeyboardInterrupt:
    pass

client.loop_stop()
client.disconnect()
