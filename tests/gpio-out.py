#!/usr/bin/env python3

import RPi.GPIO as GPIO
import sys

if len(sys.argv) != 3:
    print("%s gpio_num [1:0]" % sys.argv[0])
    sys.exit()

num = int(sys.argv[1])
on_off = int(sys.argv[2])

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(num,GPIO.OUT)

print("GPIO %d --> %d" % (num, GPIO.input(num)))
if on_off:
    print("High")
    GPIO.output(num, GPIO.HIGH)
else:
    print("Low")
    GPIO.output(num, GPIO.LOW)
