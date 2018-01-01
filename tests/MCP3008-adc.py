#!/usr/bin/env python3
# read ADC value from MCP3008 ADC chip
import spidev
import time

spi = spidev.SpiDev()
spi.open(0, 0)

spi.mode = 0
old_speed = spi.max_speed_hz
# MCP3008 doesn't work on default Pi SPI speed, 125000000
# It must set the speed as 1 M.
spi.max_speed_hz = 1000000
print('max_speed_hz %d --> %d' % (old_speed, spi.max_speed_hz))

def read_channel(channel):
    assert 0 <= channel <= 7, 'ADC channel must be a value of 0-7'
    # make read cmd.
    cmd = 0b11 << 6  # Start bit, single channel read 
    cmd |= (channel & 0x07) << 3  # channel number (in 3 bits)
    resp = spi.xfer2([cmd, 0, 0])
    print(channel, resp)
    #resp = spi.xfer2([1, (8+channel) << 4, 0])
    result = (resp[0] & 0x01) << 9
    result |= (resp[1] & 0xFF) << 1
    result |= (resp[2] & 0x80) >> 7
    return result & 0x3FF

while True:
    values = list(map(lambda x: read_channel(x), range(8)))
    print("-->", values)
    time.sleep(0.5)
