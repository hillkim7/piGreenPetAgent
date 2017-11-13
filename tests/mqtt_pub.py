import time
import sys
import paho.mqtt.client as mqtt
import json

## app run setup:
# pip3 install paho.mqtt

def num(s):
    try:
        return int(s)
    except ValueError:
        return float(s)

if len(sys.argv) != 5:
    print(sys.argv[0], "MQTT_server topic temperature humidity")
    print(sys.argv[0], "localhost PBoT/1/1001/stat/_cur 23.5 35")
    sys.exit(0)

server_addr = sys.argv[1]
topic = sys.argv[2]
temperature = num(sys.argv[3])
humidity = num(sys.argv[4])

sensor_data = {
  "tm" : int(time.time()),
  "temp" : {"unit": "C", "val": temperature},
  "humi" : {"unit": "%", "val": humidity},
  "co2" : {"unit": "ppm", "val": 2000}
}

next_reading = time.time() 

client = mqtt.Client()

# Set access token
#client.username_pw_set(ACCESS_TOKEN)

# Connect to ThingsBoard using default MQTT port and 60 seconds keepalive interval
client.connect(server_addr, 1883, 60)

# Sending humidity and temperature data to ThingsBoard
print("publish %s %s" % (topic, json.dumps(sensor_data)))
client.publish(topic, json.dumps(sensor_data), 1)
client.disconnect()
