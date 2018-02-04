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
import RPi.GPIO as GPIO

# kind of sensor values
WATER_LEVEL_CHANNEL=0
SOIL_HUMIDIFY_CHANNEL=1
CO2_CHANNEL=2
LIGHT_CHANNEL=3

# kind of request message
MSG_CHAT=0
MSG_CTRL=1
MSG_PARA=2

# alarm type
TYPE_HUMI = 'humi'    # 습도
TYPE_TEMP = 'temp'    # 온도
TYPE_CO2 = 'co2'      # CO2
TYPE_WLEV = 'wLev'    # 수위(water level)
TYPE_SHUMI = 'sHumi'  # 지습(soil humidity)
TYPE_LIGHT = 'light'  # 조도

# alarm code
ALARM_OK = 0          # 정상
ALARM_LOW = 1         # 센서 하한값 미달
ALARM_HIGH = 2        # 센서 상한값 초과
ALARM_EVENT = 3       # 이벤트 발생

def generate_topic(service_code, product_sn):
    topic = 'petG1/' + service_code + '/' + product_sn + '/stat/_cur'
    return topic

def generate_chat_topic(service_code, product_sn):
    topic = 'petG1/' + service_code + '/' + product_sn + '/chat/_cur'
    return topic

def generate_alarm_topic(service_code, product_sn, alarm_type):
    topic = 'petG1/' + service_code + '/' + product_sn + '/alarm/' + alarm_type
    return topic

# make topic for remote call 
def generate_rcall_filter(service_code, product_sn):
    topic = 'petG1/' + service_code + '/' + product_sn + '/rcall/#'
    return topic

def generate_client_id(client_prefix, product_sn):
    client_id = client_prefix + 'GPET' + product_sn + '_' + str(random.randint(100, 999))
    return client_id

def load_json_file(path):
    with open(path) as data_file:
        return json.load(data_file)

def save_json_file(path, data):
    with open(path, 'w') as data_file:
        return json.dump(data, data_file, indent=2)

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

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

def read_channel(channel):
    cmd = 0b11 << 6  # Start bit, single channel read
    cmd |= (channel & 0x07) << 3  # channel number (in 3 bits)
    resp = spi.xfer2([cmd, 0x0, 0x0])
    result = (resp[0] & 0x01) << 9
    result |= (resp[1] & 0xFF) << 1
    result |= (resp[2] & 0x80) >> 7
    return result & 0x3FF

if len(sys.argv) != 2:
    print(sys.argv[0], "petConfig.json")
    sys.exit(0)

pet_config = load_json_file(sys.argv[1])
mqtt_config = load_json_file(pet_config['mqttConfigFile'])
param_config = load_json_file(pet_config['paramConfigFile'])
script_file = pet_config['scenarioFile']
product_sn = pet_config['sn']
report_interval = pet_config['reportInterval']

print('paramConfigFile: {}'.format(json.dumps(param_config, indent=2)))

topic = generate_topic(mqtt_config['serviceCode'], product_sn)
chat_topic = generate_chat_topic(mqtt_config['serviceCode'], product_sn)
client_id = generate_client_id(mqtt_config['clientPrefix'], product_sn)

sht = sht1x_sensor.SHT1xSensor()

ACCESS_TOKEN = 'IOT_DEMO_TOKEN'

next_reading = time.time() 

script_file = 'files/pet-scenario.csv'
bot_name = 'Green Pet'
bot_user = product_sn
ipc_queue = queue.Queue()

scenario = Scenario()
input_processor = InputProcessor()
output_processor = TagMapper()
scenario.load_scenario_file(script_file)
petbot = PetBot(bot_name, scenario, input_processor, output_processor)
print('Greeting', petbot.talk('안녕'))

def handle_mqtt_msg(msg):
    global ipc_queue, bot_user
    parsed_topic = msg.topic.split('/')
    payload = msg.payload.decode('utf-8')
    data = json.loads(payload)
    if parsed_topic[3] == 'chat':
        if 'user' not in data or data['user'] != bot_user:
            # 자신이 보낸 메시지는 처리하지 않도록 함
            print("text: " + data['text'])
            if data['text']:
                ipc_queue.put((MSG_CHAT, data))
    elif parsed_topic[3] == 'rcall':
        if parsed_topic[4] == '_ctrl':
            ipc_queue.put((MSG_CTRL, data))
        elif parsed_topic[4] == '_para':
            ipc_queue.put((MSG_PARA, data))
        else:
            print("unknown topic: {}".format(msg.topic))
    else:
        print("unknown topic: {}".format(msg.topic))

def on_message(mqttc, obj, msg):
    """ topic example>
    - chat topic: petG1/1/1001/chat/_cur
    - control topic: petG1/1/1001/rcall/_ctrl/123456
    - set topic: petG1/1/1001/rcall/_para/123456
    """
    #print("on message: " + msg.topic+" "+str(msg.qos)+" payload: "+str(msg.payload))
    #print("msg.payload --> type:{} text: {} len: {}".format(type(msg.payload), msg.payload, len(msg.payload)))
    try:
        handle_mqtt_msg(msg)
    except ValueError as e:
        print("no json text: {}".format(msg))
    except:
        print("Unexpected error: {}".format(sys.exc_info()[0]))

def process_chat(data):
    print('chat data: ', data)
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

