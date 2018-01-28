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
import sensor_table
from petscript.petbot import PetBot
from petscript.inputprocessor import InputProcessor
from petscript.outputprocessor import OutputProcessor
from petscript.petscript import Scenario
import queue
from datetime import datetime

WATER_LEVEL_CHANNEL=0
SOIL_HUMIDIFY_CHANNEL=1
CO2_CHANNEL=2
LIGHT_CHANNEL=3

def generate_topic(service_code, product_sn):
    topic = 'petG1/' + service_code + '/' + product_sn + '/stat/_cur'
    return topic

def generate_chat_topic(service_code, product_sn):
    topic = 'petG1/' + service_code + '/' + product_sn + '/chat/_cur'
    return topic

def generate_client_id(client_prefix, product_sn):
    client_id = client_prefix + 'GPET' + product_sn + '_' + str(random.randint(100, 999))
    return client_id

class TagMapper(OutputProcessor):
    
    def __init__(self):
        self.mapper = {}
    
    def post_process(self, output_line):
        for key, val in self.mapper.items():
            if key in output_line:
                output_line = output_line.replace(key, val)
        return output_line

    def set_tag_value(self, tag, value):
        self.mapper[tag] = str(value)

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
chat_topic = generate_chat_topic(mqtt_config['serviceCode'], product_sn)
client_id = generate_client_id(mqtt_config['clientPrefix'], product_sn)

sht = sht1x_sensor.SHT1xSensor()

ACCESS_TOKEN = 'IOT_DEMO_TOKEN'

next_reading = time.time() 

script_file = 'files/pet-scenario.csv'
bot_name = 'Green Pet'
bot_user = product_sn
ipcQueue = queue.Queue()

scenario = Scenario()
input_processor = InputProcessor()
output_processor = TagMapper()
scenario.load_scenario_file(script_file)
petbot = PetBot(bot_name, scenario, input_processor, output_processor)
print('Greeting', petbot.talk('안녕'))

def on_message(mqttc, obj, msg):
    global ipcQueue, bot_user
    #print("on message: " + msg.topic+" "+str(msg.qos)+" payload: "+str(msg.payload))
    #print("msg.payload --> type:{} text: {} len: {}".format(type(msg.payload), msg.payload, len(msg.payload)))
    payload = msg.payload.decode('utf-8')
    try:
        data = json.loads(payload)
        if 'user' not in data or data['user'] != bot_user:
            print("text: " + data['text'])
            ipcQueue.put(data)
    except ValueError:
        print("no json text: " + payload)

def check_chat():
    try:
        data = ipcQueue.get(True, 0.2)
    except queue.Empty:
        return
    if data:
        print('data from Q: ', data)
        answer = petbot.talk(data['text'])
        msg = {}
        msg['tm'] = int(time.time())
        if answer:
            print(answer)
            msg['text'] = answer.text
            msg['emotion'] = answer.emotion
        else:
            msg['text'] = ('^^')
        msg['user'] = bot_user
        json_msg = json.dumps(msg)
        print("publish: {:s} {:s}".format(chat_topic, json_msg))
        client.publish(chat_topic, json_msg, 1)

print("MQTT client_id={} with interval={}".format(client_id, INTERVAL))
client = mqtt.Client(client_id)

client.on_message = on_message

# Set access token
client.username_pw_set(ACCESS_TOKEN)

# Connect to MQTT broker using mqttLocalHost and port and 60 seconds keepalive interval
client.connect(mqtt_config['mqttLocalHost'], mqtt_config['mqttLocalPort'], 60)

temp = 0
humi = 0
client.loop_start()
client.subscribe(chat_topic, 0)

try:
    while True:
        try:
            temp,humi = sht.read_values()
        except Exception as ex:
            print("exception: {0}".format(ex))
        co2 = read_channel(CO2_CHANNEL)
        wLev = read_channel(WATER_LEVEL_CHANNEL)
        sHumi = read_channel(SOIL_HUMIDIFY_CHANNEL)
        light = read_channel(LIGHT_CHANNEL)
        #print(u"Temperature: {:g}\u00b0C, Humidity: {:g}%".format(temp, humi))

        c_co2 = sensor_table.convert_co2(co2)
        c_wLev = sensor_table.convert_water_level(wLev)
        c_sHumi = sensor_table.convert_soil_humi(sHumi)
        c_light = sensor_table.convert_cds(light)
 
        output_processor.set_tag_value('{{temp}}', temp)
        output_processor.set_tag_value('{{humi}}', humi)
        output_processor.set_tag_value('{{co2}}', c_co2)
        output_processor.set_tag_value('{{wLev}}', c_wLev)
        output_processor.set_tag_value('{{sHumi}}', c_sHumi)
        output_processor.set_tag_value('{{light}}', c_light)
        
        sensor_data = {
          "tm" : int(time.time()),
          "temp" : {"unit": "C", "val": temp},
          "humi" : {"unit": "%", "val": humi},
          "co2" : {"unit": "ppm", "val": c_co2},
          "wLev" : {"unit": "mm", "val": c_wLev},
          "sHumi" : {"unit": "%", "val": c_sHumi},
          "light" : {"unit": "lux", "val": c_light},
        }

        data_in_json_format = json.dumps(sensor_data)
        print("publish: {:s} {:s}%".format(topic, data_in_json_format))
        client.publish(topic, data_in_json_format, 1)

        next_reading += INTERVAL
        sleep_time = next_reading-time.time()
        while sleep_time > 0:
            output_processor.set_tag_value('{{tm}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            #time.sleep(0.1)
            check_chat()
            sleep_time = next_reading-time.time()
            #print('check')
except KeyboardInterrupt:
    pass

client.loop_stop()
client.disconnect()
