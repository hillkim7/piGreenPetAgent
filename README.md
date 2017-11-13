Green PET MQTT sensor data publisher
-----------------
Various sensor data are publishing to MQTT broker.  
Running platform is Rasberry PI 3 model B with Linux raspberrypi 4.9.41-v7+ #1023 SMP Tue Aug 8 16:00:15 BST 2017 armv7l GNU/Linux.

![raspberry HW](piGrenPetPrototype1.png)

Program run setup
---------------

```bash

# Install SHT10 python3 package
sudo pip3 install pi-sht1x

# install MQTT client library
sudo pip3 install paho-mqtt
```

Program run
---------------

```bash

# Edit line according to your MQTT broker address:
# "mqttLocalHost": "127.0.0.1",
vi mqttConfig.json

# run program
sudo python3 mqtt_loop_pub.py 1001 mqttConfig.json
```