def process_ctrl(data):
    print('ctrl data: ', data)
    if data['func'] == 'onOff':
        # device 번호에 명시된 GPIO 포트를 On 또는 Off함
        num = int(data['dev'])
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(num, GPIO.OUT)
        if int(data['val']):
            print("GPIO {} High".format(num))
            GPIO.output(num, GPIO.HIGH)
        else:
            print("GPIO {} Low".format(num))
            GPIO.output(num, GPIO.LOW)
    else:
        print("unknown 'func': {}".format(data['func']))
 
def process_param(data):
    global pet_config, param_config
    param_file = pet_config['paramConfigFile']
    print('param data: ', data)
    param_config = data
    save_json_file(param_file, param_config)

def check_queue_data():
    try:
        item = ipc_queue.get(True, 0.2)
    except queue.Empty:
        return
    try:
        if item[0] == MSG_CHAT:
            process_chat(item[1])
        elif item[0] == MSG_CTRL:
            process_ctrl(item[1])
        elif item[0] == MSG_PARA:
            process_param(item[1])
    except:
        print("error: {}".format(sys.exc_info()))

alarm_table = {}

def publish_alarm(alarm_type, payload):
    global client, mqtt_config, product_sn
    alarm_topic = generate_alarm_topic(mqtt_config['serviceCode'], product_sn, alarm_type)
    print("publish: {} {}%".format(alarm_topic, payload))
    client.publish(alarm_topic, payload, retain=True)

def check_sensor_value(alarm_type, sensor_value):
    """알람 범위에 벗어 났을때 알람 객체를 반환한다.
    {
      "tm" : 1510475347,
      "code" : 1,
      "min" : 5,
      "max" : 45,
      "val" : 15
    }
    """
    global alarm_table, param_config
    alarm_obj = {}
    alarm_obj['tm'] = int(time.time())
    print("alarm_type={} param_config={}".format(alarm_type, param_config))
    param_item = param_config[alarm_type]
    print("alarm_type={} param_item={}".format(alarm_type, param_item))
    if sensor_value < param_item['min']:
        alarm_obj['min'] = param_item['min']
        alarm_obj['val'] = sensor_value
        alarm_obj['max'] = param_item['max']
        alarm_obj['code'] = ALARM_LOW
        if alarm_type not in alarm_table or alarm_table[alarm_type] != ALARM_LOW:
            alarm_table[alarm_type] = ALARM_LOW
            return alarm_obj
    elif sensor_value > param_item['max']:
        alarm_obj['min'] = param_item['min']
        alarm_obj['val'] = sensor_value
        alarm_obj['max'] = param_item['max']
        alarm_obj['code'] = ALARM_HIGH
        if alarm_type not in alarm_table or alarm_table[alarm_type] != ALARM_HIGH:
            alarm_table[alarm_type] = ALARM_HIGH
            return alarm_obj
    elif alarm_type in alarm_table:
        # 발생됐다 정상 복구된 경우
        alarm_obj['code'] = ALARM_OK
        alarm_table.pop(alarm_type) ## remove key
        return alarm_obj

def check_alarm(alarm_type, sensor_value):
    alarm_item = check_sensor_value(alarm_type, sensor_value)
    if alarm_item:
        if alarm_item['code'] == ALARM_OK:
            publish_alarm(alarm_type, None)
        else:
            publish_alarm(alarm_type, json.dumps(alarm_item))

def check_alarm_events(sensor_data):
    try:
        check_alarm(TYPE_HUMI, sensor_data[TYPE_HUMI]['val'])
        check_alarm(TYPE_TEMP, sensor_data[TYPE_TEMP]['val'])
        check_alarm(TYPE_CO2, sensor_data[TYPE_CO2]['val'])
        check_alarm(TYPE_WLEV, sensor_data[TYPE_WLEV]['val'])
        check_alarm(TYPE_SHUMI, sensor_data[TYPE_SHUMI]['val'])
        check_alarm(TYPE_LIGHT, sensor_data[TYPE_LIGHT]['val'])
    except:
        print("error: {}".format(sys.exc_info()))

print("MQTT client_id={} with interval={}".format(client_id, report_interval))
client = mqtt.Client(client_id)

client.on_message = on_message

# Set access token
client.username_pw_set(ACCESS_TOKEN)

print("MQTT mqttLocalHost={} mqttLocalPort={}".format(mqtt_config['mqttLocalHost'], mqtt_config['mqttLocalPort']))
# Connect to MQTT broker using mqttLocalHost and port and 60 seconds keepalive interval
client.connect(mqtt_config['mqttLocalHost'], mqtt_config['mqttLocalPort'], 60)

temp = 0
humi = 0
client.loop_start()

topics = []
topics.append((chat_topic, 0))
topics.append((generate_rcall_filter(mqtt_config['serviceCode'], product_sn), 0))
print("subscribe {}".format(topics))
client.subscribe(topics, 0)

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
        check_alarm_events(sensor_data)
        next_reading += report_interval
        sleep_time = next_reading-time.time()
        while sleep_time > 0:
            output_processor.set_tag_value('{{tm}}', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            #time.sleep(0.1)
            check_queue_data()
            sleep_time = next_reading-time.time()
            #print('check')
except KeyboardInterrupt:
    pass

client.loop_stop()
client.disconnect()
